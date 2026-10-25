"""
blueprints/compliance.py
Module 9: Compliance Center

Routes:
  GET  /admin/compliance                          dashboard: readiness score, gaps, expired, violations
  POST /admin/compliance/policies/<id>/frameworks  update which frameworks a policy maps to
  GET  /admin/compliance/report                    printable audit-readiness report
"""
from datetime import date

from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user

from models import (db, Policy, PolicyStatus, PolicyAcknowledgement, ComplianceFramework,
                    ensure_default_frameworks, PolicyAIReview, User, UserRole)
from utils import audit, role_required

compliance_bp = Blueprint("compliance", __name__, url_prefix="/admin")


def _compute_compliance_data():
    ensure_default_frameworks()
    frameworks = ComplianceFramework.query.filter_by(is_active=True).order_by(ComplianceFramework.name).all()
    active_policies = Policy.query.filter_by(status=PolicyStatus.ACTIVE).all()
    # Filter out restricted policies if user not authorized
    can_view = (
        (callable(getattr(current_user, "can_view_restricted", None)) and current_user.can_view_restricted()) or
        (callable(getattr(current_user, "is_admin", None)) and current_user.is_admin()) or
        getattr(current_user, "clearance", None) == "restricted"
    )
    if not can_view:
        active_policies = [p for p in active_policies if p.confidentiality != "restricted"]
    all_framework_policies = active_policies
    total_active = len(active_policies)

    # Missing compliance: frameworks with zero mapped active policies
    framework_data = []
    for f in frameworks:
        mapped_active = [p for p in f.policies if p.status == PolicyStatus.ACTIVE]
        framework_data.append({"framework": f, "policy_count": len(mapped_active), "gap": len(mapped_active) == 0})
    gaps = [fd["framework"].name for fd in framework_data if fd["gap"]]

    # Expired policies still marked active
    today = date.today()
    expired_policies = [p for p in active_policies if p.expiry_date and p.expiry_date < today]

    # Policies overdue for review
    overdue_review = [p for p in active_policies if p.review_date and p.review_date < today]

    # Violations & Acks: mandatory active policies with unacknowledged employees (Batched)
    from sqlalchemy import func
    total_employees = User.query.filter_by(role=UserRole.EMPLOYEE, is_active=True).count()
    mand_policy_ids = [p.id for p in active_policies if p.is_mandatory]
    acked_counts = dict(
        db.session.query(PolicyAcknowledgement.policy_id, func.count(PolicyAcknowledgement.id))
        .join(User, PolicyAcknowledgement.user_id == User.id)
        .filter(
            User.role == UserRole.EMPLOYEE,
            User.is_active == True,
            PolicyAcknowledgement.policy_id.in_(mand_policy_ids),
            PolicyAcknowledgement.acknowledged_at.isnot(None),
        )
        .group_by(PolicyAcknowledgement.policy_id).all()
    ) if mand_policy_ids else {}
    violations = []
    ack_scores = []
    for p in active_policies:
        if not p.is_mandatory:
            continue
        acked = acked_counts.get(p.id, 0)
        outstanding = max(0, total_employees - acked)
        if outstanding > 0:
            violations.append({"policy": p, "outstanding": outstanding, "acked": acked, "total": total_employees})
        ack_scores.append(min(100.0, 100.0 * acked / total_employees) if total_employees else 100.0)
    violations.sort(key=lambda v: -v["outstanding"])

    # Aggregated AI compliance issues (from Module 3's PolicyAIReview, already computed elsewhere)
    from sqlalchemy.orm import joinedload
    reviews = (PolicyAIReview.query
               .join(Policy, PolicyAIReview.policy_id == Policy.id)
               .options(joinedload(PolicyAIReview.policy))
               .filter(Policy.status == PolicyStatus.ACTIVE).all())
    ai_issues = []
    for review in reviews:
        for issue in (review.compliance_issues or []):
            ai_issues.append({"policy": review.policy, "issue": issue, "risk_score": review.risk_score})
    ai_issues.sort(key=lambda x: -x["risk_score"])

    # Audit readiness score (composite, 0-100)
    framework_coverage = round(100 * (len(frameworks) - len(gaps)) / len(frameworks)) if frameworks else 100
    ack_score = round(sum(ack_scores) / len(ack_scores)) if ack_scores else 100
    expiry_score = round(100 * (len(active_policies) - len(expired_policies)) / len(active_policies)) if active_policies else 100
    review_score = round(100 * (len(active_policies) - len(overdue_review)) / len(active_policies)) if active_policies else 100
    avg_ai_risk = sum(r.risk_score for r in reviews) / len(reviews) if reviews else 0
    ai_risk_score = round(100 - avg_ai_risk)

    readiness_score = round(
        0.25 * framework_coverage + 0.30 * ack_score + 0.20 * expiry_score +
        0.15 * review_score + 0.10 * ai_risk_score
    )

    return {
        "framework_data": framework_data, "gaps": gaps,
        "expired_policies": expired_policies, "overdue_review": overdue_review,
        "violations": violations, "ai_issues": ai_issues[:15],
        "readiness_score": readiness_score,
        "sub_scores": {"framework_coverage": framework_coverage, "ack_score": ack_score,
                      "expiry_score": expiry_score, "review_score": review_score,
                      "ai_risk_score": ai_risk_score},
        "active_policy_count": len(active_policies),
    }


@compliance_bp.route("/compliance")
@login_required
@role_required(UserRole.ADMIN, UserRole.HR)
def compliance_center():
    data = _compute_compliance_data()
    all_policies_q = Policy.query.filter_by(status=PolicyStatus.ACTIVE)
    can_view = (
        (callable(getattr(current_user, "can_view_restricted", None)) and current_user.can_view_restricted()) or
        (callable(getattr(current_user, "is_admin", None)) and current_user.is_admin()) or
        getattr(current_user, "clearance", None) == "restricted"
    )
    if not can_view:
        all_policies_q = all_policies_q.filter(Policy.confidentiality != "restricted")
    all_policies = all_policies_q.order_by(Policy.title).all()
    return render_template("admin/compliance_center.html", all_policies=all_policies, **data)


@compliance_bp.route("/compliance/policies/<int:policy_id>/frameworks", methods=["POST"])
@login_required
@role_required(UserRole.ADMIN, UserRole.HR)
def update_frameworks(policy_id):
    policy = Policy.query.get_or_404(policy_id)
    if not (current_user.is_admin() if callable(getattr(current_user, "is_admin", None)) else getattr(current_user, "is_admin", False)):
        from rag.authorization.evidence_filter import get_evidence_filter
        if not get_evidence_filter().is_authorized_for_policy(current_user, policy):
            abort(403)
    framework_ids = request.form.getlist("framework_ids", type=int)
    policy.frameworks = ComplianceFramework.query.filter(ComplianceFramework.id.in_(framework_ids)).all()
    db.session.commit()
    audit("compliance.map_frameworks", "policy", policy.id, {"frameworks": len(framework_ids)})
    flash(f'Updated compliance mapping for "{policy.title}".', "success")
    return redirect(url_for("compliance.compliance_center"))


@compliance_bp.route("/compliance/report")
@login_required
@role_required(UserRole.ADMIN, UserRole.HR)
def compliance_report():
    data = _compute_compliance_data()
    return render_template("admin/compliance_report.html", generated_at=date.today(), **data)
