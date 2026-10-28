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

    def stream(self, prompt: str | List[Dict[str, str]], **kwargs):
        """Helper generator yielding text tokens/words for backwards compatibility."""
        resp = self.generate(prompt, **kwargs)
        if resp and resp.text:
            words = resp.text.split(" ")
            for i, w in enumerate(words):
                yield w if i == len(words) - 1 else w + " "

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


# OllamaProvider is imported lazily via __getattr__ or get_llm_provider to prevent circular import


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
    from rag.generation.provider import OllamaProvider

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
        from rag.generation.provider import OllamaProvider
        _provider_instance = OllamaProvider()

    return _provider_instance


def __getattr__(name: str):
    if name == "OllamaProvider":
        from rag.generation.provider import OllamaProvider
        return OllamaProvider
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

