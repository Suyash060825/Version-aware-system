import re

with open('policy-ledger-v2/docker-compose.prod.yml', 'r') as f:
    content = f.read()

# I will just keep the first occurrences of the duplicates
content = re.sub(
    r"      - LLM_BACKEND=\$\{LLM_BACKEND:-ollama\}\n      - LOCAL_LLM_MODEL=\$\{LOCAL_LLM_MODEL\}\n      - LMSTUDIO_BASE_URL=http://host\.docker\.internal:1234/v1\n",
    "",
    content,
    count=1
)
content = re.sub(
    r"      - HF_HOME=/app/data/huggingface\n      - LMSTUDIO_BASE_URL=http://host\.docker\.internal:1234/v1\n",
    "",
    content,
    count=1
)

with open('policy-ledger-v2/docker-compose.prod.yml', 'w') as f:
    f.write(content)
