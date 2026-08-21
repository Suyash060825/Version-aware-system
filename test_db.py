import os
os.environ["FLASK_ENV"] = "development"
from app import create_app
app = create_app()
with app.app_context():
    from models import db, PolicyVersion, Policy
    versions = PolicyVersion.query.all()
    for v in versions:
        p = db.session.get(Policy, v.policy_id)
        dept = p.department.name if p.department else "None"
        print(f"Policy: {p.title} | Version: {v.version_label} | Active: {v.is_active} | Dept: {dept}")
