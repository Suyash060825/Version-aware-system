"""rag/llm/gemini.py + ollama.py combined"""
import os, json

REFUSAL = "I couldn't find this information in the available policies."

class GeminiClient:
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENROUTER_API_KEY", "")
        self.model = os.environ.get("LLM_MODEL", "google/gemini-2.0-flash-001")
        self.base_url = "https://openrouter.ai/api/v1"

    def complete(self, messages: list[dict]) -> str:
        try:
            from openai import OpenAI
            client = OpenAI(base_url=self.base_url, api_key=self.api_key)
            resp = client.chat.completions.create(model=self.model, messages=messages, max_tokens=1024)
            return resp.choices[0].message.content.strip()
        except Exception as e:
            return f"{REFUSAL} (LLM error: {e})"


class OllamaClient:
    def __init__(self, model: str = "llama3"):
        self.model = os.environ.get("OLLAMA_MODEL", model)
        self.base_url = os.environ.get("OLLAMA_URL", "http://localhost:11434")

    def complete(self, messages: list[dict]) -> str:
        try:
            import urllib.request
            payload = json.dumps({"model": self.model, "messages": messages, "stream": False}).encode()
            req = urllib.request.Request(f"{self.base_url}/api/chat", data=payload,
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read())
                return data["message"]["content"].strip()
        except Exception as e:
            return f"{REFUSAL} (Ollama error: {e})"


class ExtractiveClient:
    """
    Zero-dependency fallback: extracts the best-matching sentence from the
    retrieved policy excerpts.

    Each excerpt block built by prompt_builder.py looks like:
        [Excerpt N]
        Policy: <name> | Version: <v> | Section: <section> | Page: <page>
        <actual policy body text...>

    Section labels routinely contain their own period ("2. Schedule"),
    which used to fool the old sentence splitter into treating the
    metadata header itself as a "sentence" — and since it repeats the
    policy name (which usually overlaps the question's own keywords,
    e.g. "remote work" appears in both the policy title and the query),
    it would out-score the real answer and get returned verbatim. This
    strips the header off each excerpt before sentence-splitting, so only
    actual policy body text is ever considered as a candidate answer.
    """
    def complete(self, messages: list[dict]) -> str:
        import re
        user_msg = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        excerpts_match = re.search(r"POLICY EXCERPTS:\n\n(.+?)\n\nQUESTION:", user_msg, re.DOTALL)
        question = re.search(r"QUESTION: (.+)", user_msg)
        if not excerpts_match or not question:
            return REFUSAL

        q_tokens = set(re.findall(r"[a-z0-9]+", question.group(1).lower()))
        best, best_score = "", -1

        for block in excerpts_match.group(1).split("---"):
            lines = block.strip().split("\n")
            # Drop the "[Excerpt N]" line and the "Policy: ... | Page: ..."
            # metadata line — only the body text below them is eligible.
            body = "\n".join(lines[2:]) if len(lines) > 2 and lines[0].strip().startswith("[Excerpt") else block
            sentences = re.split(r"(?<=[.!?])\s+", body.strip())
            for s in sentences:
                s = s.strip()
                if not s:
                    continue
                score = len(set(re.findall(r"[a-z0-9]+", s.lower())) & q_tokens)
                if score > best_score:
                    best, best_score = s, score

        return best if best_score > 0 else REFUSAL


_client = None

def get_llm():
    global _client
    if _client:
        return _client
    provider = os.environ.get("LLM_PROVIDER", "gemini").lower()
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENROUTER_API_KEY", "")
    if provider == "ollama":
        _client = OllamaClient()
        print("[LLM] Using Ollama")
    elif key:
        _client = GeminiClient()
        print("[LLM] Using Gemini via OpenRouter")
    else:
        _client = ExtractiveClient()
        print("[LLM] No API key — using extractive fallback")
    return _client
