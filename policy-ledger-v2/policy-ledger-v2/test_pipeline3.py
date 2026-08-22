import os, sys
os.environ["FLASK_ENV"] = "development"
os.environ["LLM_BACKEND"] = "extractive"
os.environ["USE_FALLBACK_RERANKER"] = "true"
from app import create_app
from rag.chatbot.chat_service import answer
import rag.llm_provider

# Monkey patch ExtractiveProvider to print debug info
original_generate = rag.llm_provider.ExtractiveProvider.generate
def debug_generate(self, prompt, system=""):
    print("PROMPT RECEIVED:")
    print(prompt)
    import re
    excerpts_match = re.search(r"(?:POLICY EXCERPTS|RETRIEVED POLICY CHUNKS):\s*(.*?)\s*(?:QUESTION|USER QUESTION):", prompt, re.DOTALL)
    question_match = re.search(r"(?:QUESTION|USER QUESTION):\s*(.*?)(?:\n\n|$)", prompt, re.DOTALL)
    print("Excerpts Match:", bool(excerpts_match))
    print("Question Match:", bool(question_match))
    if question_match:
        print("Extracted Question:", repr(question_match.group(1)))
    
    resp = original_generate(self, prompt, system)
    print("Extractive Error:", getattr(resp, 'error', None))
    return resp

rag.llm_provider.ExtractiveProvider.generate = debug_generate

app = create_app()
with app.app_context():
    res = answer("How many paid leave days do I get?", session_id="test3", user_role="employee", user_department="Human Resources")
