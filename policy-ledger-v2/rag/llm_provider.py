"""
rag/llm_provider.py
Abstract LLM Provider interface and concrete implementations for Ollama, vLLM, Gemini, and Extractive fallback.
"""
from abc import ABC, abstractmethod
import os
import json
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import urllib.request
import urllib.error

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


class OllamaProvider(LLMProvider):
    """
    Provider for local Ollama server (http://localhost:11434 by default).
    Configurable via OLLAMA_BASE_URL and LOCAL_LLM_MODEL / OLLAMA_MODEL.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 180
    ):
        self.base_url = (
            base_url
            or os.environ.get("OLLAMA_BASE_URL")
            or os.environ.get("OLLAMA_URL", "http://localhost:11434")
        ).rstrip("/")
        self.model = (
            model
            or os.environ.get("LOCAL_LLM_MODEL")
            or os.environ.get("OLLAMA_MODEL", "llama3.1:8b-instruct-q4_K_M")
        )
        self.timeout = timeout

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
        import requests
        if not hasattr(self, "_session"):
            self._session = requests.Session()
            
        endpoint = f"{self.base_url}/api/chat"
        
        if isinstance(prompt, str):
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
        else:
            messages = prompt
            if system and not any(m.get("role") == "system" for m in messages):
                messages = [{"role": "system", "content": system}] + messages

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature
            }
        }

        try:
            resp = self._session.post(
                endpoint,
                json=payload,
                timeout=self.timeout
            )
            resp.raise_for_status()
            data = resp.json()
            content = data.get("message", {}).get("content", "").strip()
            eval_count = data.get("eval_count", 0)
            prompt_eval_count = data.get("prompt_eval_count", 0)
            
            return LLMResponse(
                text=content,
                raw_response=data,
                model=self.model,
                usage={"prompt_tokens": prompt_eval_count, "completion_tokens": eval_count},
                fallback=False
            )
        except Exception as e:
            logger.error(f"[OllamaProvider] Error generating completion: {e}")
            # Fallback to extractive
            fallback_resp = ExtractiveProvider().generate(prompt, system=system)
            fallback_resp.error = f"Ollama error: {str(e)}"
            return fallback_resp

    def embed(self, texts: List[str]) -> List[List[float]]:
        endpoint = f"{self.base_url}/api/embed"
        embeddings = []
        try:
            payload = {"model": self.model, "input": texts}
            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # nosec B310
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("embeddings", [])
        except Exception as e:
            logger.error(f"[OllamaProvider] Error creating embeddings: {e}")
            return []

    def health_check(self) -> bool:
        endpoint = f"{self.base_url}/api/tags"
        try:
            req = urllib.request.Request(endpoint, headers={"User-Agent": "PolicyLedger/1.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:  # nosec B310
                return resp.status == 200
        except Exception as e:
            logger.warning(f"[OllamaProvider] Health check failed: {e}")
            return False


class VLLMProvider(LLMProvider):
    """
    Provider for vLLM OpenAI-compatible endpoint (http://localhost:8000/v1 by default).
    Configurable via VLLM_BASE_URL and LOCAL_LLM_MODEL / VLLM_MODEL.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = 60
    ):
        self.base_url = (
            base_url
            or os.environ.get("VLLM_BASE_URL")
            or "http://localhost:8000/v1"
        ).rstrip("/")
        self.model = (
            model
            or os.environ.get("LOCAL_LLM_MODEL")
            or os.environ.get("VLLM_MODEL", "meta-llama/Meta-Llama-3.1-8B-Instruct")
        )
        self.api_key = api_key or os.environ.get("VLLM_API_KEY", "EMPTY")
        self.timeout = timeout

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
        import requests
        if not hasattr(self, "_session"):
            self._session = requests.Session()
            
        endpoint = f"{self.base_url}/chat/completions"

        if isinstance(prompt, str):
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
        else:
            messages = prompt
            if system and not any(m.get("role") == "system" for m in messages):
                messages = [{"role": "system", "content": system}] + messages

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream
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
            usage = data.get("usage", {})
            return LLMResponse(
                text=content,
                raw_response=data,
                model=self.model,
                usage=usage,
                fallback=False
            )
        except Exception as e:
            logger.error(f"[VLLMProvider] Error generating completion: {e}")
            fallback_resp = ExtractiveProvider().generate(prompt, system=system)
            fallback_resp.error = f"vLLM error: {str(e)}"
            return fallback_resp

    def embed(self, texts: List[str]) -> List[List[float]]:
        endpoint = f"{self.base_url}/embeddings"
        payload = {"model": self.model, "input": texts}
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        try:
            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # nosec B310
                data = json.loads(resp.read().decode("utf-8"))
                return [d["embedding"] for d in data.get("data", [])]
        except Exception as e:
            logger.error(f"[VLLMProvider] Error generating embeddings: {e}")
            return []

    def health_check(self) -> bool:
        endpoint = f"{self.base_url}/models"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            req = urllib.request.Request(endpoint, headers=headers)
            with urllib.request.urlopen(req, timeout=5) as resp:  # nosec B310
                return resp.status == 200
        except Exception as e:
            logger.warning(f"[VLLMProvider] Health check failed: {e}")
            return False


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

        excerpts_match = re.search(r"POLICY EXCERPTS:\n\n(.+?)\n\nQUESTION:", user_msg, re.DOTALL)
        question_match = re.search(r"QUESTION: (.+)", user_msg)

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

        blocks = excerpts_match.group(1).split("---")
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


# Cache provider instance
_provider_instance: Optional[LLMProvider] = None


def get_llm_provider(force_reload: bool = False) -> LLMProvider:
    global _provider_instance
    if _provider_instance and not force_reload:
        return _provider_instance

    backend = os.environ.get("LLM_BACKEND", "ollama").lower().strip()

    if backend == "vllm":
        logger.info("[LLMProvider] Initializing VLLMProvider")
        _provider_instance = VLLMProvider()
    elif backend == "extractive":
        logger.info("[LLMProvider] Initializing ExtractiveProvider")
        _provider_instance = ExtractiveProvider()
    else:
        logger.info("[LLMProvider] Initializing OllamaProvider")
        _provider_instance = OllamaProvider(timeout=180)

    return _provider_instance

    backend = os.environ.get("LLM_BACKEND", os.environ.get("LLM_PROVIDER", "cascade")).lower().strip()

    if backend == "cascade":
        logger.info("[LLMProvider] Initializing CascadeProvider (Ollama -> Gemini)")
        primary = OllamaProvider()
        secondary = GeminiProvider()
        _provider_instance = CascadeProvider(primary, secondary)
    elif backend == "ollama":
        logger.info("[LLMProvider] Initializing OllamaProvider")
        _provider_instance = OllamaProvider(timeout=180)
    elif backend == "vllm":
        logger.info("[LLMProvider] Initializing VLLMProvider")
        _provider_instance = VLLMProvider()
    elif backend == "gemini":
        logger.info("[LLMProvider] Initializing GeminiProvider")
        _provider_instance = GeminiProvider()
    elif backend == "extractive":
        logger.info("[LLMProvider] Initializing ExtractiveProvider")
        _provider_instance = ExtractiveProvider()
    else:
        logger.warning(f"[LLMProvider] Unknown backend '{backend}'. Auto-detecting best provider...")
        # Check if Ollama is available, else Gemini if key present, else Extractive
        ollama = OllamaProvider()
        if ollama.health_check():
            _provider_instance = ollama
        elif os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENROUTER_API_KEY"):
            _provider_instance = GeminiProvider()
        else:
            _provider_instance = ExtractiveProvider()

    return _provider_instance
