"""
rag/llm_provider.py
Abstract LLM Provider interface and concrete implementations for Ollama, vLLM, Gemini, and Extractive fallback.
"""
from abc import ABC, abstractmethod
import os
import time
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import urllib.request
import urllib.error
from config import Config

logger = logging.getLogger("rag.llm_provider")


@dataclass
class LLMResponse:
    text: str
    raw_response: Optional[Dict[str, Any]] = None
    model: str = ""
    usage: Optional[Dict[str, Any]] = field(default_factory=dict)
    fallback: bool = False
    error: Optional[str] = None


class LLMProvider(ABC):
    """Abstract base class for all LLM providers."""

    @abstractmethod
    def generate(
        self,
        prompt: str | List[Dict[str, str]],
        *,
        system: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
        stream: bool = False,
        **kwargs
    ) -> LLMResponse:
        """
        Generate completion for a given prompt or list of chat messages.
        """

    def complete(self, prompt: str | List[Dict[str, str]], **kwargs) -> str:
        """Helper method returning string content directly for backwards compatibility."""
        return self.generate(prompt, **kwargs).text

    @abstractmethod
    def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Generate vector embeddings for a list of text strings.
        """

    @abstractmethod
    def health_check(self) -> bool:
        """
        Check if the LLM backend service is healthy and responsive.
        """

    def get_model_name(self) -> str:
        """Return the model name/identifier for the provider."""
        return getattr(self, "model", "unknown")


class OllamaProvider(LLMProvider):
    """
    Provider for local Ollama server (http://localhost:11434 by default).
    Configurable via OLLAMA_BASE_URL and LOCAL_LLM_MODEL / OLLAMA_MODEL.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: Optional[Any] = None
    ):
        raw_url = (
            base_url
            or os.environ.get("OLLAMA_BASE_URL")
            or os.environ.get("LOCAL_LLM_BASE_URL")
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
        self.negative_cache_window = 30.0

    def generate(
        self,
        prompt: str | List[Dict[str, str]],
        *,
        system: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
        stream: bool = False,
        **kwargs
    ) -> LLMResponse:
        endpoint = f"{self.base_url}/api/chat"
        
        if isinstance(prompt, str):
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
        else:
            messages = list(prompt)
            if system and not any(m.get("role") == "system" for m in messages):
                messages = [{"role": "system", "content": system}] + messages

        options = {
            "num_predict": max_tokens or int(os.environ.get("LLM_MAX_NEW_TOKENS", "512")),
            "temperature": temperature,
            "num_ctx": int(os.environ.get("OLLAMA_NUM_CTX", "4096")),
            "keep_alive": os.environ.get("OLLAMA_KEEP_ALIVE", "10m"),
        }
        num_thread = int(os.environ.get("OLLAMA_NUM_THREADS", "0"))
        if num_thread > 0:
            options["num_thread"] = num_thread

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
                endpoint,
                json=payload,
                headers=headers,
                timeout=self.timeout
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
            
            import re
            # Strip Qwen3 chain-of-thought thinking blocks
            cleaned_content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
            if cleaned_content:
                content = cleaned_content
            else:
                # If model only returned thinking tags, extract inner thinking as answer
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
            fallback_resp = ExtractiveProvider().generate(prompt, system=system)
            fallback_resp.error = f"Ollama error: {str(e)}"
            fallback_resp.fallback = True
            return fallback_resp

    def stream(
        self,
        prompt: str | List[Dict[str, str]],
        *,
        system: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
        **kwargs
    ):
        """Stream tokens from Ollama with think tag suppression."""
        import json, re, time
        if self._is_healthy is False and (time.time() - self._last_health_time < self.negative_cache_window):
            return

        endpoint = f"{self.base_url}/api/chat"
        if isinstance(prompt, str):
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
        else:
            messages = list(prompt)
            if system and not any(m.get("role") == "system" for m in messages):
                messages = [{"role": "system", "content": system}] + messages

        options = {
            "num_predict": max_tokens or int(os.environ.get("LLM_MAX_NEW_TOKENS", "512")),
            "temperature": temperature,
            "num_ctx": int(os.environ.get("OLLAMA_NUM_CTX", "4096")),
            "keep_alive": os.environ.get("OLLAMA_KEEP_ALIVE", "10m"),
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": options
        }
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        def raw_token_generator():
            try:
                with self._session.post(endpoint, json=payload, headers=headers, timeout=self.timeout, stream=True) as resp:
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

        # Suppress <think> tags
        in_think = False
        buffer = ""
        start_tag = "<think>"
        end_tag = "</think>"
        for token in raw_token_generator():
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

    def embed(self, texts: List[str]) -> List[List[float]]:
        from rag.embeddings.embedder import get_embedder
        try:
            embedder = get_embedder()
            return embedder.embed(texts)
        except Exception as e:
            logger.error(f"[OllamaProvider] Error generating embeddings: {e}")
            return []

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
            # Fallback for host execution if Docker hostname was configured
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

    def diagnostics(self) -> Dict[str, Any]:
        healthy = self.health_check()
        return {
            "provider": "OllamaProvider",
            "model": self.model,
            "base_url": self.base_url,
            "healthy": healthy,
            "timeout": self.timeout,
            "backend": "ollama",
        }


class GeminiProvider(LLMProvider):
    """
    Provider for Google Gemini API or OpenRouter endpoint.
    Configurable via GEMINI_API_KEY or OPENROUTER_API_KEY.
    """

    def __init__(self, model: Optional[str] = None):
        self.gemini_api_key = os.environ.get("GEMINI_API_KEY", "")
        self.openrouter_api_key = os.environ.get("OPENROUTER_API_KEY", "")
        self.api_key = self.openrouter_api_key or self.gemini_api_key
        self.model = model or os.environ.get("LLM_MODEL") or ("gemini-2.0-flash" if self.gemini_api_key and not self.openrouter_api_key else "google/gemini-2.0-flash-001")
        self.base_url = "https://openrouter.ai/api/v1"

    def generate(
        self,
        prompt: str | List[Dict[str, str]],
        *,
        system: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
        stream: bool = False,
        **kwargs
    ) -> LLMResponse:
        raise RuntimeError(
            "[Security Policy Violation] External cloud LLM inference APIs (OpenAI/OpenRouter/Gemini) "
            "are disabled. Veritas must execute using local Ollama models (qwen3:4b-q4_K_M)."
        )

        # 1. Native Google Generative AI API via GEMINI_API_KEY
        if self.gemini_api_key and not self.openrouter_api_key:
            try:
                import urllib.request
                import json
                
                model_name = self.model if "gemini" in self.model else "gemini-2.0-flash"
                if "/" in model_name:
                    model_name = model_name.split("/")[-1]
                
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.gemini_api_key}"
                
                user_text = prompt if isinstance(prompt, str) else "\n".join([m.get("content", "") for m in prompt if m.get("role") != "system"])
                payload = {
                    "contents": [{"parts": [{"text": user_text}]}],
                    "generationConfig": {
                        "temperature": temperature,
                        "maxOutputTokens": max_tokens
                    }
                }
                if system:
                    payload["systemInstruction"] = {"parts": [{"text": system}]}
                
                data = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=30) as resp:
                    res_json = json.loads(resp.read().decode("utf-8"))
                    text = res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
                    return LLMResponse(text=text, model=model_name, fallback=False)
            except Exception as e:
                logger.error(f"[GeminiProvider] Native Google API error: {e}")
                # Try fallback to OpenAI/OpenRouter if available below

        # Cloud inference APIs are strictly prohibited in Veritas local deployment
        raise RuntimeError(
            "[Security Policy Violation] External cloud LLM inference APIs (OpenAI/OpenRouter/Gemini) "
            "are disabled. Veritas must execute using local Ollama models (qwen3:4b-q4_K_M)."
        )

    def embed(self, texts: List[str]) -> List[List[float]]:
        # Fall back or return empty if not supported
        return []

    def health_check(self) -> bool:
        return bool(self.api_key)


class ExtractiveProvider(LLMProvider):
    """
    Zero-dependency non-AI extractive fallback provider.
    Extracts relevant sentence directly from prompt excerpts when LLM is unavailable
    or relevance threshold is low.
    """

    REFUSAL = "I couldn't find this information in the available policies."

    def generate(
        self,
        prompt: str | List[Dict[str, str]],
        *,
        system: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
        stream: bool = False,
        **kwargs
    ) -> LLMResponse:
        import re

        user_msg = ""
        if isinstance(prompt, str):
            user_msg = prompt
        elif isinstance(prompt, list):
            user_msg = next((m["content"] for m in reversed(prompt) if m.get("role") == "user"), "")

        excerpts_match = re.search(r"(?:POLICY EXCERPTS|RETRIEVED POLICY CHUNKS):\s*(.*?)\s*(?:QUESTION|USER QUESTION):", user_msg, re.DOTALL)
        question_match = re.search(r"(?:QUESTION|USER QUESTION):\s*(.*?)(?:\n\n|$)", user_msg, re.DOTALL)

        if not excerpts_match or not question_match:
            return LLMResponse(
                text=self.REFUSAL,
                model="extractive-fallback",
                fallback=True
            )

        STOP_WORDS = {
            "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
            "in", "on", "at", "to", "for", "from", "of", "with", "by", "what", "which",
            "who", "whom", "this", "that", "these", "those", "and", "or", "but", "it", "how"
        }
        q_tokens = set(w for w in re.findall(r"[a-z0-9]+", question_match.group(1).lower()) if w not in STOP_WORDS)
        best_sentence, best_score = "", 0

        raw_excerpts = excerpts_match.group(1)
        raw_excerpts = re.sub(r"</?policy_chunk[^>]*>", "---", raw_excerpts)
        blocks = raw_excerpts.split("---")
        for block in blocks:
            lines = block.strip().split("\n")
            body = "\n".join(lines[2:]) if len(lines) > 2 and lines[0].strip().startswith("[Excerpt") else block
            sentences = re.split(r"(?<=[.!?])\s+", body.strip())
            for s in sentences:
                s = s.strip()
                if not s:
                    continue
                s_words = set(w for w in re.findall(r"[a-z0-9]+", s.lower()) if w not in STOP_WORDS)
                score = len(s_words & q_tokens)
                if score > best_score:
                    best_sentence, best_score = s, score

        result_text = best_sentence if (best_score > 0 and best_sentence) else self.REFUSAL
        return LLMResponse(
            text=result_text,
            model="extractive-fallback",
            fallback=True
        )

    def embed(self, texts: List[str]) -> List[List[float]]:
        return []

    def health_check(self) -> bool:
        return True


class CascadeProvider(LLMProvider):
    def __init__(self, primary: LLMProvider, secondary: LLMProvider):
        self.primary = primary
        self.secondary = secondary
        self.extractive = ExtractiveProvider()
        
        # Circuit breaker state for primary provider
        self.cb_state = "closed" # closed, open, half-open
        self.cb_failures = 0
        self.cb_max_failures = 3
        self.cb_last_failure_time = 0
        self.cb_reset_timeout = 60 # seconds

    def _execute_with_retry(self, provider: LLMProvider, max_retries: int, prompt, **kwargs):
        import time
        last_err = None
        for attempt in range(max_retries):
            resp = provider.generate(prompt, **kwargs)
            if not (resp.fallback or resp.error):
                return resp
            last_err = resp
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt) # Exponential backoff
        return last_err

    def generate(
        self,
        prompt: str | List[Dict[str, str]],
        *,
        system: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
        stream: bool = False,
        use_secondary: bool = False,
        **kwargs
    ) -> LLMResponse:
        import time
        from rag.metrics import LLM_REQUESTS, LLM_LATENCY
        
        logger.info(f"[CascadeProvider] Routing request: use_secondary={use_secondary}")
        
        # Check circuit breaker state
        if self.cb_state == "open":
            if time.time() - self.cb_last_failure_time > self.cb_reset_timeout:
                self.cb_state = "half-open"
            else:
                logger.warning("[CascadeProvider] Primary circuit is OPEN. Forcing secondary.")
                use_secondary = True

        provider = self.secondary if use_secondary else self.primary
        backend_name = provider.__class__.__name__
        
        LLM_REQUESTS.labels(backend=backend_name).inc()
        start_time = time.time()
        
        # Execute with retry
        resp = self._execute_with_retry(provider, max_retries=2, prompt=prompt, system=system, max_tokens=max_tokens, temperature=temperature, stream=stream)
        
        LLM_LATENCY.labels(backend=backend_name).observe(time.time() - start_time)
        
        # Update circuit breaker
        if not use_secondary:
            if resp.fallback or resp.error:
                self.cb_failures += 1
                self.cb_last_failure_time = time.time()
                if self.cb_failures >= self.cb_max_failures or self.cb_state == "half-open":
                    self.cb_state = "open"
            else:
                if self.cb_state == "half-open":
                    self.cb_state = "closed"
                    self.cb_failures = 0
        
        if resp.fallback or resp.error:
            logger.warning(f"[CascadeProvider] {provider.__class__.__name__} failed. Falling back.")
            alt_provider = self.primary if use_secondary else self.secondary
            if self.cb_state == "open" and alt_provider == self.primary:
                # Do not try primary if circuit is open
                alt_resp = resp
            else:
                alt_resp = self._execute_with_retry(alt_provider, max_retries=2, prompt=prompt, system=system, max_tokens=max_tokens, temperature=temperature, stream=stream)
            
            if alt_resp.fallback or alt_resp.error:
                logger.warning("[CascadeProvider] Both backends failed. Using Extractive.")
                resp = self.extractive.generate(prompt, system=system, max_tokens=max_tokens, temperature=temperature, stream=stream)
            else:
                resp = alt_resp
        return resp

    def embed(self, texts: List[str]) -> List[List[float]]:
        res = self.primary.embed(texts)
        if not res:
            res = self.secondary.embed(texts)
        return res

    def stream(self, prompt: str | List[Dict[str, str]], **kwargs):
        resp = self.generate(prompt, **kwargs)
        if resp and resp.text:
            words = resp.text.split(" ")
            for i, w in enumerate(words):
                yield w if i == len(words) - 1 else w + " "

    def health_check(self) -> bool:
        return self.primary.health_check() or self.secondary.health_check()



class MockLLMProvider(LLMProvider):
    def __init__(self, default_text: str = "Mock verified LLM response for policy audit."):
        self.default_text = default_text
        self.model = "mock-llm"

    def generate(
        self,
        prompt: str | List[Dict[str, str]],
        *,
        system: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
        stream: bool = False,
        **kwargs
    ) -> LLMResponse:
        return LLMResponse(
            text=self.default_text,
            model=self.model,
            fallback=False
        )

    def embed(self, texts: List[str]) -> List[List[float]]:
        return [[0.0] * 384 for _ in texts]

    def health_check(self) -> bool:
        return True


# Cache provider instance
_provider_instance: Optional[LLMProvider] = None


def get_llm_provider(force_reload: bool = False) -> LLMProvider:
    """
    Factory function returning the configured LLMProvider instance.
    Checks environment variable LLM_BACKEND ('ollama', 'vllm', 'gemini', 'extractive', 'mock').
    """
    global _provider_instance
    if _provider_instance and not force_reload:
        return _provider_instance

    backend = os.environ.get("LLM_BACKEND", os.environ.get("LLM_PROVIDER", "ollama")).lower().strip()

    if backend in ("mock", "stub", "test"):
        logger.info("[LLMProvider] Initializing MockLLMProvider")
        _provider_instance = MockLLMProvider()
    elif backend in ("ollama", "local", "vllm"):
        logger.info("[LLMProvider] Initializing OllamaProvider with Qwen model")
        _provider_instance = OllamaProvider()
    elif backend == "extractive":
        logger.info("[LLMProvider] Initializing ExtractiveProvider")
        _provider_instance = ExtractiveProvider()
    elif backend == "gemini":
        logger.info("[LLMProvider] Initializing GeminiProvider (ablation/evaluation reference only)")
        _provider_instance = GeminiProvider()
    elif backend == "lmstudio":
        raise RuntimeError(
            "[Architecture Constraint] LM Studio integration is disabled. Veritas strictly executes "
            "local generation via Ollama (qwen3:4b-q4_K_M)."
        )
    elif backend == "cascade":
        logger.warning("[LLMProvider] CascadeProvider is deprecated in production runtime. Defaulting to OllamaProvider.")
        _provider_instance = OllamaProvider()
    else:
        logger.info(f"[LLMProvider] Defaulting to primary local OllamaProvider (backend requested: '{backend}')")
        _provider_instance = OllamaProvider()

    return _provider_instance
