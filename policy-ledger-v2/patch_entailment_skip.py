with open('policy-ledger-v2/rag/chatbot/chat_service.py', 'r') as f:
    content = f.read()

repl = """    # 7.5 Grounding check (Entailment)
    groundedness_score = 1.0
    REFUSAL_STRINGS = {
        "I couldn't find this information in the available policies.",
        "I couldn't find sufficient information in the available policies to fully support an answer.",
    }
    if not is_fallback and answer_text not in REFUSAL_STRINGS:
        from rag.entailment import verify_entailment
        is_entailed, groundedness_score = verify_entailment(answer_text, top_chunks)
        if not citations or not is_entailed:"""

content = content.replace("""    # 7.5 Grounding check (Entailment)
    groundedness_score = 1.0
    if not is_fallback:
        from rag.entailment import verify_entailment
        is_entailed, groundedness_score = verify_entailment(answer_text, top_chunks)
        if not citations or not is_entailed:""", repl)

with open('policy-ledger-v2/rag/chatbot/chat_service.py', 'w') as f:
    f.write(content)

