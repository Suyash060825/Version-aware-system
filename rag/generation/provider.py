"""
rag/generation/provider.py
Abstract LocalLLMProvider interface with unified factory.
"""
import os
import logging
from abc import ABC, abstractmethod
from typing import Optional, Iterator, List, Dict, Any
from config import Config
from rag.llm_provider import LLMProvider, LLMResponse

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


class LocalLLMProvider(LLMProvider):
    def embed(self, texts: List[str]) -> List[List[float]]:
        return []


class OllamaProvider(LocalLLMProvider):
    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: Optional[Any] = None
    ):
        raw_url = (
            base_url
            or os.environ.get("LOCAL_LLM_BASE_URL")
            or os.environ.get("OLLAMA_BASE_URL")
            or Config.OLLAMA_BASE_URL
        ).rstrip("/")
        if "://ollama:" in raw_url:
            import socket
            try:
                socket.gethostbyname("ollama")
                self.base_url = raw_url
            except Exception:
                self.base_url = raw_url.replace("://ollama:", "://localhost:")
        else:
            self.base_url = raw_url
        self.model = (
            model
            or os.environ.get("LOCAL_LLM_MODEL")
            or os.environ.get("OLLAMA_MODEL")
            or Config.LOCAL_LLM_MODEL
        )
        self.api_key = api_key or os.environ.get("OLLAMA_API_KEY", "")
        read_timeout = float(os.environ.get("LLM_TIMEOUT", str(Config.LLM_TIMEOUT)))
        self.timeout = timeout if timeout is not None else (3.0, read_timeout)
        import requests
        self._session = requests.Session()
        self._last_health_time = 0
        self._is_healthy = None
        self.positive_cache_window = 60.0
        self.negative_cache_window = 45.0

        if "://localhost:" in self.base_url or "://127.0.0.1:" in self.base_url:
            if not self._test_connection():
                alt_url = self.base_url.replace("://localhost:", "://127.0.0.1:") if "://localhost:" in self.base_url else self.base_url.replace("://127.0.0.1:", "://localhost:")
                try:
                    if self._session.get(f"{alt_url}/api/tags", timeout=(0.5, 1.0)).status_code == 200:
                        self.base_url = alt_url
                except Exception:
                    pass

    def _test_connection(self) -> bool:
        try:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            resp = self._session.get(f"{self.base_url}/api/tags", headers=headers, timeout=(1.0, 2.0))
            return resp.status_code == 200
        except Exception:
            return False

    def _ollama_options(self, num_predict: Optional[int] = None, temperature: float = 0.1) -> dict:
        """Centralized Ollama runtime configuration options."""
        options = {
            "temperature": temperature,
            "num_predict": num_predict or int(os.environ.get("LLM_MAX_NEW_TOKENS", str(Config.LLM_MAX_NEW_TOKENS))),
            "num_ctx": int(os.environ.get("OLLAMA_NUM_CTX", str(Config.OLLAMA_NUM_CTX))),
            "keep_alive": os.environ.get("OLLAMA_KEEP_ALIVE", str(Config.OLLAMA_KEEP_ALIVE)),
            "think": False,
        }
        num_thread = int(os.environ.get("OLLAMA_NUM_THREADS", str(Config.OLLAMA_NUM_THREADS)))
        if num_thread > 0:
            options["num_thread"] = num_thread
        return options

    def generate(
        self,
        prompt: str | List[Dict[str, str]],
        *,
        system: Optional[str] = None,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        num_predict: Optional[int] = None,
        temperature: float = 0.1,
        stream: bool = False,
        timeout: Optional[Any] = None,
        **kwargs
    ) -> LLMResponse:
        import time, re
        effective_system = system or system_prompt
        effective_tokens = max_tokens or num_predict
        effective_timeout = timeout or self.timeout

        if isinstance(prompt, str):
            messages = []
            if effective_system:
                messages.append({"role": "system", "content": effective_system})
            messages.append({"role": "user", "content": prompt})
        else:
            messages = list(prompt)
            if effective_system and not any(m.get("role") == "system" for m in messages):
                messages = [{"role": "system", "content": effective_system}] + messages

        options = self._ollama_options(num_predict=effective_tokens, temperature=temperature)
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "think": False,
            "options": options
        }
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            resp = self._session.post(
                f"{self.base_url}/api/chat",
                json=payload,
                headers=headers,
                timeout=effective_timeout
            )
            resp.raise_for_status()
            data = resp.json()

            content = ""
            if "message" in data and isinstance(data["message"], dict):
                content = data["message"].get("content", "").strip()
                if not content and "thinking" in data["message"]:
                    content = data["message"].get("thinking", "").strip()
            elif "choices" in data and len(data["choices"]) > 0:
                content = data["choices"][0].get("message", {}).get("content", "").strip()
            elif "response" in data:
                content = data.get("response", "").strip()

            cleaned_content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
            if cleaned_content:
                content = cleaned_content
            else:
                content = re.sub(r"</?think>", "", content).strip()

            usage = {
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0)
            }
            self._is_healthy = True
            self._last_health_time = time.time()
            return LLMResponse(
                text=content,
                raw_response=data,
                model=self.model,
                usage=usage,
                fallback=False
            )
        except Exception as e:
            logger.error(f"[OllamaProvider] Error generating completion: {e}")
            from rag.llm_provider import ExtractiveProvider
            fallback_resp = ExtractiveProvider().generate(prompt, system=effective_system)
            fallback_resp.error = f"Ollama error: {str(e)}"
            fallback_resp.fallback = True
            return fallback_resp

    def stream(
        self,
        prompt: str | List[Dict[str, str]],
        *,
        system: Optional[str] = None,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        num_predict: Optional[int] = None,
        temperature: float = 0.1,
        timeout: Optional[Any] = None,
        **kwargs
    ):
        import json, time
        now = time.time()
        if self._is_healthy is False and (now - self._last_health_time < self.negative_cache_window):
            return

        effective_system = system or system_prompt
        effective_tokens = max_tokens or num_predict
        effective_timeout = timeout or self.timeout

        if isinstance(prompt, str):
            messages = []
            if effective_system:
                messages.append({"role": "system", "content": effective_system})
            messages.append({"role": "user", "content": prompt})
        else:
            messages = list(prompt)
            if effective_system and not any(m.get("role") == "system" for m in messages):
                messages = [{"role": "system", "content": effective_system}] + messages

        options = self._ollama_options(num_predict=effective_tokens, temperature=temperature)
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "think": False,
            "options": options
        }
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        def raw_token_generator():
            try:
                with self._session.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                    headers=headers,
                    timeout=effective_timeout,
                    stream=True
                ) as resp:
                    if resp.status_code == 200:
                        self._is_healthy = True
                        self._last_health_time = time.time()
                        for line in resp.iter_lines():
                            if line:
                                try:
                                    chunk = json.loads(line.decode("utf-8"))
                                    token = ""
                                    if "message" in chunk and isinstance(chunk["message"], dict):
                                        token = chunk["message"].get("content", "")
                                    elif "response" in chunk:
                                        token = chunk.get("response", "")
                                    if token:
                                        yield token
                                except Exception:
                                    pass
            except Exception as e:
                self._is_healthy = False
                self._last_health_time = time.time()
                logger.warning(f"[OllamaProvider] Streaming failed: {e}")

        for clean_token in _suppress_think_tags(raw_token_generator()):
            yield clean_token

    def health_check(self) -> bool:
        import time
        now = time.time()
        if self._is_healthy is True and (now - self._last_health_time < self.positive_cache_window):
            return True
        if self._is_healthy is False and (now - self._last_health_time < self.negative_cache_window):
            return False

        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            resp = self._session.get(f"{self.base_url}/api/tags", headers=headers, timeout=(1.0, 2.0))
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                model_base = self.model.split(":")[0].lower().replace("_", "-")
                has_model = any(model_base in m.lower().replace("_", "-") for m in models)
                self._is_healthy = has_model
                self._last_health_time = now
                if not has_model:
                    logger.warning(f"[OllamaProvider] Ollama online but model '{self.model}' not in {models}")
                return has_model
        except Exception as e:
            for docker_host in ("ollama:11434", "host.docker.internal"):
                if docker_host in self.base_url:
                    alt_url = self.base_url.replace(docker_host, "localhost:11434")
                    try:
                        alt_resp = self._session.get(f"{alt_url}/api/tags", headers=headers, timeout=(1.0, 2.0))
                        if alt_resp.status_code == 200:
                            data = alt_resp.json()
                            models = [m.get("name", "") for m in data.get("models", [])]
                            model_base = self.model.split(":")[0].lower().replace("_", "-")
                            has_model = any(model_base in m.lower().replace("_", "-") for m in models)
                            if has_model:
                                self.base_url = alt_url
                                self._is_healthy = True
                                self._last_health_time = now
                                return True
                    except Exception:
                        pass
            self._is_healthy = False
            self._last_health_time = now
            logger.debug(f"[OllamaProvider] Health check failed: {e}")
            return False

    def embed(self, texts: List[str]) -> List[List[float]]:
        from rag.embeddings.embedder import get_embedder
        try:
            embedder = get_embedder()
            return embedder.embed(texts)
        except Exception as e:
            logger.error(f"[OllamaProvider] Error generating embeddings: {e}")
            return []

    def diagnostics(self) -> Dict[str, Any]:
        healthy = self.health_check()
        return {
            "provider": "OllamaProvider",
            "backend": "ollama",
            "model": self.model,
            "base_url": self.base_url,
            "healthy": healthy,
        }


class MockProvider(LocalLLMProvider):
    def __init__(self, response: str = "Mock verified policy answer."):
        self.response = response
        self.model = "mock-llm"

    def generate(self, prompt: Any, *args, **kwargs) -> LLMResponse:
        return LLMResponse(text=self.response, model=self.model, fallback=False)

    def stream(self, prompt: Any, *args, **kwargs):
        words = self.response.split(" ")
        for i, w in enumerate(words):
            yield w if i == len(words) - 1 else w + " "

    def health_check(self) -> bool:
        return True


class ExtractiveGenerationProvider(LocalLLMProvider):
    def __init__(self):
        self.model = "extractive"

    def generate(self, prompt: Any, *args, **kwargs) -> LLMResponse:
        return LLMResponse(text="", model=self.model, fallback=True)

    def stream(self, prompt: Any, *args, **kwargs):
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
