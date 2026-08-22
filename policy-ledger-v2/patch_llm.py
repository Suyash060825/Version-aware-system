import re

with open('policy-ledger-v2/rag/llm_provider.py', 'r') as f:
    content = f.read()

# 1. LMStudioProvider
lmstudio_class = """class LMStudioProvider(VLLMProvider):
    \"\"\"
    Provider for LM Studio local server (http://localhost:1234/v1 by default).
    Configurable via LMSTUDIO_BASE_URL and LOCAL_LLM_MODEL.
    \"\"\"
    def __init__(self, base_url=None, model=None, timeout=600):
        resolved_base = base_url or os.environ.get("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
        resolved_model = model or os.environ.get("LOCAL_LLM_MODEL") or self._detect_model(resolved_base)
        super().__init__(
            base_url=resolved_base,
            model=resolved_model,
            api_key="lm-studio",
            timeout=timeout
        )

    @staticmethod
    def _detect_model(base_url: str) -> str:
        \"\"\"Auto-detect the first loaded model from LM Studio /v1/models.\"\"\"
        try:
            import urllib.request, json
            req = urllib.request.Request(
                f"{base_url}/models",
                headers={"Authorization": "Bearer lm-studio"}
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
                models = data.get("data", [])
                if models:
                    return models[0]["id"]
        except Exception:
            pass
        return "local-model"

    def health_check(self) -> bool:
        endpoint = f"{self.base_url}/models"
        try:
            import urllib.request
            req = urllib.request.Request(
                endpoint,
                headers={"Authorization": "Bearer lm-studio"}
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except Exception as e:
            logger.warning(f"[LMStudioProvider] Health check failed: {e}")
            return False"""

content = re.sub(
    r'class LMStudioProvider\(VLLMProvider\):.*?def __init__\(.*?\):.*?timeout=timeout\n        \)',
    lmstudio_class,
    content,
    flags=re.DOTALL
)

# 2. VLLMProvider stream and enable_thinking
vllm_replacer = """        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
            "enable_thinking": False
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }

        try:
            resp = self._session.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            resp.raise_for_status()
            data = resp.json()
            choice = data["choices"][0]
            content = choice["message"]["content"].strip()
            
            import re
            # Strip Qwen3 chain-of-thought thinking blocks
            content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
            if not content:
                raise ValueError("Empty response after stripping <think> blocks")
                
            usage = data.get("usage", {})
            return LLMResponse(
                text=content,
                raw_response=data,
                model=self.model,
                usage=usage,
                fallback=False
            )"""

# Find exactly VLLMProvider.generate's block
# Let's slice the file into lines and replace exactly.
lines = content.split('\n')
start = -1
end = -1
for i, line in enumerate(lines):
    if line.startswith("class VLLMProvider"):
        for j in range(i, len(lines)):
            if "payload = {" in lines[j]:
                start = j
                break
        if start != -1:
            for j in range(start, len(lines)):
                if "return LLMResponse(" in lines[j] and "fallback=False" in lines[j+5]:
                    end = j + 6
                    break
        break

if start != -1 and end != -1:
    content = '\n'.join(lines[:start]) + '\n' + vllm_replacer + '\n' + '\n'.join(lines[end:])

# 3. get_llm_provider health check
repl_get = """    elif backend == "lmstudio":
        logger.info("[LLMProvider] Initializing LMStudioProvider")
        provider = LMStudioProvider()
        if not provider.health_check():
            logger.error("[LLMProvider] LM Studio health check FAILED — is LM Studio running at %s?", provider.base_url)
        _provider_instance = provider"""

content = re.sub(
    r'    elif backend == "lmstudio":\n        logger.info\("\[LLMProvider\] Initializing LMStudioProvider"\)\n        _provider_instance = LMStudioProvider\(\)',
    repl_get,
    content
)

with open('policy-ledger-v2/rag/llm_provider.py', 'w') as f:
    f.write(content)

