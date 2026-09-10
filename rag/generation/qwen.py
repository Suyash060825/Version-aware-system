"""
rag/generation/qwen.py
Qwen local provider connecting to Ollama with structured JSON response extraction.
"""
import os
import json
import logging
from typing import Optional, Dict, Any
from rag.generation.provider import LocalLLMProvider, OllamaProvider
from rag.generation.prompts import SYSTEM_POLICY_GROUNDING_PROMPT, build_grounded_qa_prompt

logger = logging.getLogger("rag.generation.qwen")

class QwenLocalProvider(OllamaProvider):
    def generate_grounded_answer(self, query: str, chunks: list) -> Optional[Dict[str, Any]]:
        prompt = build_grounded_qa_prompt(query, chunks)
        raw_output = self.generate(prompt, system_prompt=SYSTEM_POLICY_GROUNDING_PROMPT)
        if not raw_output:
            return None

        # Attempt to parse structured JSON
        try:
            # Clean markdown codeblocks if wrapped in ```json ... ```
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
