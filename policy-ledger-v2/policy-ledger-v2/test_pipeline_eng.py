import os
os.environ["FLASK_ENV"] = "development"
os.environ["LLM_BACKEND"] = "extractive"
os.environ["USE_FALLBACK_RERANKER"] = "true"
from app import create_app
from rag.chatbot.chat_service import answer

app = create_app()
with app.app_context():
    print("Testing pipeline for Engineering employee...")
    res = answer("How many paid leave days do I get?", session_id="test_eng", user_role="employee", user_department="Engineering")
    print("FINAL ANSWER:", res)
