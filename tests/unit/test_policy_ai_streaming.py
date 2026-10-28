import pytest
from app import create_app
from models import db, User, UserRole, Policy, PolicyStatus
import policy_ai

@pytest.fixture
def client_and_policy():
    app = create_app("testing")
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            admin = User(email="admin@example.com", role=UserRole.ADMIN, name="Admin")
            admin.set_password("password")
            db.session.add(admin)
            db.session.flush()

            policy = Policy(
                policy_id="POL-AI-TEST",
                title="Remote Work Policy",
                status=PolicyStatus.ACTIVE,
                author_id=admin.id,
                current_version="1.0"
            )
            db.session.add(policy)
            db.session.commit()

            yield client, policy.id, admin

            db.session.remove()
            db.drop_all()

def test_policy_ai_stream_generators(monkeypatch):
    class FakeLLM:
        def stream(self, messages):
            yield "This "
            yield "is "
            yield "streamed."

        def generate(self, messages):
            from rag.llm_provider import LLMResponse
            return LLMResponse(text="This is streamed.")

    monkeypatch.setattr(policy_ai, "get_llm", lambda: FakeLLM())

    tokens = list(policy_ai.rewrite_text_stream("Sample content", "simplify"))
    assert "".join(tokens) == "This is streamed."

    exp_tokens = list(policy_ai.explain_clause_stream("Sample policy", "Section 1 clause"))
    assert "".join(exp_tokens) == "This is streamed."

def test_writer_action_synchronous_preserved(client_and_policy, monkeypatch):
    client, policy_id, admin = client_and_policy
    client.post("/auth/login", data={"email": "admin@example.com", "password": "password"})

    import blueprints.policy_ai
    monkeypatch.setattr(blueprints.policy_ai, "rewrite_text", lambda content, mode, lang="": "Simplified policy content.")

    res = client.post(f"/admin/policies/{policy_id}/ai/writer", data={
        "mode": "simplify",
        "content": "Original policy content."
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["result"] == "Simplified policy content."

def test_writer_action_stream_endpoint(client_and_policy, monkeypatch):
    client, policy_id, admin = client_and_policy
    client.post("/auth/login", data={"email": "admin@example.com", "password": "password"})

    def fake_stream(content, mode, lang=""):
        yield "Word1 "
        yield "Word2"

    import blueprints.policy_ai
    monkeypatch.setattr(blueprints.policy_ai, "rewrite_text_stream", fake_stream)

    res = client.post(f"/admin/policies/{policy_id}/ai/writer/stream", data={
        "mode": "rewrite",
        "content": "Original content."
    })
    assert res.status_code == 200
    assert res.mimetype == "text/event-stream"
    text = res.get_data(as_text=True)
    assert 'data: {"type": "token", "token": "Word1 "}' in text
    assert 'data: {"type": "token", "token": "Word2"}' in text
    assert 'data: {"type": "done", "result": "Word1 Word2"}' in text
