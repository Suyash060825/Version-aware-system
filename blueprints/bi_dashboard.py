"""
blueprints/bi_dashboard.py
Module 11: Dashboard & BI

A single executive analytics page pulling together data already produced by
Modules 3/5/8/14 (policy AI usage, meetings, search, workflow approvals) plus
core policy/employee stats — with a short auto-generated text insight.

Route: GET /admin/bi-dashboard
"""
from datetime import datetime, timedelta, date, timezone
from collections import defaultdict

from flask import Blueprint, render_template
from flask_login import login_required
from sqlalchemy import func

from models import (db, db, Policy, PolicyVersion, PolicyStatus, PolicyCategory, Priority,
                    Department, User, UserRole, PolicyAcknowledgement, AuditLog,
                    SearchHistory, Meeting, WorkflowStageInstance)
from utils import role_required

bi_bp = Blueprint("bi", __name__, url_prefix="/admin")


def _month_buckets(n_months=12):
    """Returns n_months (year, month) tuples ending at the current month."""
    today = date.today()
    buckets = []
    y, m = today.year, today.month
    for _ in range(n_months):
        buckets.append((y, m))
        m -= 1
        if m == 0:
            m, y = 12, y - 1
    return list(reversed(buckets))


def _month_label(y, m):
    return date(y, m, 1).strftime("%b %Y")


def _count_by_month(rows_with_dates, n_months=12):
    buckets = _month_buckets(n_months)
    counts = {b: 0 for b in buckets}
    for d in rows_with_dates:
        if d is None:
            continue
        key = (d.year, d.month)
        if key in counts:
            counts[key] += 1
    return [{"label": _month_label(y, m), "value": counts[(y, m)]} for (y, m) in buckets]


def _generate_insight(stats: dict) -> str:
    """Short natural-language callout with Redis caching and deterministic fallback."""
    import os, json
    # Check cache first
    redis_client = None
    cache_key = "bi_dashboard:insight"
    try:
        import redis
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        redis_client = redis.Redis.from_url(redis_url, socket_timeout=1.0)
        cached = redis_client.get(cache_key)
        if cached:
            return cached.decode("utf-8")
    except Exception:
        pass

    result = None
    try:
        from rag.llm_provider import get_llm_provider
        llm = get_llm_provider()
        if llm.health_check():
            from policy_ai import _llm_text
            prompt = (
                f"Dashboard stats: {stats}. In ONE short sentence, surface the single most "
                f"actionable insight for a policy compliance manager (e.g. a bottleneck, a "
                f"compliance gap, or a trend). Plain text, no preamble."
            )
            result = _llm_text("You write terse, specific one-sentence insights from dashboard metrics.", prompt)
            if result and len(result) < 300:
                if redis_client:
                    try:
                        redis_client.setex(cache_key, 3600, result)
                    except Exception:
                        pass
                return result
            return result
    except Exception:
        pass

    # Deterministic fallback: pick the most notable metric ourselves
    if stats.get("overdue_stages", 0) > 0:
        fallback = f"{stats['overdue_stages']} approval stage(s) are past their SLA — check Workflow Analytics."
    elif stats.get("compliance_rate", 100) < 70:
        fallback = f"Mandatory-policy compliance is at {stats['compliance_rate']}% — below the 70% healthy threshold."
    elif stats.get("zero_result_searches", 0) > 3:
        fallback = f"{stats['zero_result_searches']} searches recently returned nothing — possible content gaps."
    elif stats.get("top_category"):
        fallback = f"\"{stats['top_category']}\" is your most active department by policy count."
    else:
        fallback = "No standout risks detected — metrics look steady."

    if redis_client:
        try:
            redis_client.setex(cache_key, 3600, fallback)
        except Exception:
            pass
    return fallback


@bi_bp.route("/bi-dashboard")
@login_required
@role_required(UserRole.ADMIN, UserRole.HR)
def bi_dashboard():
    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)

    # ---------- Policy Growth & Version Growth ----------
    policy_dates = [p[0] for p in Policy.query.with_entities(Policy.created_at).all()]
    policy_growth = _count_by_month(policy_dates)
    version_dates = [v[0] for v in PolicyVersion.query.with_entities(PolicyVersion.created_at).all()]
    version_growth = _count_by_month(version_dates)

    # ---------- Employee Compliance / Read Rate ----------
    total_employees = User.query.filter_by(role=UserRole.EMPLOYEE, is_active=True).count()
    mandatory_policies = Policy.query.filter_by(status=PolicyStatus.ACTIVE, is_mandatory=True).count()
    total_required = total_employees * mandatory_policies
    total_acked = PolicyAcknowledgement.query.filter(
        PolicyAcknowledgement.acknowledged_at.isnot(None), PolicyAcknowledgement.is_mandatory == True
    ).count()
    compliance_rate = round(100 * total_acked / total_required) if total_required else 100

    total_reads = PolicyAcknowledgement.query.filter(PolicyAcknowledgement.read_at.isnot(None)).count()
    total_acks_all = PolicyAcknowledgement.query.count()
    read_rate = round(100 * total_reads / max(total_acks_all, 1)) if total_acks_all else 0

    # ---------- Department Analytics (Batched Queries) ----------
    dept_emp_counts = dict(
        db.session.query(User.department_id, func.count(User.id))
        .filter(User.role == UserRole.EMPLOYEE, User.is_active == True)
        .group_by(User.department_id).all()
    )
    dept_pol_counts = dict(
        db.session.query(Policy.department_id, func.count(Policy.id))
        .group_by(Policy.department_id).all()
    )
    dept_mand_counts = dict(
        db.session.query(Policy.department_id, func.count(Policy.id))
        .filter(Policy.is_mandatory == True, Policy.status == PolicyStatus.ACTIVE)
        .group_by(Policy.department_id).all()
    )
    dept_ack_counts = dict(
        db.session.query(Policy.department_id, func.count(PolicyAcknowledgement.id))
        .join(Policy, PolicyAcknowledgement.policy_id == Policy.id)
        .filter(PolicyAcknowledgement.acknowledged_at.isnot(None))
        .group_by(Policy.department_id).all()
    )

    dept_data = []
    for d in Department.query.order_by(Department.name).all():
        dept_employees = dept_emp_counts.get(d.id, 0)
        dept_policies = dept_pol_counts.get(d.id, 0)
        dept_mandatory = dept_mand_counts.get(d.id, 0)
        dept_required = dept_employees * dept_mandatory
        dept_acked = dept_ack_counts.get(d.id, 0)
        dept_compliance = round(100 * dept_acked / dept_required) if dept_required else None
        dept_data.append({"name": d.name, "policies": dept_policies, "employees": dept_employees,
                          "compliance": dept_compliance})
    dept_data.sort(key=lambda x: -x["policies"])

    # ---------- AI Usage (from AuditLog — Modules 3 & 5) ----------
    ai_actions = (db.session.query(AuditLog.action, func.count(AuditLog.id))
                 .filter(AuditLog.action.like("policy_ai.%") | AuditLog.action.like("meeting.generate_mom%"))
                 .filter(AuditLog.timestamp >= thirty_days_ago)
                 .group_by(AuditLog.action).all())
    ai_usage = [{"action": a.replace("policy_ai.", "").replace("_", " ").title(), "count": c}
               for a, c in sorted(ai_actions, key=lambda x: -x[1])]
    total_ai_calls = sum(x["count"] for x in ai_usage)

    # ---------- Search Trends (Module 14, last 14 days) ----------
    fourteen_days_ago = now - timedelta(days=14)
    search_rows = SearchHistory.query.filter(SearchHistory.created_at >= fourteen_days_ago).all()
    search_by_day = defaultdict(int)
    zero_result = 0
    for s in search_rows:
        search_by_day[s.created_at.date()] += 1
        if not s.answered:
            zero_result += 1
    search_trend = []
    for i in range(13, -1, -1):
        d = (now - timedelta(days=i)).date()
        search_trend.append({"label": d.strftime("%d %b"), "value": search_by_day.get(d, 0)})

    # ---------- Meeting Trends (Module 5) ----------
    meeting_dates = [m[0] for m in Meeting.query.with_entities(Meeting.scheduled_at).all() if m[0]]
    meeting_trend = _count_by_month(meeting_dates, n_months=6)

    # ---------- Risk Heatmap: Category x Priority (Batched) ----------
    categories = PolicyCategory.query.order_by(PolicyCategory.name).all()
    priorities = [Priority.LOW, Priority.MEDIUM, Priority.HIGH, Priority.CRITICAL]
    heatmap_data = (
        db.session.query(Policy.category_id, Policy.priority, func.count(Policy.id))
        .filter(Policy.status == PolicyStatus.ACTIVE)
        .group_by(Policy.category_id, Policy.priority).all()
    )
    heatmap_lookup = defaultdict(lambda: defaultdict(int))
    for cid, prio, cnt in heatmap_data:
        heatmap_lookup[cid][prio] = cnt

    heatmap = []
    for c in categories:
        row = {"category": c.name, "cells": []}
        for p in priorities:
            row["cells"].append(heatmap_lookup[c.id][p])
        if sum(row["cells"]):
            heatmap.append(row)

    # ---------- Pending Reviews ----------
    pending_review_count = Policy.query.filter(Policy.status.in_(PolicyStatus.IN_REVIEW)).count()
    review_due_soon = Policy.query.filter(
        Policy.review_date.isnot(None),
        Policy.review_date <= date.today() + timedelta(days=30),
        Policy.review_date >= date.today(),
        Policy.status == PolicyStatus.ACTIVE,
    ).count()

    # ---------- Approval Bottlenecks (Module 8) ----------
    completed_stages = WorkflowStageInstance.query.filter(WorkflowStageInstance.completed_at.isnot(None)).all()
    stage_times = defaultdict(list)
    for s in completed_stages:
        hours = (s.completed_at.replace(tzinfo=None) - s.created_at).total_seconds() / 3600
        stage_times[s.name].append(hours)
    bottlenecks = sorted(
        [{"name": name, "avg_hours": round(sum(v) / len(v), 1)} for name, v in stage_times.items()],
        key=lambda x: -x["avg_hours"]
    )[:6]
    overdue_stages = sum(1 for s in WorkflowStageInstance.query.filter_by(status="pending").all() if s.is_overdue)

    # ---------- Employee Activity (last 30 days - Joined) ----------
    activity_rows = (db.session.query(User.name, func.count(AuditLog.id).label("cnt"))
                     .join(User, AuditLog.user_id == User.id)
                     .filter(AuditLog.timestamp >= thirty_days_ago)
                     .group_by(User.name).order_by(func.count(AuditLog.id).desc()).limit(8).all())
    most_active = [{"name": name, "count": cnt} for name, cnt in activity_rows]

    # ---------- Most Viewed Policies ----------
    most_viewed = (Policy.query.filter_by(status=PolicyStatus.ACTIVE)
                  .order_by(Policy.view_count.desc()).limit(8).all())

    top_department = dept_data[0]["name"] if dept_data else None
    stats_for_insight = {
        "overdue_stages": overdue_stages, "compliance_rate": compliance_rate,
        "zero_result_searches": zero_result, "top_category": top_department,
    }
    insight = _generate_insight(stats_for_insight)

    return render_template("admin/bi_dashboard.html",
        policy_growth=policy_growth, version_growth=version_growth,
        compliance_rate=compliance_rate, read_rate=read_rate, dept_data=dept_data,
        ai_usage=ai_usage, total_ai_calls=total_ai_calls,
        search_trend=search_trend, zero_result=zero_result, meeting_trend=meeting_trend,
        heatmap=heatmap, priorities=priorities,
        pending_review_count=pending_review_count, review_due_soon=review_due_soon,
        bottlenecks=bottlenecks, overdue_stages=overdue_stages,
        most_active=most_active, most_viewed=most_viewed,
        total_employees=total_employees, mandatory_policies=mandatory_policies,
        insight=insight,
    )
