"""
blueprints/what_if.py
Module 25: Policy Impact Simulator ("What-If" Compliance Checker)

New capability, not present anywhere else in the app: instead of asking a
question and getting a conversational answer (Module 3 / AI Assistant), an
employee describes a real decision or situation they're considering, and
gets back a structured verdict — Compliant / Not Compliant / Depends /
Unclear — with the exact policy sections it's based on, concrete required
next steps, and a confidence score. Ambiguous or risky scenarios are
automatically flagged into an HR queue, turning fuzzy "am I allowed to..."
questions into something HR/Compliance can proactively review instead of
waiting for a ticket or a mistake.

Routes:
  GET  /what-if                  form + (if ?scenario= or POSTed) result
  POST /what-if                  run a new scenario
  GET  /what-if/history          the current user's past scenarios
  GET  /admin/what-if-queue      HR/Admin: flagged scenarios across all employees
  POST /admin/what-if/<id>/resolve   HR/Admin: mark a flagged scenario reviewed
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from models import db, WhatIfQuery, UserRole, Notification
from utils import audit, role_required
from whatif_ai import evaluate_scenario

what_if_bp = Blueprint("what_if", __name__)


def _unread_count():
    return Notification.query.filter_by(user_id=current_user.id, is_read=False).count()


@what_if_bp.route("/what-if", methods=["GET", "POST"])
@login_required
def simulator():
    scenario = ""
    result = None

    if request.method == "POST":
        scenario = (request.form.get("scenario") or "").strip()
        if not scenario:
            flash("Describe a scenario first — e.g. \"Can I expense a personal phone under $300?\"", "warning")
            return redirect(url_for("what_if.simulator"))
        if len(scenario) > 800:
            flash("Please keep the scenario under 800 characters.", "warning")
            return redirect(url_for("what_if.simulator"))

        dept = current_user.department.name if current_user.department else ""
        try:
            ai_result = evaluate_scenario(
                scenario=scenario, user_role=current_user.role, user_department=dept,
            )
        except Exception:
            ai_result = {
                "verdict": "unclear", "confidence": 0,
                "explanation": "The simulator couldn't complete this check right now. Please try again "
                               "shortly or ask HR directly.",
                "required_actions": [], "citations": [], "flagged_for_hr": True, "chunks_used": 0,
            }

        record = WhatIfQuery(
            user_id=current_user.id,
            scenario_text=scenario,
            verdict=ai_result["verdict"],
            confidence=ai_result["confidence"],
            explanation=ai_result["explanation"],
            flagged_for_hr=ai_result["flagged_for_hr"],
        )
        record.required_actions = ai_result["required_actions"]
        record.applicable_policies = ai_result["citations"]
        db.session.add(record)
        db.session.commit()
        audit("what_if.run", "what_if_query", record.id,
              {"verdict": record.verdict, "confidence": record.confidence})

        result = {
            "id": record.id, "verdict": ai_result["verdict"], "confidence": ai_result["confidence"],
            "explanation": ai_result["explanation"], "required_actions": ai_result["required_actions"],
            "citations": ai_result["citations"], "flagged_for_hr": ai_result["flagged_for_hr"],
        }

    return render_template("employee/what_if.html",
        scenario=scenario, result=result, unread_count=_unread_count())


@what_if_bp.route("/what-if/history")
@login_required
def history():
    queries = WhatIfQuery.query.filter_by(user_id=current_user.id)\
        .order_by(WhatIfQuery.created_at.desc()).limit(50).all()
    return render_template("employee/what_if_history.html",
        queries=queries, unread_count=_unread_count())


# ================================================================
# HR / Admin queue of flagged (grey-area / risky) scenarios
# ================================================================
@what_if_bp.route("/admin/what-if-queue")
@login_required
@role_required(UserRole.ADMIN, UserRole.HR)
def review_queue():
    status = request.args.get("status", "open")
    q = WhatIfQuery.query.filter_by(flagged_for_hr=True)
    if status == "open":
        pass  # flagged_for_hr stays True until resolved (we clear the flag on resolve)
    queries = q.order_by(WhatIfQuery.created_at.desc()).limit(200).all()
    total_runs = WhatIfQuery.query.count()
    return render_template("admin/what_if_queue.html",
        queries=queries, total_runs=total_runs)


@what_if_bp.route("/admin/what-if/<int:query_id>/resolve", methods=["POST"])
@login_required
@role_required(UserRole.ADMIN, UserRole.HR)
def resolve(query_id):
    record = WhatIfQuery.query.get_or_404(query_id)
    record.flagged_for_hr = False
    db.session.commit()
    audit("what_if.resolve", "what_if_query", record.id)
    flash("Marked as reviewed.", "success")
    return redirect(url_for("what_if.review_queue"))
