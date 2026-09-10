"""
rag/api/rag_routes.py
Flask blueprint for all RAG endpoints. Preserves original layout, updated to QueryEngine.
"""
import uuid
import json
from datetime import datetime
from flask import Blueprint, request, jsonify, render_template, session, Response, stream_with_context
from flask_login import login_required, current_user
from models import (db, ChatSession, ChatMessage, SearchHistory, Feedback, IndexingJob,
                    PolicyChunk, PolicyChunkV2, CompilationJob, Policy, PolicyVersion,
                    PolicyFact, CanonicalQuestion)
from extensions import csrf, limiter
from utils import rate_limit_key_user_or_ip

rag_bp = Blueprint("rag", __name__, url_prefix="/rag")

# ─── Employee chat ─────────────────────────────────────────────────────────────

@rag_bp.route("/chat")
@login_required
def chat_page():
    """Render the AI chat interface for employees."""
    unread_count = _unread_count()
    try:
        doc_count = db.session.query(PolicyChunkV2.policy_id).distinct().count()
        if doc_count == 0:
            doc_count = db.session.query(PolicyChunk.policy_id).distinct().count()
    except Exception:
        doc_count = 0
    return render_template("employee/chat.html", unread_count=unread_count, doc_count=doc_count)


@rag_bp.route("/api/chat/stream", methods=["POST"])
@login_required
@limiter.limit("30 per minute", key_func=rate_limit_key_user_or_ip)
def api_chat_stream():
    data = request.get_json(force=True)
    query = (data.get("query") or "").strip()
    session_id = data.get("session_id")
    
    if session_id:
        from models import ChatSession
        cs = db.session.get(ChatSession, session_id)
        if not cs or cs.user_id != current_user.id:
            return jsonify({"error": "Unauthorized session_id"}), 403
    else:
        session_id = _get_or_create_session()

    if not query:
        return jsonify({"error": "Empty query"}), 400

    if len(query) > 1000:
        return jsonify({"error": "Query too long (max 1000 chars)"}), 400

    # User object and context for generator
    user_obj = current_user._get_current_object()

    def generate_events():
        from rag.engine.query_engine import get_query_engine
        engine = get_query_engine()
        full_answer = ""
        final_result_data = None

        try:
            for event in engine.stream_answer(query, user=user_obj, session_id=session_id):
                if event["type"] == "token":
                    full_answer += event["token"]
                    yield f"data: {json.dumps(event)}\n\n"
                elif event["type"] == "done":
                    final_result_data = event["result"]
                    
                    # Format citations
                    formatted_citations = []
                    for cit in final_result_data.get("citations", []):
                        formatted_citations.append({
                            "policy_id": cit.get("policy_id", 0),
                            "version_id": cit.get("version_id", 0),
                            "policy_name": cit.get("policy_name", "Policy"),
                            "version": cit.get("version", "1.0"),
                            "section": cit.get("section", "General"),
                            "page": cit.get("page", 1)
                        })

                    message_id = _save_message(
                        session_id, query, final_result_data["answer"], formatted_citations,
                        len(formatted_citations), model_name=final_result_data.get("model", "qwen3"),
                        cache_hit=False
                    )

                    _save_search_history(query, {
                        "fallback": final_result_data.get("fallback", False),
                        "chunks_used": len(formatted_citations)
                    })

                    event_payload = {
                        "type": "done",
                        "answer": final_result_data["answer"],
                        "citations": formatted_citations,
                        "confidence": final_result_data.get("confidence", 100),
                        "route": final_result_data.get("route", "HYBRID_RAG"),
                        "llm_used": final_result_data.get("llm_used", False),
                        "latency_ms": final_result_data.get("latency_ms", 0),
                        "session_id": session_id,
                        "message_id": message_id,
                        "fallback": final_result_data.get("fallback", False)
                    }
                    yield f"data: {json.dumps(event_payload)}\n\n"
        except Exception as e:
            import logging
            logging.getLogger("rag.api").exception("Stream error in api_chat_stream")
            yield f"data: {json.dumps({'type': 'error', 'error': 'An internal error occurred processing the chat stream.'})}\n\n"

    return Response(stream_with_context(generate_events()), mimetype="text/event-stream")


@rag_bp.route("/api/chat", methods=["POST"])
@login_required
@limiter.limit("20 per minute", key_func=rate_limit_key_user_or_ip)
def api_chat():
    data = request.get_json(force=True)
    query = (data.get("query") or "").strip()
    session_id = data.get("session_id")
    
    if session_id:
        from models import ChatSession
        cs = db.session.get(ChatSession, session_id)
        if not cs or cs.user_id != current_user.id:
            return jsonify({"error": "Unauthorized session_id"}), 403
    else:
        session_id = _get_or_create_session()

    if not query:
        return jsonify({"error": "Empty query"}), 400

    if len(query) > 1000:
        return jsonify({"error": "Query too long (max 1000 chars)"}), 400

    try:
        from rag.engine.query_engine import get_query_engine
        engine = get_query_engine()
        
        result = engine.answer(query, user=current_user, session_id=session_id)
        
        # Format citations to match chat.html's expectation
        citations = []
        for cit in result.citations:
            citations.append({
                "policy_id": cit.get("policy_id", 0),
                "version_id": cit.get("version_id", 0),
                "policy_name": cit.get("policy_name", "Policy"),
                "version": cit.get("version", "1.0"),
                "section": cit.get("section", "General"),
                "page": cit.get("page", 1)
            })

        message_id = _save_message(
            session_id, query, result.answer, citations,
            result.retrieval_count, model_name=result.model or "qwen3",
            cache_hit=False
        )
        
        _save_search_history(query, {
            "fallback": result.abstained,
            "chunks_used": result.retrieval_count
        })

        return jsonify({
            "answer": result.answer,
            "citations": citations,
            "chunks_used": result.retrieval_count,
            "session_id": session_id,
            "fallback": result.abstained,
            "model": result.model or "qwen3",
            "message_id": message_id,
            "confidence": result.confidence * 100,  # Convert to 0-100 scale for UI check
            "cache_hit": False,
            "route": result.route,
            "llm_used": result.llm_used,
            "latency_ms": result.latency_ms
        })
    except Exception as e:
        return jsonify({"error": "An internal error occurred processing your request."}), 500


@rag_bp.route("/api/feedback", methods=["POST"])
@login_required
def api_feedback():
    data = request.get_json(force=True)
    vote = data.get("vote")  # "up" or "down"
    comment = (data.get("comment") or "").strip()

    if vote not in ("up", "down"):
        return jsonify({"error": "Invalid vote"}), 400

    try:
        msg_id = int(data.get("message_id"))
        from models import ChatMessage, db
        msg = db.session.get(ChatMessage, msg_id)
        if not msg or msg.role != "assistant" or not msg.session or msg.session.user_id != current_user.id:
            return jsonify({"error": "Unauthorized message_id"}), 403
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid message_id"}), 400

    fb = Feedback(
        user_id=current_user.id,
        message_id=msg_id,
        vote=vote,
        comment=comment,
        created_at=datetime.utcnow(),
    )
    db.session.add(fb)
    db.session.commit()
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
        import logging
        logging.getLogger("rag.api").error(f"Failed to fetch store stats: {e}")
        vec_stats = {"total_chunks": 0, "status": "unavailable"}

    import os
    embedder = get_embedder()
    llm = get_llm()
    llm_provider = getattr(llm, "model", "Local LLM")
    embedder_model = os.environ.get("EMBEDDING_MODEL") or os.environ.get("FASTEMBED_MODEL") or getattr(embedder, "model_name", "BAAI/bge-small-en-v1.5")
    
    chunk_count = PolicyChunkV2.query.count()
    if chunk_count == 0:
        chunk_count = PolicyChunk.query.count()
    indexed_policies = db.session.query(PolicyChunkV2.policy_id).distinct().count()
    if indexed_policies == 0:
        indexed_policies = db.session.query(PolicyChunk.policy_id).distinct().count()

    compilation_jobs = CompilationJob.query.order_by(CompilationJob.started_at.desc()).limit(15).all()
    recent_jobs = []
    for cj in compilation_jobs:
        p = db.session.get(Policy, cj.policy_id)
        v = db.session.get(PolicyVersion, cj.version_id)
        recent_jobs.append({
            "id": cj.id,
            "policy_id": cj.policy_id,
            "policy_title": p.title if p else f"Policy #{cj.policy_id}",
            "version_label": v.version_label if v else "—",
            "chunks_indexed": cj.chunk_count or 0,
            "fact_count": cj.fact_count or 0,
            "qa_count": cj.qa_count or 0,
            "status": cj.stage or "ready",
            "error_message": cj.error,
            "completed_at": cj.completed_at or cj.started_at,
        })
    if not recent_jobs:
        # Fallback to legacy IndexingJob if CompilationJob table is empty
        for ij in IndexingJob.query.order_by(IndexingJob.completed_at.desc()).limit(10).all():
            p = db.session.get(Policy, ij.policy_id) if ij.policy_id else None
            recent_jobs.append({
                "id": ij.id,
                "policy_id": ij.policy_id,
                "policy_title": p.title if p else f"Policy #{ij.policy_id}",
                "version_label": ij.model_version or "—",
                "chunks_indexed": ij.chunks_indexed,
                "fact_count": 0,
                "qa_count": 0,
                "status": ij.status,
                "error_message": ij.error_message,
                "completed_at": ij.completed_at,
            })

    failed_jobs = (CompilationJob.query.filter_by(stage="failed").count() +
                   IndexingJob.query.filter_by(status="failed").count())

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
    if total_cache == 0:
        # Check database chat message cache stats if Prometheus reset
        total_asst_msgs = ChatMessage.query.filter_by(role="assistant").count()
        cached_msgs = ChatMessage.query.filter_by(role="assistant", cache_hit=True).count()
        cache_hit_rate = round(100 * cached_msgs / total_asst_msgs, 1) if total_asst_msgs else 0
    else:
        cache_hit_rate = round(100 * cache_hits / total_cache, 1)
    
    invalidations = REGISTRY.get_sample_value('rag_cache_invalidations_total', {'reason': 'explicit_drift'}) or 0
    ollama_req = REGISTRY.get_sample_value('rag_llm_requests_total', {'backend': 'OllamaProvider'}) or 0
    grounding_rej = REGISTRY.get_sample_value('rag_grounding_rejections_total') or 0
    
    total_llm_sum = (REGISTRY.get_sample_value('rag_llm_latency_seconds_sum', {'backend': 'OllamaProvider'}) or 0)
    total_llm_count = (REGISTRY.get_sample_value('rag_llm_latency_seconds_count', {'backend': 'OllamaProvider'}) or 0)
    llm_avg_ms = round((total_llm_sum / total_llm_count) * 1000) if total_llm_count else 0
    
    from blueprints.ai_analytics import _token_usage
    token_stats = _token_usage()
    cost_usd = token_stats.get("cost_est_usd", 0)

    return render_template("admin/rag_dashboard.html",
        vec_stats=vec_stats,
        embedder_model=embedder_model,
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
    from tasks import compile_policy_version_task
    try:
        compile_policy_version_task.delay(policy_id, version_id)
        job = CompilationJob.query.filter_by(policy_id=policy_id, version_id=version_id).first()
        return jsonify({
            "success": True,
            "message": "Compilation job queued",
            "chunks": job.chunk_count if job else 0,
            "facts": job.fact_count if job else 0,
            "qa": job.qa_count if job else 0,
            "stage": "queued"
        })
    except Exception as celery_err:
        from flask import current_app
        current_app.logger.warning(f"Celery enqueue failed: {celery_err}. Compiling synchronously.")
        from rag.compiler.pipeline import KnowledgeCompilerPipeline
        pipeline = KnowledgeCompilerPipeline()
        job = pipeline.compile(policy_id, version_id)
        return jsonify({
            "success": True,
            "message": f"Compilation status: {job.stage}",
            "chunks": job.chunk_count or 0,
            "facts": job.fact_count or 0,
            "qa": job.qa_count or 0,
            "stage": job.stage
        })


@rag_bp.route("/api/policy/<int:policy_id>/chunks", methods=["GET"])
@login_required
def get_policy_chunks(policy_id):
    if not current_user.can_manage_policies():
        return jsonify({"error": "Forbidden"}), 403
    policy = db.session.get(Policy, policy_id)
    if not policy:
        return jsonify({"error": "Policy not found"}), 404
    active_ver = policy.versions.filter_by(is_active=True).first()
    version_id = request.args.get("version_id", active_ver.id if active_ver else None, type=int)
    
    chunks_query = PolicyChunkV2.query.filter_by(policy_id=policy_id)
    if version_id:
        chunks_query = chunks_query.filter_by(version_id=version_id)
    chunks = chunks_query.order_by(PolicyChunkV2.id.asc()).all()
    
    data = []
    if chunks:
        for c in chunks:
            data.append({
                "chunk_id": c.chunk_id,
                "section_path": c.section_path or "—",
                "page": c.page or 1,
                "paragraph_num": c.paragraph_num or 1,
                "char_count": c.char_count or len(c.text),
                "text": c.text,
                "text_hash": (c.text_hash or "")[:12],
                "version_id": c.version_id,
            })
    else:
        legacy_chunks = PolicyChunk.query.filter_by(policy_id=policy_id).all()
        for lc in legacy_chunks:
            data.append({
                "chunk_id": f"chunk-{lc.id}",
                "section_path": "General",
                "page": 1,
                "paragraph_num": 1,
                "char_count": len(lc.chunk_text or ""),
                "text": lc.chunk_text or "",
                "text_hash": "legacy",
                "version_id": lc.version_id,
            })
            
    return jsonify({
        "policy_id": policy.id,
        "policy_title": policy.title,
        "version_label": active_ver.version_label if active_ver else "v1.0",
        "total_chunks": len(data),
        "chunks": data,
    })


@rag_bp.route("/admin/delete/<int:policy_id>", methods=["POST"])
@login_required
def admin_delete_index(policy_id):
    if not current_user.can_manage_policies():
        return jsonify({"error": "Forbidden"}), 403
    from rag.vectordb.chroma import get_store
    get_store().delete_policy(policy_id)
    return jsonify({"ok": True})


# ─── Health Endpoints ──────────────────────────────────────────────────────────

@rag_bp.route("/health", methods=["GET"])
def health_check():
    db_status = "ok"
    try:
        from sqlalchemy import text
        db.session.execute(text("SELECT 1"))
    except Exception as e:
        import logging
        logging.getLogger("rag.health").error(f"DB Health Check Failed: {e}")
        db_status = "error"

    chroma_status = "ok"
    try:
        from rag.vectordb.chroma import get_store
        get_store().stats()
    except Exception as e:
        import logging
        logging.getLogger("rag.health").error(f"Chroma Health Check Failed: {e}")
        chroma_status = "error"

    healthy = (db_status == "ok" and chroma_status == "ok")
    return jsonify({
        "status": "healthy" if healthy else "degraded",
        "database": db_status,
        "chromadb": chroma_status,
        "timestamp": datetime.utcnow().isoformat()
    }), (200 if healthy else 503)


@rag_bp.route("/health/llm", methods=["GET"])
def llm_health_check():
    from rag.llm_provider import get_llm_provider
    try:
        provider = get_llm_provider()
        is_healthy = provider.health_check()
    except Exception:
        is_healthy = False
    return jsonify({
        "healthy": is_healthy,
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
