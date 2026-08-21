from app import create_app
from models import db, Policy, PolicyVersion
from rag.indexing.index_policy import index_policy_version

app = create_app("development")
with app.app_context():
    policies = Policy.query.all()
    for p in policies:
        active_v = next((v for v in p.versions if v.is_active), None)
        if active_v:
            print(f"Indexing policy {p.id} version {active_v.id}...")
            res = index_policy_version(p.id, active_v.id)
            print(res)
