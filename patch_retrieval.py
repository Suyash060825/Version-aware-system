with open('policy-ledger-v2/rag/chatbot/chat_service.py', 'r') as f:
    content = f.read()

repl = """    # 2. Retrieve top-N semantic matches
    t_retrieve = time.time()
    hits = store.search(
        query_embedding=q_vec,
        query_text=query,
        top_k=top_k_retrieve,
        active_only=not is_diff_query,
        allowed_departments=allowed_depts,
    )
    RETRIEVAL_LATENCY.observe(time.time() - t_retrieve)"""

content = content.replace("""    # 2. Retrieve top-N semantic matches
    hits = store.search(
        query_embedding=q_vec,
        query_text=query,
        top_k=top_k_retrieve,
        active_only=not is_diff_query,
        allowed_departments=allowed_depts,
    )
    RETRIEVAL_LATENCY.observe(time.time() - t0)""", repl)

with open('policy-ledger-v2/rag/chatbot/chat_service.py', 'w') as f:
    f.write(content)

