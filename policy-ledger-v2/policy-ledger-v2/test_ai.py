from app import create_app
from rag.chatbot.chat_service import answer
app = create_app()
with app.app_context():
    res = answer("What is the remote work policy?", "Engineering", "test-session")
    print("AI RESPONSE KEYS:", res.keys())
    if "text" in res:
        print("AI RESPONSE:", res["text"])
    elif "answer" in res:
        print("AI RESPONSE:", res["answer"])
