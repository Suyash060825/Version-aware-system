import re

with open('policy-ledger-v2/rag/llm_provider.py', 'r') as f:
    content = f.read()

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
            return False
"""

# Replace the LMStudioProvider class
content = re.sub(
    r'class LMStudioProvider\(VLLMProvider\):.*?def __init__\(.*?\):.*?timeout=timeout\n        \)',
    lmstudio_class,
    content,
    flags=re.DOTALL
)

with open('policy-ledger-v2/rag/llm_provider.py', 'w') as f:
    f.write(content)

