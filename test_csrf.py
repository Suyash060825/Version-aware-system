from app import create_app
import os
os.environ["FLASK_ENV"] = "development"
app = create_app("development")
client = app.test_client()

with app.app_context():
    from models import db, User
    from flask_login import login_user
    u = db.session.query(User).filter_by(email="admin@company.com").first()
    
    @app.route('/auto_login')
    def auto_login():
        login_user(u)
        return "ok"

client.get("/auto_login")
resp = client.post("/rag/api/chat", json={"query": "hello"})
print(f"Status Code: {resp.status_code}")
print(f"Response: {resp.data}")
