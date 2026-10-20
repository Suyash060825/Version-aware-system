"""
rag/generation/qwen.py
Qwen local provider connecting to Ollama with structured JSON response extraction.
"""
import json
import logging
from typing import Optional, Dict, Any
from rag.generation.provider import OllamaProvider
from rag.generation.prompts import SYSTEM_POLICY_GROUNDING_PROMPT, build_grounded_qa_prompt

logger = logging.getLogger("rag.generation.qwen")

class QwenLocalProvider(OllamaProvider):
    def _get_core_provider(self):
        try:
            from rag.llm_provider import get_llm_provider
            return get_llm_provider()
        except Exception:
            return None

    def health_check(self) -> bool:
        if super().health_check():
            return True
        core = self._get_core_provider()
        if core and core.health_check():
            return True
        return False

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Optional[str]:
        if super().health_check():
            res = super().generate(prompt, system_prompt)
            if res:
                return res
        core = self._get_core_provider()
        if core and core.health_check():
            try:
                resp = core.generate(prompt, system=system_prompt)
                if resp and not (getattr(resp, "fallback", False) or getattr(resp, "error", None)):
                    return resp.text
            except Exception as e:
                logger.debug(f"Core LLM provider generation failed: {e}")
        return None

    def stream(self, prompt: str, system_prompt: Optional[str] = None):
        if super().health_check():
            has_tokens = False
            for tok in super().stream(prompt, system_prompt):
                has_tokens = True
                yield tok
            if has_tokens:
                return
        core = self._get_core_provider()
        if core and core.health_check():
            try:
                resp = core.generate(prompt, system=system_prompt)
                if resp and not (getattr(resp, "fallback", False) or getattr(resp, "error", None)):
                    words = resp.text.split(" ")
                    for i, w in enumerate(words):
                        yield w if i == len(words) - 1 else w + " "
            except Exception as e:
                logger.debug(f"Core LLM provider streaming failed: {e}")

    def generate_grounded_answer(self, query: str, chunks: list) -> Optional[Dict[str, Any]]:
        prompt = build_grounded_qa_prompt(query, chunks)
        raw_output = self.generate(prompt, system_prompt=SYSTEM_POLICY_GROUNDING_PROMPT)
        if not raw_output:
            return None

        # Attempt to parse structured JSON
        try:
            cleaned = raw_output.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            parsed = json.loads(cleaned)
            if isinstance(parsed, dict) and "answer" in parsed:
                return parsed
        except Exception:
            pass

        # Fallback to raw text
        return {
            "answer": raw_output,
            "reasoning_summary": "Extracted from local LLM response.",
            "used_evidence_ids": [c.get("chunk_id") for c in chunks if c.get("chunk_id")],
            "needs_clarification": False
        }

_QWEN_PROVIDER = None

def get_qwen_provider() -> QwenLocalProvider:
    global _QWEN_PROVIDER
    if _QWEN_PROVIDER is None:
        _QWEN_PROVIDER = QwenLocalProvider()
    return _QWEN_PROVIDER
