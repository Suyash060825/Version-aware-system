"""
blueprints/gamification.py
Module 19: Gamification & Rewards

Like Confusion Index / Governance Health, this is a pure aggregation over
signals the app already logs — no new ledger table, no risk of the points
total drifting out of sync with what actually happened. Points are computed
live from QuizAttempt, PolicyAcknowledgement, PolicyComment, PolicyLike,
OnboardingChecklistItem and MeetingActionItem every time the page loads.

Points formula (per user):
  +10   each QuizAttempt that passed
  +5    each mandatory PolicyAcknowledgement completed within 7 days of the
        policy becoming active (on-time), else +2 (late-but-done still counts)
  +3    each PolicyComment authored
  +2    each PolicyLike given
  +8    each OnboardingChecklistItem completed
  +5    each MeetingActionItem completed where the user is the owner

Badges (thresholds evaluated against the same totals — no separate storage):
  First Steps        - 1+ quiz passed
  Quiz Master         - 10+ quizzes passed
  Fast Reader         - 5+ on-time mandatory acknowledgements
  Compliance Champion - 100% of assigned mandatory policies acknowledged
  Team Player         - 5+ comments authored
  On a Roll           - current activity streak of 5+ days
  Action Hero         - 10+ completed meeting action items

Streak: consecutive calendar days (ending today or yesterday, so a day not
yet started doesn't break it) on which the user logged at least one quiz
attempt or acknowledgement.

Routes:
  GET /rewards                 employee: my points, badges, streak, rank
  GET /admin/leaderboard        hr/admin: org-wide + department leaderboard
"""
from collections import defaultdict
from datetime import date, timedelta

from flask import Blueprint, render_template
from flask_login import login_required, current_user

from models import (User, UserRole, QuizAttempt, PolicyAcknowledgement, PolicyComment,
                    PolicyLike, OnboardingChecklistItem, MeetingActionItem,
                    ActionItemStatus, Policy)
from utils import role_required

gamification_bp = Blueprint("gamification", __name__)

ON_TIME_WINDOW_DAYS = 7

BADGE_DEFS = [
    ("first_steps", "First Steps", "Passed your first quiz", "🌱"),
    ("quiz_master", "Quiz Master", "Passed 10+ quizzes", "🎓"),
    ("fast_reader", "Fast Reader", "5+ on-time acknowledgements", "⚡"),
    ("compliance_champion", "Compliance Champion", "100% mandatory policies acknowledged", "🏆"),
    ("team_player", "Team Player", "5+ policy comments", "💬"),
    ("on_a_roll", "On a Roll", "5+ day activity streak", "🔥"),
    ("action_hero", "Action Hero", "10+ completed action items", "✅"),
]


def _activity_dates(user_id):
    """Set of dates(user was active) from quiz attempts + acknowledgements."""
    dates = set()
    for (d,) in QuizAttempt.query.filter_by(user_id=user_id).with_entities(QuizAttempt.completed_at).all():
        if d:
            dates.add(d.date())
    for (d,) in (PolicyAcknowledgement.query.filter_by(user_id=user_id)
                 .filter(PolicyAcknowledgement.acknowledged_at.isnot(None))
                 .with_entities(PolicyAcknowledgement.acknowledged_at).all()):
        if d:
            dates.add(d.date())
    return dates


def _streak(dates):
    if not dates:
        return 0
    today = date.today()
    cursor = today if today in dates else today - timedelta(days=1)
    if cursor not in dates:
        return 0
    streak = 0
    while cursor in dates:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def _mandatory_ack_rate(user):
    """% of currently-active mandatory policies this user has acknowledged."""
    mandatory = Policy.query.filter_by(status="active", is_mandatory=True).all()
    if not mandatory:
        return 100.0
    acked_ids = {a.policy_id for a in PolicyAcknowledgement.query.filter_by(
        user_id=user.id).filter(PolicyAcknowledgement.acknowledged_at.isnot(None)).all()}
    done = sum(1 for p in mandatory if p.id in acked_ids)
    return round(100 * done / len(mandatory), 1)


def compute_user_stats(user):
    quizzes = QuizAttempt.query.filter_by(user_id=user.id, passed=True).all()
    acks = (PolicyAcknowledgement.query.filter_by(user_id=user.id)
            .filter(PolicyAcknowledgement.acknowledged_at.isnot(None)).all())
    comments = PolicyComment.query.filter_by(user_id=user.id).count()
    likes = PolicyLike.query.filter_by(user_id=user.id).count()
    onboarding_done = OnboardingChecklistItem.query.filter_by(user_id=user.id, is_done=True).count()
    action_items_done = MeetingActionItem.query.filter_by(
        owner_id=user.id, status=ActionItemStatus.DONE).count()

    on_time = 0
    late = 0
    for a in acks:
        policy = a.policy
        anchor = (policy.effective_date if policy and policy.effective_date else
                  (policy.created_at.date() if policy else None))
        if anchor and (a.acknowledged_at.date() - anchor).days <= ON_TIME_WINDOW_DAYS:
            on_time += 1
        else:
            late += 1

    points = (len(quizzes) * 10 + on_time * 5 + late * 2 + comments * 3 +
              likes * 2 + onboarding_done * 8 + action_items_done * 5)

    ack_rate = _mandatory_ack_rate(user)
    streak = _streak(_activity_dates(user.id))

    earned = set()
    if len(quizzes) >= 1:
        earned.add("first_steps")
    if len(quizzes) >= 10:
        earned.add("quiz_master")
    if on_time >= 5:
        earned.add("fast_reader")
    if ack_rate >= 100:
        earned.add("compliance_champion")
    if comments >= 5:
        earned.add("team_player")
    if streak >= 5:
        earned.add("on_a_roll")
    if action_items_done >= 10:
        earned.add("action_hero")

    return {
        "user": user,
        "points": points,
        "quizzes_passed": len(quizzes),
        "on_time_acks": on_time,
        "late_acks": late,
        "comments": comments,
        "likes": likes,
        "onboarding_done": onboarding_done,
        "action_items_done": action_items_done,
        "ack_rate": ack_rate,
        "streak": streak,
        "badges": [b for b in BADGE_DEFS if b[0] in earned],
        "badge_count": len(earned),
    }


@gamification_bp.route("/rewards")
@login_required
def my_rewards():
    stats = compute_user_stats(current_user)

    all_users = User.query.filter_by(is_active=True).all()
    ranked = sorted((compute_user_stats(u) for u in all_users),
                    key=lambda s: s["points"], reverse=True)
    rank = next((i + 1 for i, s in enumerate(ranked) if s["user"].id == current_user.id), None)

    return render_template("employee/rewards.html", stats=stats,
                           rank=rank, total_users=len(ranked),
                           all_badges=BADGE_DEFS)


@gamification_bp.route("/admin/leaderboard")
@login_required
@role_required(UserRole.HR, UserRole.ADMIN, UserRole.MANAGER)
def leaderboard():
    all_users = User.query.filter_by(is_active=True).all()
    ranked = sorted((compute_user_stats(u) for u in all_users),
                    key=lambda s: s["points"], reverse=True)

    dept_totals = defaultdict(lambda: {"points": 0, "count": 0, "name": "Unassigned"})
    for s in ranked:
        dept = s["user"].department
        key = dept.id if dept else 0
        dept_totals[key]["name"] = dept.name if dept else "Unassigned"
        dept_totals[key]["points"] += s["points"]
        dept_totals[key]["count"] += 1

    dept_ranking = sorted(
        ({"name": v["name"], "total_points": v["points"], "headcount": v["count"],
          "avg_points": round(v["points"] / v["count"], 1) if v["count"] else 0}
         for v in dept_totals.values()),
        key=lambda d: d["avg_points"], reverse=True)

    return render_template("admin/leaderboard.html", ranked=ranked[:50],
                           dept_ranking=dept_ranking)
