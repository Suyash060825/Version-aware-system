"""
rag/api/rag_routes.py
Flask blueprint for all RAG endpoints.
Register in app.py: app.register_blueprint(rag_bp)
"""
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, render_template, session
from flask_login import login_required, current_user
from models import db, ChatSession, ChatMessage, SearchHistory, Feedback, IndexingJob, PolicyChunk
from app import csrf

rag_bp = Blueprint("rag", __name__, url_prefix="/rag")


# ─── Employee chat ─────────────────────────────────────────────────────────────

@rag_bp.route("/chat")
@login_required
def chat_page():
    """Render the AI chat interface for employees."""
    unread_count = _unread_count()
    try:
        doc_count = db.session.query(PolicyChunk.policy_id).distinct().count()
    except Exception:
        doc_count = 0
    return render_template("employee/chat.html", unread_count=unread_count, doc_count=doc_count)


@rag_bp.route("/api/chat", methods=["POST"])
@csrf.exempt
@login_required
def api_chat():
    data = request.get_json(force=True)
    query = (data.get("query") or "").strip()
    session_id = data.get("session_id") or _get_or_create_session()

    if not query:
        return jsonify({"error": "Empty query"}), 400

    if len(query) > 1000:
        return jsonify({"error": "Query too long (max 1000 chars)"}), 400

    from rag.chatbot.chat_service import answer as rag_answer
    dept = current_user.department.name if current_user.department else ""
    
    is_stream = data.get("stream", False)

    if is_stream:
        from flask import Response
        import json
        
        def generate_stream():
            for chunk in rag_answer(
                query=query,
                session_id=session_id,
                user_role=current_user.role,
                user_department=dept,
                stream=True
            ):
                yield f"data: {json.dumps(chunk)}\n\n"
        
        return Response(generate_stream(), mimetype="text/event-stream")
        
    result = rag_answer(
        query=query,
        session_id=session_id,
        user_role=current_user.role,
        user_department=dept,
        stream=False
    )

    # Persist to DB with model traceability
    message_id = _save_message(
        session_id, query, result["answer"], result["citations"],
        result["chunks_used"], model_name=result.get("model"),
        cache_hit=result.get("cache_hit", False),
        usage=result.get("usage", {})
    )
    _save_search_history(query, result)

    return jsonify({
        "answer": result["answer"],
        "citations": result["citations"],
        "chunks_used": result["chunks_used"],
        "session_id": session_id,
        "fallback": result["fallback"],
        "model": result.get("model"),
        "message_id": message_id,
        "confidence": result.get("confidence", 0),  # I7 fix: expose to frontend
        "cache_hit": result.get("cache_hit", False),
    })


@rag_bp.route("/api/feedback", methods=["POST"])
@csrf.exempt
@login_required
def api_feedback():
    data = request.get_json(force=True)
    vote = data.get("vote")  # "up" or "down"
    comment = (data.get("comment") or "").strip()

    if vote not in ("up", "down"):
        return jsonify({"error": "Invalid vote"}), 400

    # message_id must be a real ChatMessage row id (integer) or None —
    # never trust it blindly, since the FK column will reject anything else.
    try:
        msg_id = int(data.get("message_id"))
    except (TypeError, ValueError):
        msg_id = None

    fb = Feedback(
        user_id=current_user.id,
        message_id=msg_id,
        vote=vote,
        comment=comment,
        created_at=datetime.utcnow(),
    )
    db.session.add(fb)
    db.session.commit()
    
    if vote == "down" and msg_id:
        from rag.chatbot.self_healing import trigger_self_healing
        import threading
        # Run in background to avoid blocking response
        threading.Thread(target=trigger_self_healing, args=(msg_id,)).start()

    return jsonify({"ok": True})


@rag_bp.route("/api/sessions/<session_id>/history")
@login_required
def api_session_history(session_id):
    session_obj = db.session.get(ChatSession, session_id)
    if not session_obj or session_obj.user_id != current_user.id:
        from flask import abort
        abort(403)
    msgs = ChatMessage.query.filter_by(session_id=session_id)\
        .order_by(ChatMessage.created_at).all()
    return jsonify([{
        "id": m.id, "role": m.role, "content": m.content,
        "citations": m.citations_json, "created_at": m.created_at.isoformat(),
    } for m in msgs])


@rag_bp.route("/api/sessions/clear", methods=["POST"])
@csrf.exempt
@login_required
def api_clear_session():
    sid = request.get_json(force=True).get("session_id")
    session_obj = db.session.get(ChatSession, sid)
    if not session_obj or session_obj.user_id != current_user.id:
        from flask import abort
        abort(403)
    from rag.chatbot.memory import clear_session
    clear_session(sid)
    return jsonify({"ok": True})


# ─── Admin RAG dashboard ────────────────────────────────────────────────────────

@rag_bp.route("/admin/dashboard")
@login_required
def admin_rag_dashboard():
    if not current_user.can_manage_policies():
        from flask import abort
        abort(403)

    from rag.vectordb.chroma import get_store
    from rag.embeddings.embedder import get_embedder
    from rag.llm_provider import get_llm_provider as get_llm

    try:
        store = get_store()
        vec_stats = store.stats()
    except Exception as e:
        vec_stats = {"total_chunks": 0, "error": str(e)}

    embedder = get_embedder()
    llm = get_llm()
    if True:
        llm_provider = getattr(llm, "model", "Local LLM")
    else:
        llm_provider = "Extractive fallback (no LLM_PROVIDER / API key configured)"
    chunk_count = PolicyChunk.query.count()
    indexed_policies = db.session.query(PolicyChunk.policy_id).distinct().count()
    recent_jobs = IndexingJob.query.order_by(IndexingJob.completed_at.desc()).limit(10).all()
    failed_jobs = IndexingJob.query.filter_by(status="failed").count()

    # Search analytics
    total_queries = SearchHistory.query.count()
    failed_queries = SearchHistory.query.filter_by(answered=False).count()

    # Feedback stats
    thumbs_up = Feedback.query.filter_by(vote="up").count()
    thumbs_down = Feedback.query.filter_by(vote="down").count()

    # Top searched queries
    from sqlalchemy import func
    top_queries = db.session.query(
        SearchHistory.query_text,
        func.count(SearchHistory.id).label("count")
    ).group_by(SearchHistory.query_text).order_by(func.count(SearchHistory.id).desc()).limit(8).all()

    unread_count = _unread_count()
    
    # Observability Panel (Prometheus & Costs)
    from prometheus_client import REGISTRY
    cache_hits = REGISTRY.get_sample_value('rag_cache_hits_total') or 0
    cache_misses = (REGISTRY.get_sample_value('rag_cache_misses_total', {'reason': 'version_drift'}) or 0) + \
                   (REGISTRY.get_sample_value('rag_cache_misses_total', {'reason': 'not_found'}) or 0)
    total_cache = cache_hits + cache_misses
    cache_hit_rate = round(100 * cache_hits / total_cache, 1) if total_cache else 0
    
    invalidations = REGISTRY.get_sample_value('rag_cache_invalidations_total', {'reason': 'explicit_drift'}) or 0
    
    ollama_req = REGISTRY.get_sample_value('rag_llm_requests_total', {'backend': 'OllamaProvider'}) or 0
    grounding_rej = REGISTRY.get_sample_value('rag_grounding_rejections_total') or 0
    
    total_llm_sum = (REGISTRY.get_sample_value('rag_llm_latency_seconds_sum', {'backend': 'OllamaProvider'}) or 0) + \
                    (REGISTRY.get_sample_value('rag_llm_latency_seconds_sum', {'backend': 'GeminiProvider'}) or 0)
    total_llm_count = (REGISTRY.get_sample_value('rag_llm_latency_seconds_count', {'backend': 'OllamaProvider'}) or 0) + \
                      (REGISTRY.get_sample_value('rag_llm_latency_seconds_count', {'backend': 'GeminiProvider'}) or 0)
    llm_avg_ms = round((total_llm_sum / total_llm_count) * 1000) if total_llm_count else 0
    
    from blueprints.ai_analytics import _token_usage
    token_stats = _token_usage()
    cost_usd = token_stats.get("cost_est_usd", 0)

    return render_template("admin/rag_dashboard.html",
        vec_stats=vec_stats,
        embedder_model=embedder.model_name,
        llm_provider=llm_provider,
        chunk_count=chunk_count,
        indexed_policies=indexed_policies,
        recent_jobs=recent_jobs,
        failed_jobs=failed_jobs,
        total_queries=total_queries,
        failed_queries=failed_queries,
        thumbs_up=thumbs_up,
        thumbs_down=thumbs_down,
        top_queries=top_queries,
        unread_count=unread_count,
        cache_hit_rate=cache_hit_rate,
        invalidations=invalidations,
        ollama_req=ollama_req,
        
        grounding_rej=grounding_rej,
        llm_avg_ms=llm_avg_ms,
        cost_usd=cost_usd,
    )


@rag_bp.route("/admin/index/<int:policy_id>/<int:version_id>", methods=["POST"])
@login_required
def admin_index_policy(policy_id, version_id):
    if not current_user.can_manage_policies():
        return jsonify({"error": "Forbidden"}), 403
    from tasks import index_policy_version_task
    try:
        index_policy_version_task.delay(policy_id, version_id)
        return jsonify({"success": True, "message": "Indexing job queued"})
    except Exception as celery_err:
        from flask import current_app
        current_app.logger.warning(f"Celery enqueue failed: {celery_err}. Indexing synchronously.")
        from rag.indexing.index_policy import index_policy_version
        result = index_policy_version(policy_id, version_id)
        if result.get("success"):
            return jsonify({"success": True, "message": "Indexing completed synchronously"})
        else:
            return jsonify({"success": False, "error": result.get("error") or "Sync indexing failed"}), 500


@rag_bp.route("/admin/delete/<int:policy_id>", methods=["POST"])
@login_required
def admin_delete_index(policy_id):
    if not current_user.can_manage_policies():
        return jsonify({"error": "Forbidden"}), 403
    from rag.indexing.index_policy import delete_policy_from_index
    delete_policy_from_index(policy_id)
    return jsonify({"ok": True})


# ─── Health Endpoints ──────────────────────────────────────────────────────────

@rag_bp.route("/health", methods=["GET"])
def health_check():
    db_status = "ok"
    try:
        from sqlalchemy import text
        db.session.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"error: {str(e)}"

    chroma_status = "ok"
    try:
        from rag.vectordb.chroma import get_store
        get_store().stats()
    except Exception as e:
        chroma_status = f"error: {str(e)}"

    healthy = (db_status == "ok" and chroma_status == "ok")
    return jsonify({
        "status": "healthy" if healthy else "degraded",
        "database": db_status,
        "chromadb": chroma_status,
        "timestamp": datetime.utcnow().isoformat()
    }), (200 if healthy else 503)


@rag_bp.route("/health/llm", methods=["GET"])
def llm_health_check():
    import os
    from rag.llm_provider import get_llm_provider
    provider = get_llm_provider()
    is_healthy = provider.health_check()
    model = getattr(provider, "model", "unknown")
    return jsonify({
        "healthy": is_healthy,
        "backend": os.environ.get("LLM_BACKEND", os.environ.get("LLM_PROVIDER", "ollama")),
        "model": model,
        "timestamp": datetime.utcnow().isoformat()
    }), (200 if is_healthy else 503)


# ─── Helpers ───────────────────────────────────────────────────────────────────

def _get_or_create_session() -> str:
    key = "rag_session_id"
    if key not in session:
        sid = str(uuid.uuid4())
        session[key] = sid
        cs = ChatSession(
            id=sid,
            user_id=current_user.id,
            created_at=datetime.utcnow(),
        )
        db.session.add(cs)
        db.session.commit()
    return session[key]


def _save_message(session_id, query, answer, citations, chunks_used, model_name=None, cache_hit=False, usage=None):
    import json
    usage = usage or {}
    try:
        msg_user = ChatMessage(
            session_id=session_id, role="user", content=query,
            created_at=datetime.utcnow(),
        )
        db.session.add(msg_user)
        db.session.flush()

        msg_asst = ChatMessage(
            session_id=session_id, role="assistant", content=answer,
            citations_json=json.dumps(citations),
            chunks_used=chunks_used,
            model_name=model_name,
            model_used=model_name,
            cache_hit=cache_hit,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            created_at=datetime.utcnow(),
        )
        db.session.add(msg_asst)
        db.session.commit()
        return msg_asst.id
    except Exception:
        pass


def _save_search_history(query, result):
    try:
        sh = SearchHistory(
            user_id=current_user.id,
            query_text=query[:500],
            answered=not result["fallback"],
            chunks_found=result["chunks_used"],
            created_at=datetime.utcnow(),
        )
        db.session.add(sh)
        db.session.commit()
    except Exception:
        pass


def _unread_count():
    from models import Notification
    try:
        return Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    except Exception:
        return 0
