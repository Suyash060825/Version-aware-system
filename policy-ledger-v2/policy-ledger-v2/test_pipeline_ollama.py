import os
os.environ["FLASK_ENV"] = "development"
os.environ["LLM_BACKEND"] = "ollama"
# Try using the actual OllamaProvider
from app import create_app
from rag.chatbot.chat_service import answer

app = create_app()
with app.app_context():
    print("Testing pipeline with Ollama...")
    res = answer("How many paid leave days do I get?", session_id="test_ollama", user_role="employee", user_department="Human Resources")
    print("FINAL ANSWER:", res)
