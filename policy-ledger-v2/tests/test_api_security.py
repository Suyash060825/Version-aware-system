import pytest
import json
from app import create_app
from extensions import db
from models import User, ChatSession, ChatMessage

@pytest.fixture
def app():
    app = create_app("testing")
    app.config["WTF_CSRF_ENABLED"] = True
    app.config["WTF_CSRF_METHODS"] = ["POST", "PUT", "PATCH", "DELETE"]
    with app.app_context():
        db.create_all()
        u1 = User(id=1, email="user1@company.com", name="User 1")
        u2 = User(id=2, email="user2@company.com", name="User 2")
        db.session.add_all([u1, u2])
        
        c1 = ChatSession(id="sess-user1", user_id=1)
        c2 = ChatSession(id="sess-user2", user_id=2)
        db.session.add_all([c1, c2])
        
        m1 = ChatMessage(id=10, session_id="sess-user1", role="assistant", content="Answer")
        db.session.add(m1)
        
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

def login(client, user_id):
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user_id)
        # Add a CSRF token to the session
        from flask_wtf.csrf import generate_csrf
        sess["csrf_token"] = generate_csrf()

def get_csrf(client):
    with client.session_transaction() as sess:
        from flask_wtf.csrf import generate_csrf
        return generate_csrf()

def test_csrf_missing(client, app):
    login(client, 1)
    # No CSRF header
    res = client.post("/rag/api/chat", json={"query": "test"})
    assert res.status_code == 400
    assert b"CSRF" in res.data or b"token" in res.data or res.status_code == 400

def test_session_ownership_enforced(client, app):
    login(client, 1)
    token = get_csrf(client)
    headers = {"X-CSRFToken": token}
    
    # Try to use User 2's session as User 1
    res = client.post("/rag/api/chat", json={"query": "test", "session_id": "sess-user2"}, headers=headers)
    assert res.status_code == 403
    assert b"Unauthorized session_id" in res.data

def test_feedback_ownership(client, app):
    login(client, 2)
    token = get_csrf(client)
    headers = {"X-CSRFToken": token}
    
    # User 2 tries to feedback User 1's message (msg_id 10)
    res = client.post("/rag/api/feedback", json={"message_id": 10, "vote": "up"}, headers=headers)
    assert res.status_code == 403
    assert b"Unauthorized message_id" in res.data
