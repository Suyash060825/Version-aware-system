import os
os.environ["FLASK_ENV"] = "development"
os.environ["LLM_BACKEND"] = "extractive"
os.environ["USE_FALLBACK_RERANKER"] = "true"
from app import create_app
from rag.chatbot.chat_service import answer

def run_test(role, dept):
    print(f"\n--- Testing Role: {role}, Dept: {dept} ---")
    res = answer("How many paid leave days do I get?", session_id=f"test_{role}_{dept}", user_role=role, user_department=dept)
    print("Chunks used:", res.get("chunks_used"))
    print("Answer:", res.get("answer"))

app = create_app()
with app.app_context():
    run_test("hr", "")
    run_test("admin", "")
    run_test("employee", "")
    run_test("employee", "Engineering")
