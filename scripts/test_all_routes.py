"""
scripts/test_all_routes.py
Comprehensive smoke test across all platform routes and views.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if not os.environ.get("DATABASE_URL") or "postgres:" in os.environ.get("DATABASE_URL", ""):
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "ledger.db")
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

from app import create_app
from models import db, User

app = create_app("development")

def run_tests():
    client = app.test_client()
    
    with app.app_context():
        admin = User.query.filter_by(email="admin@company.com").first()
        assert admin is not None, "Admin user must exist"

    print("Authenticating as admin...")
    with client.session_transaction() as sess:
        sess["_user_id"] = str(admin.id)
        sess["user_id"] = admin.id
        sess["role"] = "admin"

    endpoints = [
        # Admin Core & Policy Management
        ("/admin/", "Admin Main Dashboard", ["Knowledge Base & Semantic Index", "Semantic chunks", "Policies"]),
        ("/admin/policies", "Policy Inventory", ["Index", "chunks"]),
        ("/admin/policies/1", "Policy Detail View", ["Vector Index & Knowledge Compilation", "Inspect Chunks"]),
        
        # RAG & AI Intelligence
        ("/rag/admin/dashboard", "RAG & AI Dashboard", ["AI & RAG Dashboard", "Semantic Chunks", "Compilation Jobs"]),
        ("/rag/health", "RAG Health & Stats API", ["status", "database"]),
        ("/rag/api/policy/1/chunks", "RAG API Policy Chunks JSON", ["chunks", "policy_id"]),
        
        # Enterprise Compliance & Governance
        ("/admin/compliance", "Statutory Compliance Center", ["ISO 27001", "Compliance"]),
        ("/admin/governance", "Governance & Meetings (MOM)", ["Meetings", "Action Items"]),
        ("/admin/contradictions", "Contradiction Radar", ["Run Contradiction Scan Now", "Contradiction"]),
        ("/admin/confusion-index", "Policy Confusion Index", ["Policy Confusion Index", "Ranked by confusion score"]),
        ("/admin/knowledge-graph", "Interactive Knowledge Graph", ["Knowledge Graph"]),
        ("/admin/bi-dashboard", "Executive BI & Analytics", ["Executive Dashboard", "Employee compliance"]),
        ("/admin/ai-analytics", "AI Adoption & RAG Analytics", ["AI Analytics", "Queries"]),
        ("/admin/audit-center", "Audit & Forensic Center", ["Audit Center", "Total events"]),
        ("/admin/workflows", "Workflow Process Management", ["Workflow", "Standard 3-Tier"]),
        ("/admin/leaderboard", "Gamification & Leaderboard", ["Leaderboard", "Points"]),
        
        # Employee Portal & What-If Simulator
        ("/dashboard", "Employee Knowledge Portal", ["Policies", "Compliance"]),
        ("/what-if", "Policy Impact Simulator (What-If)", ["What-If", "Scenario"]),
        ("/admin/what-if-queue", "What-If HR Review Queue", ["What-If Review Queue", "HR Review"]),
        ("/onboarding", "Guided Onboarding Reading Path", ["Onboarding", "Checklist"]),
    ]

    all_passed = True
    print("\n" + "="*75)
    print(f"{'ROUTE':<28} | {'STATUS':<16} | {'VALIDATION':<26}")
    print("="*75)

    for route, label, needles in endpoints:
        res = client.get(route)
        if res.status_code == 302:
            status_str = f"302 -> {res.headers.get('Location', '')[:20]}"
            passed = False
        elif res.status_code == 200:
            status_str = "200 OK"
            text = res.get_data(as_text=True)
            missing = [n for n in needles if n.lower() not in text.lower()]
            if missing:
                passed = False
                status_str = f"200 (missed '{missing[0]}')"
            else:
                passed = True
        else:
            status_str = f"{res.status_code}"
            passed = False

        val_mark = "✓ PASS" if passed else "✗ FAIL"
        if not passed:
            all_passed = False
        print(f"{route:<28} | {status_str:<16} | {val_mark} ({label})")

    print("="*75)
    if all_passed:
        print("\n🎉 ALL 18 PLATFORM VIEWS & APIS VALIDATED SUCCESSFULLY! 100% OPERATIONAL.\n")
    else:
        print("\n⚠️ SOME ROUTES FAILED VALIDATION. PLEASE REVIEW.\n")
        sys.exit(1)

if __name__ == "__main__":
    run_tests()
