import requests
import json
import os
from typing import Optional

class QwenLocalProvider:
    """
    Connects to local Ollama running qwen3:4b-q4_K_M.
    """
    def __init__(self, base_url=os.environ.get("LOCAL_LLM_BASE_URL", "http://localhost:11434")):
        self.base_url = base_url
        self.model = "qwen2.5-coder:1.5b" # Or whichever small fast model is available
        # The prompt requested qwen3:4b-q4_K_M. Ollama naming conventions might just be qwen2.5 or qwen.
        # We will use the model specified in environment or default to a known good one.
        import os
        self.model = os.environ.get("LOCAL_LLM_MODEL", "qwen3:4b-q4_K_M")

    def generate(self, prompt: str) -> Optional[str]:
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 256
                    }
                },
                timeout=30
            )
            response.raise_for_status()
            return response.json().get("response", "").strip()
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Ollama generation failed: {e}")
            return None
