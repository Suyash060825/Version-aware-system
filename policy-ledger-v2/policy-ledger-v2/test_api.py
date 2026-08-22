import os
import json
os.environ["FLASK_ENV"] = "development"
os.environ["LLM_BACKEND"] = "ollama"
from app import create_app
from models import db, User
from flask_jwt_extended import create_access_token

app = create_app()
with app.app_context():
    # Login as employee
    user = User.query.filter_by(email="employee@company.com").first()
    token = create_access_token(identity=user.id)
    
    with app.test_client() as client:
        # POST to chat api
        headers = {"Authorization": f"Bearer {token}"}
        payload = {"message": "How many paid leave days do I get?", "session_id": "test_api"}
        
        print("Sending request to /api/chat...")
        resp = client.post("/api/chat", json=payload, headers=headers)
        print("Response:", resp.status_code)
        print(resp.json)
