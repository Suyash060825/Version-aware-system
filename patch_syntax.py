with open('policy-ledger-v2/rag/llm_provider.py', 'r') as f:
    content = f.read()

import re
content = re.sub(r'                fallback=False\n            \)\n            \)', r'                fallback=False\n            )', content)

with open('policy-ledger-v2/rag/llm_provider.py', 'w') as f:
    f.write(content)

