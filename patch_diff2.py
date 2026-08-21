import re

with open('policy-ledger-v2/rag/chatbot/chat_service.py', 'r') as f:
    content = f.read()

# I will find the function and replace it using regex
content = re.sub(
    r'def _run_diff_agent\(query: str, session_id: str, q_vec: list, allowed_depts: list, provider, store\) -> dict:(.*?)add_message\(session_id, "assistant", ans\)\n    return \{\n.*?"usage": llm_resp\.usage\n    \}',
    r'''def _run_diff_agent(query: str, session_id: str, q_vec: list, allowed_depts: list, provider, store) -> dict:
    try:
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
        prompt = f"You are a specialized Policy Diffing Agent.\\nThe user is asking about changes in the '{policy.title}' policy.\\n\\nOLD version (v{v_old.version_num}):\\n{v_old.content[:2000]}...\\n\\nNEW version (v{v_new.version_num}):\\n{v_new.content[:2000]}...\\n\\nQuestion: {query}\\nExplain the changes clearly based ONLY on the provided texts."

        messages = [{"role": "system", "content": "You are a helpful HR assistant."}, {"role": "user", "content": prompt}]
        llm_resp = provider.generate(messages)
        
        ans = llm_resp.text
        add_message(session_id, "user", query)
        add_message(session_id, "assistant", ans)
        return {
            "answer": ans,
            "citations": [{"policy_id": target_policy_id, "title": f"Diff: {policy.title} v{v_old.version_num} -> v{v_new.version_num}"}],
            "chunks_used": 2,
            "session_id": session_id,
            "fallback": False,
            "model": llm_resp.model,
            "cache_hit": False,
            "confidence": 95,
            "usage": llm_resp.usage
        }
    except Exception as e:
        logger.error(f"[DiffAgent] Error: {e}")
        return None''',
    content,
    flags=re.DOTALL
)

with open('policy-ledger-v2/rag/chatbot/chat_service.py', 'w') as f:
    f.write(content)

