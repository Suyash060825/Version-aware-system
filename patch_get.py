import re

with open('policy-ledger-v2/rag/llm_provider.py', 'r') as f:
    content = f.read()

repl = """    elif backend == "lmstudio":
        logger.info("[LLMProvider] Initializing LMStudioProvider")
        provider = LMStudioProvider()
        if not provider.health_check():
            logger.error("[LLMProvider] LM Studio health check FAILED — is LM Studio running at %s?", provider.base_url)
        _provider_instance = provider"""

content = re.sub(
    r'    elif backend == "lmstudio":\n        logger.info\("\[LLMProvider\] Initializing LMStudioProvider"\)\n        _provider_instance = LMStudioProvider\(\)',
    repl,
    content
)

with open('policy-ledger-v2/rag/llm_provider.py', 'w') as f:
    f.write(content)

