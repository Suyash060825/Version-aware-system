"""
rag/generation/provider.py
Abstract LocalLLMProvider interface with unified factory.
"""
import os
import json
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

logger = logging.getLogger("rag.generation.provider")

class LocalLLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Optional[str]:
        pass

    def stream(self, prompt: str, system_prompt: Optional[str] = None):
        """Default fallback generator yielding the full response."""
        res = self.generate(prompt, system_prompt)
        if res:
            yield res

    @abstractmethod
    def health_check(self) -> bool:
        pass

class OllamaProvider(LocalLLMProvider):
    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        self.base_url = base_url or os.environ.get("LOCAL_LLM_BASE_URL", "http://localhost:11434")
        self.model = model or os.environ.get("LOCAL_LLM_MODEL", "qwen3:4b-q4_K_M")
        self.timeout = int(os.environ.get("LLM_TIMEOUT", "6"))
        self._last_health_time = 0
        self._is_healthy = None

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Optional[str]:
        import requests, time
        # Fast check if server is available
        if self._is_healthy is False and (time.time() - self._last_health_time < 30):
            return None

        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": int(os.environ.get("LLM_MAX_NEW_TOKENS", "256"))
                }
            }
            if system_prompt:
                payload["system"] = system_prompt

            resp = requests.post(f"{self.base_url}/api/generate", json=payload, timeout=(2.0, float(self.timeout)))
            resp.raise_for_status()
            data = resp.json()
            self._is_healthy = True
            self._last_health_time = time.time()
            return data.get("response", "").strip()
        except Exception as e:
            self._is_healthy = False
            self._last_health_time = time.time()
            logger.warning(f"Ollama offline/busy ({self.model} at {self.base_url}): {e}. Fast failover active.")
            return None

    def stream(self, prompt: str, system_prompt: Optional[str] = None):
        import requests, json, time
        if self._is_healthy is False and (time.time() - self._last_health_time < 30):
            return

        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": True,
                "options": {
                    "temperature": 0.1,
                    "num_predict": int(os.environ.get("LLM_MAX_NEW_TOKENS", "256"))
                }
            }
            if system_prompt:
                payload["system"] = system_prompt

            with requests.post(f"{self.base_url}/api/generate", json=payload, timeout=(2.0, float(self.timeout)), stream=True) as resp:
                if resp.status_code == 200:
                    self._is_healthy = True
                    self._last_health_time = time.time()
                    for line in resp.iter_lines():
                        if line:
                            try:
                                chunk = json.loads(line.decode("utf-8"))
                                token = chunk.get("response", "")
                                if token:
                                    yield token
                            except Exception:
                                pass
        except Exception as e:
            self._is_healthy = False
            self._last_health_time = time.time()
            logger.warning(f"Ollama streaming failed: {e}")

    def health_check(self) -> bool:
        import requests, time
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=1.5)
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                # Check if model is pulled or if any model exists
                model_base = self.model.split(":")[0].lower()
                has_model = any(model_base in m.lower() for m in models) if models else False
                self._is_healthy = has_model
                self._last_health_time = time.time()
                return has_model
            self._is_healthy = False
            self._last_health_time = time.time()
            return False
        except Exception:
            self._is_healthy = False
            self._last_health_time = time.time()
            return False

_PROVIDER = None

def get_llm_provider() -> LocalLLMProvider:
    global _PROVIDER
    if _PROVIDER is None:
        backend = os.environ.get("LLM_BACKEND", "ollama").lower()
        if backend == "ollama":
            _PROVIDER = OllamaProvider()
        else:
            _PROVIDER = OllamaProvider()
    return _PROVIDER
