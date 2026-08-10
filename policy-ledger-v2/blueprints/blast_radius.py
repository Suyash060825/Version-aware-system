"""
blueprints/blast_radius.py
Module: Change Impact Preview ("Policy Blast Radius")  — NOVEL FEATURE

Every other AI module in this app looks *backward*: Confusion Index scores
how confused people already are, Contradiction Radar flags conflicts that
already exist, Governance Health scores the portfolio as it stands today.
None of them answer the one question an HR editor actually needs *before*
hitting publish on a change: "what will this break?"

Blast Radius is forward-looking. Given a policy that's about to be edited
or republished, it previews the downstream footprint of that change using
signals that already exist elsewhere in the app but have never been pulled
together into a pre-publish check:

  Re-acknowledgement load   how many employees already signed off on the
                            current version and would need to re-acknowledge
  Audience reach            how many active employees are in scope (whole
                            company if mandatory + no department restriction,
                            otherwise just that department)
  Linked meetings           meetings (and the decisions taken in them) that
                            reference this policy — minutes may need a note
  Training debt             quiz attempts already taken against the current
                            wording — a real edit invalidates that history
                            and the AI-generated quiz/FAQ should be regenerated
  Grey-area exposure        open What-If Simulator queries that cited this
                            policy, especially any flagged for HR — guidance
                            already given to employees may no longer hold
  Existing risk & conflicts current AI Review risk score plus any *open*
                            Contradiction Radar flags involving this policy

These roll into one 0-100 Impact Score so an editor can tell, at a glance,
whether a change is low-friction (adjust a typo) or high-blast-radius
(rewrite a mandatory, heavily-cited, already-flagged policy) — and see
exactly who/what needs a heads-up before they publish.

Routes:
  GET /admin/policies/<policy_id>/blast-radius
"""
from datetime import date

from flask import Blueprint, render_template
from flask_login import login_required

from models import (Policy, PolicyStatus, PolicyAcknowledgement, User, UserRole,
                    QuizAttempt, WhatIfQuery, WhatIfVerdict, ContradictionFlag,
                    ContradictionScanStatus, PolicyAIReview)
from utils import role_required

blast_radius_bp = Blueprint("blast_radius", __name__, url_prefix="/admin")


def _whatif_hits(policy_id):
    """WhatIfQuery rows whose applicable_policies_json cites this policy id."""
    hits, flagged = [], 0
    for wq in WhatIfQuery.query.all():
        for ref in (wq.applicable_policies or []):
            try:
                pid = int(ref.get("policy_id"))
            except (TypeError, ValueError):
                continue
            if pid == policy_id:
                hits.append(wq)
                if wq.flagged_for_hr:
                    flagged += 1
                break
    uncertain = sum(1 for wq in hits if wq.verdict in (WhatIfVerdict.DEPENDS, WhatIfVerdict.UNCLEAR))
    return {"total": len(hits), "flagged": flagged, "uncertain": uncertain, "recent": hits[:8]}


def _open_conflicts(policy_id):
    return (ContradictionFlag.query
            .filter(ContradictionFlag.status == ContradictionScanStatus.OPEN)
            .filter((ContradictionFlag.policy_a_id == policy_id) |
                    (ContradictionFlag.policy_b_id == policy_id))
            .all())


def compute_blast_radius(policy: Policy):
    acked = (PolicyAcknowledgement.query.filter_by(policy_id=policy.id)
             .filter(PolicyAcknowledgement.acknowledged_at.isnot(None)).all())
    reack_count = len(acked)

    if policy.department_id and not policy.is_mandatory:
        audience = User.query.filter_by(department_id=policy.department_id, is_active=True).count()
        audience_scope = policy.department.name if policy.department else "department"
    else:
        audience = User.query.filter_by(is_active=True).count()
        audience_scope = "whole company" if policy.is_mandatory else "all active users"

    meetings = list(policy.related_meetings)
    meeting_rows = [{"meeting": m, "decision_count": m.decisions.count()} for m in meetings]

    quiz_attempts = QuizAttempt.query.filter_by(policy_id=policy.id).all()
    quiz_count = len(quiz_attempts)
    quiz_pass_rate = (round(100 * sum(1 for q in quiz_attempts if q.passed) / quiz_count, 1)
                      if quiz_count else None)

    whatif = _whatif_hits(policy.id)
    conflicts = _open_conflicts(policy.id)
    review = policy.ai_review  # PolicyAIReview or None (uselist=False backref)
    risk_score = review.risk_score if review else None

    # ---- Impact Score (0-100), weighted ----
    total_employees = max(User.query.filter_by(is_active=True).count(), 1)
    reach_pct = min(100, round(100 * audience / total_employees))
    reach_component = reach_pct  # 0-100, higher reach = higher impact

    artifact_hits = len(meeting_rows) + quiz_count + whatif["total"]
    artifact_component = min(100, artifact_hits * 8)  # saturates around ~12-13 touchpoints

    risk_component = risk_score if risk_score is not None else 20  # unknown risk = mild default

    conflict_component = min(100, len(conflicts) * 40 + whatif["flagged"] * 15)

    impact_score = round(
        reach_component * 0.30 +
        artifact_component * 0.25 +
        risk_component * 0.25 +
        conflict_component * 0.20
    )
    impact_score = max(0, min(100, impact_score))

    return {
        "policy": policy,
        "impact_score": impact_score,
        "sub_scores": {
            "reach": reach_component, "artifacts": artifact_component,
            "risk": risk_component, "conflicts": conflict_component,
        },
        "reack_count": reack_count,
        "audience": audience,
        "audience_scope": audience_scope,
        "meeting_rows": meeting_rows,
        "quiz_count": quiz_count,
        "quiz_pass_rate": quiz_pass_rate,
        "whatif": whatif,
        "conflicts": conflicts,
        "risk_score": risk_score,
        "has_ai_insight": policy.ai_insight is not None,
    }


@blast_radius_bp.route("/policies/<int:policy_id>/blast-radius")
@login_required
@role_required(UserRole.HR, UserRole.ADMIN)
def preview(policy_id):
    policy = Policy.query.get_or_404(policy_id)
    data = compute_blast_radius(policy)
    return render_template("admin/blast_radius.html", **data)
