import re

with open('policy-ledger-v2/rag/entailment.py', 'r') as f:
    content = f.read()

# Add ENTAILMENT_ENABLED
content = content.replace("import re\n", "import re\nimport os\n\nENTAILMENT_ENABLED = os.environ.get('ENTAILMENT_ENABLED', 'true').lower() == 'true'\n")

# Add ENTAILMENT_ENABLED bypass
content = content.replace("def verify_entailment(answer: str, chunks: list[dict]) -> tuple[bool, float]:\n    \"\"\"\n    Verify if claims in answer are entailed by the provided chunks.\n    Returns (is_entailed, groundedness_score).\n    \"\"\"\n    if not answer or not chunks:", "def verify_entailment(answer: str, chunks: list[dict]) -> tuple[bool, float]:\n    \"\"\"\n    Verify if claims in answer are entailed by the provided chunks.\n    Returns (is_entailed, groundedness_score).\n    \"\"\"\n    if not ENTAILMENT_ENABLED:\n        return True, 1.0\n    if not answer or not chunks:")

# Fix entailment_idx
repl = """            label2id = {k.lower(): v for k, v in nli.config.label2id.items()}
            entailment_idx = label2id.get('entailment', 2)"""
content = content.replace("entailment_idx = nli.config.label2id.get('entailment', 1)", repl)

with open('policy-ledger-v2/rag/entailment.py', 'w') as f:
    f.write(content)

