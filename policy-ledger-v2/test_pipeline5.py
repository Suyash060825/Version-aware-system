import os
os.environ["FLASK_ENV"] = "development"
os.environ["LLM_BACKEND"] = "extractive"
os.environ["USE_FALLBACK_RERANKER"] = "true"
from app import create_app
from rag.chatbot.chat_service import answer
import rag.llm_provider

# Monkey patch ExtractiveProvider to print debug info
original_generate = rag.llm_provider.ExtractiveProvider.generate
def debug_generate(self, prompt, system=""):
    
    if isinstance(prompt, list):
        prompt_str = next((m["content"] for m in prompt if m["role"] == "user"), str(prompt))
    else:
        prompt_str = prompt
        
    print("PROMPT_STR:")
    print(prompt_str)
    
    import re
    excerpts_match = re.search(r"(?:POLICY EXCERPTS|RETRIEVED POLICY CHUNKS):\s*(.*?)\s*(?:QUESTION|USER QUESTION):", prompt_str, re.DOTALL)
    question_match = re.search(r"(?:QUESTION|USER QUESTION):\s*(.*?)(?:\n\n|$)", prompt_str, re.DOTALL)
    
    if question_match:
        STOP_WORDS = {
            "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
            "in", "on", "at", "to", "for", "from", "of", "with", "by", "what", "which",
            "who", "whom", "this", "that", "these", "those", "and", "or", "but", "it", "how"
        }
        q_tokens = set(w for w in re.findall(r"[a-z0-9]+", question_match.group(1).lower()) if w not in STOP_WORDS)
        print("Q_TOKENS:", q_tokens)
    
    if excerpts_match:
        raw_excerpts = excerpts_match.group(1)
        raw_excerpts = re.sub(r"</?policy_chunk[^>]*>", "---", raw_excerpts)
        blocks = raw_excerpts.split("---")
        print("BLOCKS:", len(blocks))
        best_score = 0
        for block in blocks:
            lines = block.strip().split("\n")
            body = "\n".join(lines[2:]) if len(lines) > 2 and lines[0].strip().startswith("[Excerpt") else block
            sentences = re.split(r"(?<=[.!?])\s+", body.strip())
            for s in sentences:
                s_tokens = set(re.findall(r"[a-z0-9]+", s.lower()))
                overlap = len(q_tokens & s_tokens)
                if overlap > best_score:
                    best_score = overlap
        print("BEST_SCORE:", best_score)
    
    resp = original_generate(self, prompt, system)
    return resp

rag.llm_provider.ExtractiveProvider.generate = debug_generate

app = create_app()
with app.app_context():
    res = answer("How many paid leave days do I get?", session_id="test2", user_role="employee", user_department="Human Resources")
    print("FINAL ANSWER:", res)
