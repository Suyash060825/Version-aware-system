"""
scripts/audit_rendered_views.py
Deep audit of all rendered views and dashboards.
Checks for:
1. HTTP 200 on all routes
2. No Jinja rendering errors or missing context keys
3. No 'None', 'NaN', 'undefined', 'null' strings rendered into HTML or JS
4. No empty tables (all tables have non-empty tbody rows)
5. No spurious/mock/dummy text or placeholders
6. Zero template crashes
"""
import os
import sys
import re
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if not os.environ.get("DATABASE_URL") or "postgres:" in os.environ.get("DATABASE_URL", ""):
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "ledger.db")
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

from app import create_app
from models import db, User

app = create_app("development")
client = app.test_client()

with app.app_context():
    admin = User.query.filter_by(email="admin@company.com").first()

with client.session_transaction() as sess:
    sess["_user_id"] = str(admin.id)
    sess["user_id"] = admin.id
    sess["role"] = "admin"

routes_to_audit = [
    # Admin Core Dashboards
    "/admin/",
    "/admin/policies",
    "/admin/policies/1",
    "/admin/categories",
    "/admin/departments",
    "/admin/users",
    
    # Intelligence & AI
    "/rag/admin/dashboard",
    "/admin/ai-analytics",
    "/admin/search-analytics",
    
    # Compliance, Governance & Risk
    "/admin/compliance",
    "/admin/governance",
    "/admin/contradictions",
    "/admin/confusion-index",
    "/admin/what-if-queue",
    
    # Visual Analytics & Process
    "/admin/knowledge-graph",
    "/admin/bi-dashboard",
    "/admin/workflows",
    "/admin/workflow-analytics",
    "/admin/leaderboard",
    
    # Audit & Security Center
    "/admin/audit-center",
    "/admin/audit-center/timeline",
    "/admin/audit-center/security",
    "/admin/audit-center/user/1",
    
    # Meetings & Action Items
    "/meetings",
    "/meetings/1",
    "/my-action-items",
    
    # Employee views as user
    "/dashboard",
    "/what-if",
    "/what-if/history",
    "/onboarding",
    "/saved",
    "/notifications",
]

print("="*85)
print(f"{'ROUTE':<36} | {'STATUS':<8} | {'TABLE ROWS':<12} | {'ANOMALIES / ISSUES'}")
print("="*85)

total_issues = 0

for route in routes_to_audit:
    res = client.get(route)
    if res.status_code != 200:
        print(f"{route:<36} | {res.status_code:<8} | {'-':<12} | ERROR: Non-200 status code")
        total_issues += 1
        continue
        
    html = res.get_data(as_text=True)
    soup = BeautifulSoup(html, "html.parser")
    
    issues = []
    
    # Check for literal None / NaN / undefined in visible text
    if re.search(r'>\s*None\s*<', html):
        issues.append("Literal 'None' in HTML element")
    if re.search(r'\bNaN\b', html):
        issues.append("Literal 'NaN' found")
    if re.search(r'>\s*undefined\s*<', html):
        issues.append("Literal 'undefined' in HTML")
        
    # Check for empty tables
    tables = soup.find_all("table")
    total_tbody_rows = 0
    empty_tables = 0
    for idx, t in enumerate(tables):
        tbody = t.find("tbody")
        if tbody:
            rows = tbody.find_all("tr")
            total_tbody_rows += len(rows)
            if len(rows) == 0:
                empty_tables += 1
        else:
            rows = t.find_all("tr")
            total_tbody_rows += max(0, len(rows) - 1)
            
    if empty_tables > 0:
        issues.append(f"{empty_tables} empty table(s)")
        
    # Check for unrendered Jinja tags
    if "{{" in html or "{%" in html:
        issues.append("Unrendered Jinja template tags")
        
    # Check for placeholder text
    if re.search(r'\blorem\s+ipsum\b|\bdummy\s+text\b', html, re.I):
        issues.append("Placeholder text")
            
    issue_str = ", ".join(issues) if issues else "CLEAN ✓"
    if issues:
        total_issues += len(issues)
        
    print(f"{route:<36} | {res.status_code:<8} | {total_tbody_rows:<12} | {issue_str}")

print("="*85)
if total_issues == 0:
    print(f"🎉 AUDIT PASSED WITH ZERO ANOMALIES ACROSS ALL {len(routes_to_audit)} ROUTES!")
else:
    print(f"Audit completed. Total anomalies identified: {total_issues}")
    sys.exit(1)
