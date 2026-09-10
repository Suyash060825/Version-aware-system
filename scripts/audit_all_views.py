#!/usr/bin/env python3
"""
scripts/audit_all_views.py

Master Comprehensive Platform Audit Suite:
Executes deep rendering and structural verification across all 51 GET routes
for both Administrator and Employee user roles.
"""

import sys
import os
import re
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set local SQLite DB
if not os.environ.get("DATABASE_URL") or "postgres:" in os.environ.get("DATABASE_URL", ""):
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "ledger.db")
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

from app import create_app
from models import User

def run_master_audit():
    app = create_app("development")
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False

    admin_routes = [
        "/admin/",
        "/admin/policies",
        "/admin/policies/1",
        "/admin/policies/1/ai",
        "/admin/policies/1/blast-radius",
        "/admin/policies/1/versions/compare?v1=1&v2=2",
        "/admin/policies/new",
        "/admin/categories",
        "/admin/departments",
        "/admin/users",
        "/admin/users/new",
        "/admin/search-analytics",
        "/admin/compliance",
        "/admin/compliance/report",
        "/admin/governance",
        "/admin/contradictions",
        "/admin/confusion-index",
        "/admin/what-if-queue",
        "/admin/knowledge-graph",
        "/admin/bi-dashboard",
        "/admin/workflows",
        "/admin/workflows/1/edit",
        "/admin/workflows/new",
        "/admin/workflow-analytics",
        "/admin/leaderboard",
        "/admin/audit-center",
        "/admin/audit-center/timeline",
        "/admin/audit-center/security",
        "/admin/audit-center/user/1",
        "/rag/admin/dashboard",
        "/rag/chat",
        "/meetings",
        "/meetings/1",
        "/meetings/new",
        "/my-action-items",
        "/dashboard",
        "/policies",
        "/policies/1",
        "/policies/1/certificate",
        "/policies/1/quiz",
        "/rewards",
        "/search",
        "/search/advanced",
        "/search/saved",
        "/what-if",
        "/what-if/history",
        "/onboarding",
        "/saved",
        "/notifications",
        "/auth/profile",
    ]

    employee_routes = [
        "/dashboard",
        "/policies",
        "/policies/1",
        "/policies/1/certificate",
        "/policies/1/quiz",
        "/rewards",
        "/search",
        "/search/advanced",
        "/search/saved",
        "/what-if",
        "/what-if/history",
        "/onboarding",
        "/saved",
        "/notifications",
        "/auth/profile",
        "/meetings",
        "/meetings/2",
        "/my-action-items",
        "/rag/chat",
    ]

    print("\n" + "=" * 95)
    print("      VERSION-AWARE ENTERPRISE POLICY INTELLIGENCE — MASTER AUDIT SUITE")
    print("=" * 95)

    with app.app_context():
        admin = User.query.filter_by(role="admin").first()
        emp = User.query.filter_by(role="employee").first()

        assert admin is not None, "Admin user missing in database"
        assert emp is not None, "Employee user missing in database"

        total_tested = 0
        total_passed = 0
        failures = []

        # 1. Test Admin Routes
        print(f"\n[PHASE 1] Auditing Administrator Views as {admin.name} ({admin.email})...")
        print("-" * 95)
        print(f"{'ROUTE':42} | {'STATUS':8} | {'SIZE':9} | {'HEALTH STATUS'}")
        print("-" * 95)

        client = app.test_client()
        with client.session_transaction() as sess:
            sess["_user_id"] = str(admin.id)
            sess["_fresh"] = True

        for r in admin_routes:
            total_tested += 1
            try:
                resp = client.get(r)
                if resp.status_code != 200:
                    failures.append((r, f"HTTP {resp.status_code}"))
                    print(f"{r:42} | {resp.status_code:<8} | {'-':9} | ❌ FAILED (Status {resp.status_code})")
                    continue

                html = resp.data.decode("utf-8", errors="ignore")
                issues = []

                # Jinja syntax leaks
                jinja_matches = re.findall(r"\{\{.*?\}\}|\{%.*?%\}", html)
                leaks = [m for m in jinja_matches if not any(k in m for k in ["MathJax", "alpine"])]
                if leaks:
                    issues.append(f"Jinja leak: {leaks[0][:30]}")

                # Empty table body
                if re.search(r"<tbody[^>]*>\s*</tbody>", html, re.IGNORECASE):
                    issues.append("Empty <tbody>")

                # Placeholder markers
                placeholders = re.findall(r"\b(lorem\s+ipsum|TODO|TBD|FIXME|dummy\s+data)\b", html, re.IGNORECASE)
                if placeholders:
                    issues.append(f"Placeholder: {placeholders[0]}")

                # Empty chart datasets
                if re.search(r"data:\s*\[\s*\]", html):
                    issues.append("Empty chart data")

                if issues:
                    failures.append((r, ", ".join(issues)))
                    print(f"{r:42} | {resp.status_code:<8} | {len(html):<9} | ⚠️  ISSUES ({', '.join(issues)})")
                else:
                    total_passed += 1
                    print(f"{r:42} | {resp.status_code:<8} | {len(html):<9} | ✓ CLEAN")

            except Exception as e:
                failures.append((r, str(e)))
                print(f"{r:42} | ERROR    | {'-':9} | ❌ EXCEPTION: {e}")

        # 2. Test Employee Routes
        print(f"\n[PHASE 2] Auditing Employee Views as {emp.name} ({emp.email})...")
        print("-" * 95)
        print(f"{'ROUTE':42} | {'STATUS':8} | {'SIZE':9} | {'HEALTH STATUS'}")
        print("-" * 95)

        client_emp = app.test_client()
        with client_emp.session_transaction() as sess:
            sess["_user_id"] = str(emp.id)
            sess["_fresh"] = True

        for r in employee_routes:
            total_tested += 1
            try:
                resp = client_emp.get(r)
                if resp.status_code != 200:
                    failures.append((f"[Employee] {r}", f"HTTP {resp.status_code}"))
                    print(f"{r:42} | {resp.status_code:<8} | {'-':9} | ❌ FAILED (Status {resp.status_code})")
                    continue

                html = resp.data.decode("utf-8", errors="ignore")
                issues = []

                jinja_matches = re.findall(r"\{\{.*?\}\}|\{%.*?%\}", html)
                leaks = [m for m in jinja_matches if not any(k in m for k in ["MathJax", "alpine"])]
                if leaks:
                    issues.append(f"Jinja leak: {leaks[0][:30]}")

                if re.search(r"<tbody[^>]*>\s*</tbody>", html, re.IGNORECASE):
                    issues.append("Empty <tbody>")

                placeholders = re.findall(r"\b(lorem\s+ipsum|TODO|TBD|FIXME|dummy\s+data)\b", html, re.IGNORECASE)
                if placeholders:
                    issues.append(f"Placeholder: {placeholders[0]}")

                if issues:
                    failures.append((f"[Employee] {r}", ", ".join(issues)))
                    print(f"{r:42} | {resp.status_code:<8} | {len(html):<9} | ⚠️  ISSUES ({', '.join(issues)})")
                else:
                    total_passed += 1
                    print(f"{r:42} | {resp.status_code:<8} | {len(html):<9} | ✓ CLEAN")

            except Exception as e:
                failures.append((f"[Employee] {r}", str(e)))
                print(f"{r:42} | ERROR    | {'-':9} | ❌ EXCEPTION: {e}")

        # Summary
        print("\n" + "=" * 95)
        print(f"AUDIT SUMMARY: {total_passed}/{total_tested} checks passed ({total_passed/total_tested*100:.1f}%)")
        print("=" * 95)

        if failures:
            print(f"\n❌ {len(failures)} failures identified:")
            for r, err in failures:
                print(f"  - {r}: {err}")
            sys.exit(1)
        else:
            print("\n🎉 ALL PLATFORM ROUTES AND USER EXPERIENCES VERIFIED 100% OPERATIONAL WITH ZERO ANOMALIES!\n")
            sys.exit(0)

if __name__ == "__main__":
    run_master_audit()
