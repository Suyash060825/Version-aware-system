"""
rag/generation/provider.py
Abstract LocalLLMProvider interface with unified factory.
"""
import os
import logging
from abc import ABC, abstractmethod
from typing import Optional, Iterator
from config import Config

logger = logging.getLogger("rag.generation.provider")

def _suppress_think_tags(token_stream: Iterator[str]) -> Iterator[str]:
    """
    Robust state machine that suppresses everything inside <think>...</think>,
    carrying residual substrings across token boundaries.
    """
    in_think = False
    buffer = ""
    start_tag = "<think>"
    end_tag = "</think>"

    for token in token_stream:
        buffer += token
        while buffer:
            if not in_think:
                start_idx = buffer.find(start_tag)
                if start_idx != -1:
                    pre = buffer[:start_idx]
                    if pre:
                        yield pre
                    buffer = buffer[start_idx + len(start_tag):]
                    in_think = True
                    continue

                matched_prefix_len = 0
                for plen in range(min(len(buffer), len(start_tag) - 1), 0, -1):
                    if start_tag.startswith(buffer[-plen:]):
                        matched_prefix_len = plen
                        break

                if matched_prefix_len > 0:
                    emit = buffer[:-matched_prefix_len]
                    if emit:
                        yield emit
                    buffer = buffer[-matched_prefix_len:]
                    break
                else:
                    yield buffer
                    buffer = ""
                    break
            else:
                end_idx = buffer.find(end_tag)
                if end_idx != -1:
                    buffer = buffer[end_idx + len(end_tag):]
                    in_think = False
                    continue

                matched_prefix_len = 0
                for plen in range(min(len(buffer), len(end_tag) - 1), 0, -1):
                    if end_tag.startswith(buffer[-plen:]):
                        matched_prefix_len = plen
                        break

                if matched_prefix_len > 0:
                    buffer = buffer[-matched_prefix_len:]
                else:
                    buffer = ""
                break

    if not in_think and buffer:
        yield buffer


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
        raw_url = (base_url or os.environ.get("LOCAL_LLM_BASE_URL") or os.environ.get("OLLAMA_BASE_URL") or Config.OLLAMA_BASE_URL).rstrip("/")
        if "://ollama:" in raw_url:
            import socket
            try:
                socket.gethostbyname("ollama")
                self.base_url = raw_url
            except Exception:
                self.base_url = raw_url.replace("://ollama:", "://localhost:")
        else:
            self.base_url = raw_url
        self.model = model or os.environ.get("LOCAL_LLM_MODEL") or Config.LOCAL_LLM_MODEL
        self.timeout = float(os.environ.get("LLM_TIMEOUT", str(Config.LLM_TIMEOUT)))
        self.positive_cache_window = 60.0
        self.negative_cache_window = 45.0
        self._last_health_time = 0
        self._is_healthy = None

    def _ollama_options(self) -> dict:
        """Centralized Ollama runtime configuration options."""
        return {
            "temperature": 0.1,
            "num_predict": Config.LLM_MAX_NEW_TOKENS,
            "num_ctx": Config.OLLAMA_NUM_CTX,
            "num_thread": Config.OLLAMA_NUM_THREADS,
            "keep_alive": Config.OLLAMA_KEEP_ALIVE,
        }

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Optional[str]:
        import requests, time, re
        if not self.health_check():
            return None

        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": self._ollama_options()
            }
            if system_prompt:
                payload["system"] = system_prompt

            resp = requests.post(f"{self.base_url}/api/generate", json=payload, timeout=(3.0, float(self.timeout)))
            resp.raise_for_status()
            data = resp.json()
            self._is_healthy = True
            self._last_health_time = time.time()
            raw_res = data.get("response", "")
            cleaned = re.sub(r"<think>.*?</think>", "", raw_res, flags=re.DOTALL).strip()
            return cleaned
        except Exception as e:
            self._is_healthy = False
            self._last_health_time = time.time()
            logger.warning(f"Ollama offline/busy ({self.model} at {self.base_url}): {e}. Fast failover active.")
            return None

    def stream(self, prompt: str, system_prompt: Optional[str] = None):
        import requests, json, time
        if self._is_healthy is False and (time.time() - self._last_health_time < self.negative_cache_window):
            return

        def raw_token_generator():
            try:
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": True,
                    "options": self._ollama_options()
                }
                if system_prompt:
                    payload["system"] = system_prompt

                with requests.post(f"{self.base_url}/api/generate", json=payload, timeout=(3.0, float(self.timeout)), stream=True) as resp:
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
                                except Exception as parse_err:
                                    logger.debug(f"Streaming chunk JSON parse error: {parse_err}")
            except Exception as e:
                self._is_healthy = False
                self._last_health_time = time.time()
                logger.warning(f"Ollama streaming failed: {e}")

        for clean_token in _suppress_think_tags(raw_token_generator()):
            yield clean_token

    def health_check(self) -> bool:
        import requests, time
        now = time.time()
        # If recently confirmed healthy, skip round-trip (positive cache: 60s)
        if self._is_healthy is True and (now - self._last_health_time < self.positive_cache_window):
            return True
        if self._is_healthy is False and (now - self._last_health_time < self.negative_cache_window):
            return False
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=(0.3, 0.5))
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                if not models:
                    logger.error(f"Ollama is running but no models are pulled. Run: ollama pull {self.model}")
                    self._is_healthy = False
                    self._last_health_time = time.time()
                    return False

                # Check if model is pulled with case-insensitive and hyphen/underscore normalization
                model_base = self.model.split(":")[0].lower().replace("_", "-")
                has_model = any(model_base in m.lower().replace("_", "-") for m in models)
                if not has_model:
                    logger.warning(f"Ollama running but model {self.model} not found in {models}")
                self._is_healthy = has_model
                self._last_health_time = time.time()
                return has_model
            self._is_healthy = False
            self._last_health_time = time.time()
            return False
        except Exception as conn_err:
            if "ollama:11434" in self.base_url:
                try:
                    alt_url = self.base_url.replace("ollama:11434", "localhost:11434")
                    alt_resp = requests.get(f"{alt_url}/api/tags", timeout=(0.3, 0.5))
                    if alt_resp.status_code == 200:
                        self.base_url = alt_url
                        self._is_healthy = True
                        self._last_health_time = time.time()
                        return True
                except Exception:
                    pass
            logger.debug(f"LLM health check connection failed: {conn_err}")
            self._is_healthy = False
            self._last_health_time = time.time()
            return False


class MockProvider(LocalLLMProvider):
    def __init__(self, response: str = "Mock verified policy answer."):
        self.response = response
        self.model = "mock-llm"

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Optional[str]:
        return self.response

    def stream(self, prompt: str, system_prompt: Optional[str] = None):
        words = self.response.split(" ")
        for i, w in enumerate(words):
            yield w if i == len(words) - 1 else w + " "

    def health_check(self) -> bool:
        return True


class ExtractiveGenerationProvider(LocalLLMProvider):
    def __init__(self):
        self.model = "extractive"

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Optional[str]:
        return None

    def stream(self, prompt: str, system_prompt: Optional[str] = None):
        return
        yield

    def health_check(self) -> bool:
        return True


_PROVIDER = None

def get_llm_provider(force_reload: bool = False) -> LocalLLMProvider:
    global _PROVIDER
    if _PROVIDER is None or force_reload:
        backend = os.environ.get("LLM_BACKEND", "ollama").lower().strip()
        if backend in ("mock", "stub", "test"):
            _PROVIDER = MockProvider()
        elif backend in ("extractive", "offline"):
            _PROVIDER = ExtractiveGenerationProvider()
        elif backend == "ollama":
            _PROVIDER = OllamaProvider()
        else:
            _PROVIDER = OllamaProvider()
    return _PROVIDER
