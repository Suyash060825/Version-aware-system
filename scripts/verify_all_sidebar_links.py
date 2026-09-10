"""
scripts/verify_all_sidebar_links.py
Tests every link that appears in base.html sidebar and topbar using url_for.
"""
import os
import sys
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if not os.environ.get("DATABASE_URL") or "postgres:" in os.environ.get("DATABASE_URL", ""):
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "ledger.db")
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

from app import create_app
from models import db, User
from flask import url_for

app = create_app("development")
client = app.test_client()

with app.app_context():
    admin = User.query.filter_by(email="admin@company.com").first()
    assert admin is not None, "Admin user required"

with client.session_transaction() as sess:
    sess["_user_id"] = str(admin.id)
    sess["user_id"] = admin.id
    sess["role"] = "admin"

sidebar_endpoints = [
    ("admin.dashboard", {}),
    ("admin.policy_list", {}),
    ("admin.policy_create", {}),
    ("admin.user_list", {}),
    ("admin.category_list", {}),
    ("audit_center.audit_dashboard", {}),
    ("compliance.compliance_center", {}),
    ("governance.dashboard", {}),
    ("confusion_index.dashboard", {}),
    ("contradiction_radar.dashboard", {}),
    ("knowledge_graph.graph_page", {}),
    ("what_if.review_queue", {}),
    ("rag.admin_rag_dashboard", {}),
    ("ai_analytics.dashboard", {}),
    ("search.search_analytics", {}),
    ("bi.bi_dashboard", {}),
    ("workflow.template_list", {}),
    ("gamification.leaderboard", {}),
    ("employee.dashboard", {}),
    ("employee.onboarding", {}),
    ("meetings.list_meetings", {}),
    ("meetings.my_action_items", {}),
    ("rag.chat_page", {}),
    ("what_if.simulator", {}),
    ("employee.policy_browse", {}),
    ("employee.search", {}),
    ("search.advanced_search", {}),
    ("employee.saved_list", {}),
    ("gamification.my_rewards", {}),
    ("employee.notifications", {}),
]

print("="*85)
print(f"{'ENDPOINT':<32} | {'URL':<28} | {'STATUS':<8} | {'DETAILS'}")
print("="*85)

failed = 0
with app.test_request_context():
    for ep, kwargs in sidebar_endpoints:
        try:
            target_url = url_for(ep, **kwargs)
        except Exception as e:
            print(f"{ep:<32} | {'ERROR':<28} | {'BUILD_ERR':<8} | {e}")
            failed += 1
            continue

        res = client.get(target_url)
        if res.status_code == 200:
            soup = BeautifulSoup(res.get_data(as_text=True), "html.parser")
            h1 = soup.find("h1")
            title_text = h1.get_text(strip=True) if h1 else (soup.title.get_text(strip=True) if soup.title else "")
            print(f"{ep:<32} | {target_url:<28} | 200 OK   | {title_text[:40]}")
        else:
            print(f"{ep:<32} | {target_url:<28} | {res.status_code:<8} | FAILED")
            failed += 1

print("="*85)
if failed == 0:
    print(f"🎉 ALL {len(sidebar_endpoints)} SIDEBAR AND USER NAVIGATION LINKS RESOLVE TO HTTP 200 OK!")
else:
    print(f"⚠️ {failed} endpoints failed.")
    sys.exit(1)
