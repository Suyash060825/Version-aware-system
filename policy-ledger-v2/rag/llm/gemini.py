"""
rag/llm/gemini.py
Backwards compatibility shim delegating to rag.llm_provider.
"""
from rag.llm_provider import (
    get_llm_provider as get_llm,
    get_llm_provider,
    GeminiProvider as GeminiClient,
    OllamaProvider as OllamaClient,
    VLLMProvider,
    ExtractiveProvider as ExtractiveClient,
    LLMProvider,
    LLMResponse,
)

__all__ = [
    "get_llm",
    "get_llm_provider",
    "GeminiClient",
    "OllamaClient",
    "VLLMProvider",
    "ExtractiveClient",
    "LLMProvider",
    "LLMResponse",
]
