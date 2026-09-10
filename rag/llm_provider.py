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
        timeout: Optional[int] = None
    ):
        raw_url = (
            base_url
            or os.environ.get("LOCAL_LLM_BASE_URL")
            or os.environ.get("OLLAMA_BASE_URL")
            or os.environ.get("OLLAMA_URL", "http://localhost:11434")
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
            or os.environ.get("OLLAMA_MODEL", "qwen3:4b-q4_K_M")
        )
        self.api_key = os.environ.get("OLLAMA_API_KEY", "")
        self.timeout = timeout if timeout is not None else (2.0, 3.5)
        import requests
        self._session = requests.Session()

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

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature
            }
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
            return fallback_resp

    def embed(self, texts: List[str]) -> List[List[float]]:
        from rag.embeddings.embedder import get_embedder
        try:
            embedder = get_embedder()
            return embedder.embed(texts)
        except Exception as e:
            logger.error(f"[OllamaProvider] Error generating embeddings: {e}")
            return []

    def health_check(self) -> bool:
        endpoint = f"{self.base_url}/api/version"
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        try:
            req = urllib.request.Request(endpoint, headers=headers)
            with urllib.request.urlopen(req, timeout=5) as resp:  # nosec B310
                return resp.status == 200
        except Exception as e:
            logger.debug(f"[OllamaProvider] Health check failed: {e}")
            return False


class LMStudioProvider(OllamaProvider):
    """
    Provider for LM Studio local server (http://localhost:1234/v1 by default).
    Configurable via LMSTUDIO_BASE_URL and LOCAL_LLM_MODEL.
    """
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
        """Auto-detect the first loaded model from LM Studio /v1/models."""
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
        if not self.api_key:
            logger.warning("[GeminiProvider] No API key set. Falling back to ExtractiveProvider.")
            return ExtractiveProvider().generate(prompt, system=system)

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

        # 2. OpenRouter API via OPENROUTER_API_KEY
        try:
            from openai import OpenAI
            client = OpenAI(base_url=self.base_url, api_key=self.api_key)
            
            if isinstance(prompt, str):
                messages = []
                if system:
                    messages.append({"role": "system", "content": system})
                messages.append({"role": "user", "content": prompt})
            else:
                messages = prompt
                if system and not any(m.get("role") == "system" for m in messages):
                    messages = [{"role": "system", "content": system}] + messages

            resp = client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            content = resp.choices[0].message.content.strip()
            usage = {
                "prompt_tokens": getattr(resp.usage, "prompt_tokens", 0),
                "completion_tokens": getattr(resp.usage, "completion_tokens", 0)
            } if hasattr(resp, "usage") and resp.usage else {}

            return LLMResponse(
                text=content,
                raw_response=None,
                model=self.model,
                usage=usage,
                fallback=False
            )
        except Exception as e:
            logger.error(f"[GeminiProvider] Error generating completion: {e}")
            fallback_resp = ExtractiveProvider().generate(prompt, system=system)
            fallback_resp.error = f"Gemini error: {str(e)}"
            return fallback_resp

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

    def health_check(self) -> bool:
        return self.primary.health_check() or self.secondary.health_check()



# Cache provider instance
_provider_instance: Optional[LLMProvider] = None


def get_llm_provider(force_reload: bool = False) -> LLMProvider:
    """
    Factory function returning the configured LLMProvider instance.
    Checks environment variable LLM_BACKEND ('ollama', 'vllm', 'gemini', 'extractive').
    """
    global _provider_instance
    if _provider_instance and not force_reload:
        return _provider_instance

    backend = os.environ.get("LLM_BACKEND", os.environ.get("LLM_PROVIDER", "cascade")).lower().strip()

    if backend == "cascade":
        logger.info("[LLMProvider] Initializing CascadeProvider (LMStudio -> Gemini)")
        primary = LMStudioProvider()
        secondary = GeminiProvider()
        _provider_instance = CascadeProvider(primary, secondary)
    elif backend == "ollama":
        logger.info("[LLMProvider] Initializing OllamaProvider")
        _provider_instance = OllamaProvider(timeout=10)
    elif backend == "vllm":
        logger.info("[LLMProvider] Initializing OllamaProvider")
        _provider_instance = OllamaProvider()
    elif backend == "lmstudio":
        logger.info("[LLMProvider] Initializing LMStudioProvider")
        provider = LMStudioProvider()
        if not provider.health_check():
            logger.error("[LLMProvider] LM Studio health check FAILED — is LM Studio running at %s?", provider.base_url)
        _provider_instance = provider
    elif backend == "gemini":
        logger.info("[LLMProvider] Initializing GeminiProvider")
        _provider_instance = GeminiProvider()
    elif backend == "extractive":
        logger.info("[LLMProvider] Initializing ExtractiveProvider")
        _provider_instance = ExtractiveProvider()
    else:
        logger.warning(f"[LLMProvider] Unknown backend '{backend}'. Auto-detecting best provider...")
        # Check if LM Studio is available, else Gemini if key present, else Extractive
        lmstudio = LMStudioProvider()
        if lmstudio.health_check():
            _provider_instance = lmstudio
        elif os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENROUTER_API_KEY"):
            _provider_instance = GeminiProvider()
        else:
            _provider_instance = ExtractiveProvider()

    return _provider_instance
