import os
os.environ["FLASK_ENV"] = "development"
os.environ["LLM_BACKEND"] = "extractive"
from app import create_app
from rag.chatbot.chat_service import answer
import rag.chatbot.chat_service as chat_service

app = create_app()
with app.app_context():
    # Let's call answer but mock provider.generate
    orig_answer = chat_service.answer
    print("Testing pipeline with extractive...")
    res = orig_answer("How many paid leave days do I get?", session_id="test2", user_role="employee", user_department="Human Resources")
    print("FINAL ANSWER:", res)
