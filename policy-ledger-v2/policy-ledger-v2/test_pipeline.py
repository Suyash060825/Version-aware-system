import os
os.environ["FLASK_ENV"] = "development"
from app import create_app
from rag.chatbot.chat_service import answer
app = create_app()
with app.app_context():
    res = answer("How many paid leave days do I get?", session_id="test2", user_role="employee", user_department="Human Resources")
    print("FINAL ANSWER:", res)
