"""
rag/chatbot/chat_service.py
Full RAG pipeline: question → embed → retrieve → rerank → prompt → pluggable LLM → cite
"""
from rag.embeddings.embedder import get_embedder
from rag.vectordb.chroma import get_store
from rag.reranker.reranker import get_reranker
from rag.llm.prompt_builder import build_prompt
from rag.llm_provider import get_llm_provider
from rag.chatbot.citations import build_citations
from rag.chatbot.memory import get_history, add_message
from rag.cache.semantic_cache import get_cache
import threading

RELEVANCE_THRESHOLD = 0.10

_embed_dedup_cache = {}
_embed_dedup_lock = threading.Lock()


def _run_diff_agent(query: str, session_id: str, q_vec: list, allowed_depts: list, provider, store) -> dict:
    from models import db, Policy, PolicyVersion
    from rag.chatbot.memory import add_message
    
    hits = store.search(
        query_embedding=q_vec,
        query_text=query,
        top_k=5,
        active_only=False,
        allowed_departments=allowed_depts,
    )
    if not hits:
        return None
        
    policy_ids = [int(h.get("policy_id")) for h in hits[:3] if h.get("policy_id") and str(h.get("policy_id")).isdigit()]
    if not policy_ids:
        return None
        
    from collections import Counter
    target_policy_id = Counter(policy_ids).most_common(1)[0][0]
    
    policy = db.session.get(Policy, target_policy_id)
    if not policy:
        return None
        
    versions = policy.versions.order_by(PolicyVersion.version_num.desc()).limit(2).all()
    if len(versions) < 2:
        ans = f"The '{policy.title}' policy only has one version (v{versions[0].version_num}), so there are no changes to compare."
        add_message(session_id, "user", query)
        add_message(session_id, "assistant", ans)
        return {
            "answer": ans,
            "citations": [],
            "chunks_used": 0,
            "session_id": session_id,
            "fallback": False,
            "model": "DiffAgent",
            "cache_hit": False,
            "confidence": 100,
            "usage": {}
        }
        
    v_new, v_old = versions[0], versions[1]
    prompt = f"You are a specialized Policy Diffing Agent.\nThe user is asking about changes in the '{policy.title}' policy.\n\nOLD version (v{v_old.version_num}):\n{v_old.content[:2000]}...\n\nNEW version (v{v_new.version_num}):\n{v_new.content[:2000]}...\n\nQuestion: {query}\nExplain the changes clearly based ONLY on the provided texts."

    messages = [{"role": "system", "content": "You are a helpful HR assistant."}, {"role": "user", "content": prompt}]
    llm_resp = provider.generate(messages)
    
    ans = llm_resp.text
    add_message(session_id, "user", query)
    add_message(session_id, "assistant", ans)
    
    return {
        "answer": ans,
        "citations": [{"id": "diff", "title": f"Diff: {policy.title}", "version": f"v{v_old.version_num}->v{v_new.version_num}", "section": "Full text analysis"}],
        "chunks_used": 2,
        "session_id": session_id,
        "fallback": False,
        "model": "DiffAgent_" + (provider.get_model_name() if hasattr(provider, "get_model_name") else getattr(provider, "model", "none")),
        "cache_hit": False,
        "confidence": 100,
        "usage": {}
    }


def answer(
    query: str,
    session_id: str,
    user_role: str = "employee",
    user_department: str = "",
    top_k_retrieve: int = 20,
    top_k_rerank: int = 5,
    stream: bool = False,
) -> dict:
    """
    Full RAG pipeline. Returns:
    {
        "answer": str,
        "citations": list[dict],
        "chunks_used": int,
        "session_id": str,
        "fallback": bool,
        "model": str,
    }
    """
    embedder = get_embedder()
    store = get_store()
    reranker = get_reranker()
    provider = get_llm_provider()

    # Role-based department filtering
    allowed_depts = None
    if user_role == "employee" and user_department:
        allowed_depts = [user_department, ""]  # own dept + company-wide
    elif user_role in ("hr", "admin"):
        allowed_depts = None  # no restriction

    import time
    from rag.metrics import RETRIEVAL_LATENCY, RERANK_LATENCY, CACHE_LATENCY, GUARDRAIL_LATENCY, GENERATION_LATENCY


    # Guardrails: Input check
    from rag.guardrails import check_input_guardrails, apply_output_guardrails
    t0 = time.time()
    is_allowed, fallback_msg = check_input_guardrails(query)
    GUARDRAIL_LATENCY.observe(time.time() - t0)
    
    if not is_allowed:
        add_message(session_id, "user", query)
        add_message(session_id, "assistant", fallback_msg)
        final_res = {
            "answer": fallback_msg,
            "citations": [],
            "chunks_used": 0,
            "session_id": session_id,
            "fallback": True,
            "model": "guardrails",
            "cache_hit": False,
            "usage": {},
            "confidence": 100
        }
        if stream:
            def generate_guardrail():
                yield {"token": fallback_msg}
                yield {"final": final_res}
            return generate_guardrail()
        return final_res

    # 1. Embed query (with dedup cache in memory)
    # Dedup cache is just a simple memory dict for high throughput local dedup
    global _embed_dedup_cache, _embed_dedup_lock
    import time
    t0 = time.time()
    
    with _embed_dedup_lock:
        if query in _embed_dedup_cache:
            q_vec = _embed_dedup_cache[query]
        else:
            q_vec = None

    if q_vec is None:
        q_vec = embedder.embed_query(query)
        with _embed_dedup_lock:
            _embed_dedup_cache[query] = q_vec
            if len(_embed_dedup_cache) > 1000:
                _embed_dedup_cache.clear() # naive TTL/eviction

    diff_keywords = ["changed", "used to", "previous version", "difference between", "compare", "diff"]
    is_diff_query = any(k in query.lower() for k in diff_keywords)
    
    if is_diff_query:
        diff_res = _run_diff_agent(query, session_id, q_vec, allowed_depts, provider, store)
        if diff_res:
            if stream:
                def generate_diff():
                    yield {"token": diff_res["answer"]}
                    yield {"final": diff_res}
                return generate_diff()
            return diff_res

    # 1.5 Cache Lookup
    t_cache = time.time()
    cache = get_cache()
    cached = cache.get(q_vec, allowed_depts, is_diff_query=is_diff_query)
    CACHE_LATENCY.observe(time.time() - t_cache)
    
    if cached:
        add_message(session_id, "user", query)
        add_message(session_id, "assistant", cached["answer"])
        final_res = {
            "answer": cached["answer"],
            "citations": cached["citations"],
            "chunks_used": cached["chunks_used"],
            "session_id": session_id,
            "fallback": False,
            "model": "cache",
            "cache_hit": True,
            "confidence": cached.get("confidence", 100)
        }
        if stream:
            def generate_cache():
                yield {"token": cached["answer"]}
                yield {"final": final_res}
            return generate_cache()
        return final_res

    # 2. Retrieve top-N semantic matches
    hits = store.search(
        query_embedding=q_vec,
        query_text=query,
        top_k=top_k_retrieve,
        active_only=not is_diff_query,
        allowed_departments=allowed_depts,
    )
    RETRIEVAL_LATENCY.observe(time.time() - t0)

    # 3. Filter by relevance threshold
    hits = [h for h in hits if h.get("score", 0) >= RELEVANCE_THRESHOLD]

    if not hits:
        answer_text = "I couldn't find this information in the available policies."
        add_message(session_id, "user", query)
        add_message(session_id, "assistant", answer_text)
        final_res = {
            "answer": answer_text,
            "citations": [],
            "chunks_used": 0,
            "session_id": session_id,
            "fallback": True,
            "model": provider.get_model_name(),
            "cache_hit": False,
            "usage": {},
            "confidence": 0
        }
        if stream:
            def generate_empty():
                yield {"token": answer_text}
                yield {"final": final_res}
            return generate_empty()
        return final_res

    # 4. Rerank
    t0 = time.time()
    top_chunks = reranker.rerank(query, hits, top_k=top_k_rerank)
    RERANK_LATENCY.observe(time.time() - t0)

    # 4.5 Decide routing and confidence
    top_score = top_chunks[0].get("rerank_score", 0) if top_chunks else 0
    confidence_score = int(min(1.0, max(0.0, top_score)) * 100) if top_chunks else 0
    use_secondary = confidence_score < 60 or is_diff_query
    augmented_query = query
    # 4.5 Diff-aware augmentation
    _is_diff_for_augment = any(k in query.lower() for k in ["diff", "change", "compare", "difference"])
    if _is_diff_for_augment:
        try:
            from models import PolicyVersion
            policy_ids = list(set([int(c.get("policy_id")) for c in top_chunks if c.get("policy_id")]))
            diffs = []
            for pid in policy_ids:
                versions = PolicyVersion.query.filter_by(policy_id=pid).order_by(PolicyVersion.version_num.desc()).limit(2).all()
                if len(versions) == 2:
                    diffs.append(f"Diff for Policy {pid} (v{versions[1].version_label} -> v{versions[0].version_label}): {versions[0].diff_json or 'None'}")
            if diffs:
                augmented_query = augmented_query + "\n\nPolicy Diffs:\n" + "\n".join(diffs) + "\n\nPlease contrast the versions based on the above diffs and excerpts."
        except Exception:
            pass

    # 4.8 Contradiction-aware generation
    if top_chunks:
        try:
            from models import ContradictionFlag
            policy_ids = list(set([int(c.get("policy_id")) for c in top_chunks if c.get("policy_id")]))
            if len(policy_ids) > 1:
                # Find any open contradictions between these policies
                flags = ContradictionFlag.query.filter(
                    ContradictionFlag.status == "open",
                    ContradictionFlag.policy_a_id.in_(policy_ids),
                    ContradictionFlag.policy_b_id.in_(policy_ids)
                ).all()
                if flags:
                    flag_texts = []
                    for f in flags:
                        flag_texts.append(f"Policies {f.policy_a_id} and {f.policy_b_id} have an open contradiction flag: {f.description}")
                    augmented_query = augmented_query + "\n\nWARNING: " + "\n".join(flag_texts) + "\n\nDo not silently pick one side. Explicitly state the contradiction in your answer."
        except Exception as e:
            pass

    # 4.9 Prompt compression
    # Extract only top-N most query-relevant sentences per chunk before prompting
    import re
    compressed_chunks = []
    q_tokens_cmp = set(re.findall(r"[a-z0-9]+", query.lower()))
    for c in top_chunks:
        sentences = re.split(r'(?<=[.!?])\s+', c.get("text", "").strip())
        if len(sentences) > 3:
            s_scores = []
            for s in sentences:
                s_toks = set(re.findall(r"[a-z0-9]+", s.lower()))
                overlap = len(q_tokens_cmp & s_toks) / max(len(s_toks), 1)
                s_scores.append((overlap, s))
            s_scores.sort(key=lambda x: x[0], reverse=True)
            # Keep top 3 most relevant sentences in original order
            top_s = [s[1] for s in sorted(s_scores[:3], key=lambda x: sentences.index(x[1]))]
            new_c = dict(c)
            new_c["text"] = " ".join(top_s)
            compressed_chunks.append(new_c)
        else:
            compressed_chunks.append(c)

    # 5. Build prompt with conversation memory & prompt engineering guards
    history = get_history(session_id)
    messages = build_prompt(
        augmented_query,
        compressed_chunks,
        chat_history=history,
        user_role=user_role,
        user_department=user_department,
    )

    # 5.5 Exact Match Cache Check
    import hashlib
    chunk_ids = [str(c.get("id", "")) for c in top_chunks]
    cache_key_str = f"{query.strip().lower()}|{user_role}|{user_department}|{','.join(sorted(chunk_ids))}"
    exact_cache_key = "exact:" + hashlib.sha256(cache_key_str.encode()).hexdigest()
    
    exact_cached = None
    if cache.use_redis:
        data = cache.redis.get(exact_cache_key)
        if data:
            import json
            exact_cached = json.loads(data)

    if exact_cached:
        answer_text = exact_cached["answer"]
        llm_resp = type('obj', (object,), {'text': answer_text, 'fallback': False, 'error': None, 'model': 'exact-cache', 'usage': {}})()
    else:
        # 6. Generate answer via LLMProvider
        t0 = time.time()
        # H1 fix: only pass use_secondary to CascadeProvider
        kwargs = {"use_secondary": use_secondary} if getattr(provider, "__class__", None).__name__ == "CascadeProvider" else {}
        try:
            llm_resp = provider.generate(messages, **kwargs)
        except Exception as e:
            llm_resp = type('obj', (object,), {'text': f"Error: {str(e)}", 'fallback': True, 'error': str(e), 'model': 'error', 'usage': {}})()
        GENERATION_LATENCY.observe(time.time() - t0)
        
        if cache.use_redis and not (llm_resp.fallback or llm_resp.error):
            import json
            cache.redis.setex(exact_cache_key, 3600, json.dumps({"answer": llm_resp.text}))

    answer_text = llm_resp.text
    is_fallback = llm_resp.fallback or (llm_resp.error is not None)

    # Guardrails: Output check
    if not is_fallback:
        answer_text = apply_output_guardrails(answer_text, top_chunks)
        if "blocked by safety filters" in answer_text or "hallucinated citation" in answer_text:
            is_fallback = True

    # 7. Citations
    citations = build_citations(top_chunks)
    
    # 7.5 Grounding check (Entailment)
    groundedness_score = 1.0
    if not is_fallback:
        from rag.entailment import verify_entailment
        is_entailed, groundedness_score = verify_entailment(answer_text, top_chunks)
        if not citations or not is_entailed:
            from rag.metrics import GROUNDING_REJECTIONS
            GROUNDING_REJECTIONS.inc()
            answer_text = "I couldn't find sufficient information in the available policies to fully support an answer."
            is_fallback = True

    # 8. Update memory
    add_message(session_id, "user", query)
    add_message(session_id, "assistant", answer_text)

    # 9. Cache put
    if not is_fallback:
        cache.put(
            query_embedding=q_vec,
            answer=answer_text,
            citations=citations,
            chunks_used=len(top_chunks),
            allowed_depts=allowed_depts,
            model=llm_resp.model,
            is_diff_query=is_diff_query,
        )
        # We don't store confidence in cache explicitly unless we update SemanticCache put, but we can just use 100 on cache hit.

    final_result = {
        "answer": answer_text,
        "citations": citations,
        "chunks_used": len(top_chunks),
        "session_id": session_id,
        "fallback": is_fallback,
        "model": llm_resp.model,
        "cache_hit": False,
        "usage": llm_resp.usage,
        "confidence": confidence_score,
        "groundedness": groundedness_score
    }
    
    if stream:
        def generate():
            # Simulate streaming for now by chunking the final answer.
            # In a real setup, LLMProvider would yield partial LLMResponse chunks.
            words = answer_text.split(" ")
            for i, word in enumerate(words):
                yield {"token": word + (" " if i < len(words) - 1 else "")}
            yield {"final": final_result}
        return generate()

    return final_result
