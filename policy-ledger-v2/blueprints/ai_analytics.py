"""
blueprints/ai_analytics.py
Module 17: AI Analytics

Distinct from the Confusion Index (Module: which policies are hard to
understand) — this dashboard looks at the AI layer itself: is the chatbot
answering well, what does it not know, and roughly what is it costing.
Pure aggregation over ChatMessage/ChatSession/Feedback/SearchHistory —
no new tables, degrades gracefully to "no data yet" on a fresh install.

Shows:
  Top questions           most frequent normalized user queries
  Unknown questions       zero-result / unanswered SearchHistory rows
  Failed answers          assistant messages that got a thumbs-down
  AI accuracy             thumbs-up ratio across all rated answers
  Popular policies        most-cited policies in chatbot answers
  Employee sentiment      heuristic positive/negative split of feedback comments
                          (keyword-based — NOT a trained sentiment model; labelled
                          as an estimate, not a scientific measure)
  Token usage / cost      character-based token estimate (~4 chars/token) and an
                          estimated cost at a configurable $/1K rate — no live
                          token metering exists yet, so this is clearly labelled
                          as an approximation, not billed spend
  Knowledge gaps          repeated (2+) unanswered queries — same question
                          nobody could answer more than once is a documentation gap

Routes:
  GET /admin/ai-analytics
"""
import json
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from flask import Blueprint, render_template
from flask_login import login_required

from models import (ChatMessage, ChatSession, Feedback, SearchHistory,
                    Policy, UserRole)
from utils import role_required

ai_analytics_bp = Blueprint("ai_analytics", __name__, url_prefix="/admin")

# Rough, clearly-labelled estimate — no live token metering is wired up yet.
CHARS_PER_TOKEN = 4
EST_COST_PER_1K_TOKENS = 0.004  # blended input/output estimate, USD

_POSITIVE_WORDS = {"great", "helpful", "thanks", "thank", "good", "clear",
                    "useful", "perfect", "awesome", "nice", "accurate", "love"}
_NEGATIVE_WORDS = {"wrong", "confusing", "bad", "useless", "unclear", "incorrect",
                    "unhelpful", "broken", "slow", "hate", "frustrating", "outdated"}


def _normalize(text: str) -> str:
    text = (text or "").strip().lower()
    text = re.sub(r"[^a-z0-9\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _top_questions(limit=10):
    counts = defaultdict(int)
    samples = {}
    msgs = ChatMessage.query.filter_by(role="user").all()
    for m in msgs:
        key = _normalize(m.content)
        if not key:
            continue
        counts[key] += 1
        samples.setdefault(key, m.content.strip())
    ranked = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:limit]
    return [{"question": samples[k], "count": c} for k, c in ranked]


def _unknown_questions(limit=15):
    rows = (SearchHistory.query
            .filter((SearchHistory.chunks_found == 0) | (SearchHistory.answered == False))
            .order_by(SearchHistory.created_at.desc()).limit(200).all())
    return rows[:limit], rows


def _knowledge_gaps(unknown_rows, min_repeat=2):
    counts = defaultdict(int)
    samples = {}
    for r in unknown_rows:
        key = _normalize(r.query_text)
        if not key:
            continue
        counts[key] += 1
        samples.setdefault(key, r.query_text.strip())
    gaps = [{"query": samples[k], "times_asked": c}
           for k, c in counts.items() if c >= min_repeat]
    gaps.sort(key=lambda g: g["times_asked"], reverse=True)
    return gaps[:15]


def _failed_answers(limit=15):
    downs = (Feedback.query.filter_by(vote="down")
             .order_by(Feedback.created_at.desc()).limit(200).all())
    out = []
    for f in downs[:limit]:
        msg = ChatMessage.query.get(f.message_id) if f.message_id else None
        out.append({
            "answer": (msg.content[:220] if msg else "(message not found)"),
            "comment": f.comment,
            "created_at": f.created_at,
        })
    return out, len(downs)


def _ai_accuracy():
    up = Feedback.query.filter_by(vote="up").count()
    down = Feedback.query.filter_by(vote="down").count()
    total = up + down
    return {
        "up": up, "down": down, "total": total,
        "accuracy_pct": round(100 * up / total, 1) if total else None,
    }


def _popular_policies(limit=10):
    counts = defaultdict(int)
    for m in ChatMessage.query.filter_by(role="assistant").all():
        try:
            citations = json.loads(m.citations_json) if m.citations_json else []
        except (ValueError, TypeError):
            citations = []
        seen = set()
        for c in citations:
            try:
                pid = int(c.get("policy_id"))
            except (TypeError, ValueError):
                continue
            seen.add(pid)
        for pid in seen:
            counts[pid] += 1
    ranked = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:limit]
    out = []
    for pid, cnt in ranked:
        p = Policy.query.get(pid)
        if p:
            out.append({"policy": p, "citation_count": cnt})
    return out


def _sentiment():
    comments = [f.comment for f in Feedback.query.filter(
        Feedback.comment.isnot(None), Feedback.comment != "").all()]
    pos = neg = neutral = 0
    for c in comments:
        words = set(_normalize(c).split())
        has_pos = bool(words & _POSITIVE_WORDS)
        has_neg = bool(words & _NEGATIVE_WORDS)
        if has_pos and not has_neg:
            pos += 1
        elif has_neg and not has_pos:
            neg += 1
        else:
            neutral += 1
    total = pos + neg + neutral
    return {"positive": pos, "negative": neg, "neutral": neutral, "total": total}


def _token_usage():
    """Character-based estimate, bucketed by day for the last 14 days."""
    since = datetime.now(timezone.utc) - timedelta(days=14)
    msgs = ChatMessage.query.filter(ChatMessage.created_at >= since).all()
    daily = defaultdict(int)
    total_chars = 0
    for m in msgs:
        chars = len(m.content or "")
        total_chars += chars
        daily[m.created_at.date().isoformat()] += chars

    total_tokens_est = total_chars // CHARS_PER_TOKEN
    cost_est = round(total_tokens_est / 1000 * EST_COST_PER_1K_TOKENS, 2)

    daily_series = sorted(
        [{"date": d, "tokens_est": chars // CHARS_PER_TOKEN} for d, chars in daily.items()],
        key=lambda r: r["date"])

    return {
        "message_count": len(msgs),
        "total_tokens_est": total_tokens_est,
        "cost_est_usd": cost_est,
        "daily_series": daily_series,
        "rate_per_1k": EST_COST_PER_1K_TOKENS,
    }


@ai_analytics_bp.route("/ai-analytics")
@login_required
@role_required(UserRole.HR, UserRole.ADMIN)
def dashboard():
    top_questions = _top_questions()
    unknown_top, unknown_all = _unknown_questions()
    gaps = _knowledge_gaps(unknown_all)
    failed, failed_total = _failed_answers()
    accuracy = _ai_accuracy()
    popular = _popular_policies()
    sentiment = _sentiment()
    tokens = _token_usage()

    total_sessions = ChatSession.query.count()
    total_messages = ChatMessage.query.count()

    return render_template("admin/ai_analytics.html",
        top_questions=top_questions, unknown_top=unknown_top,
        unknown_total=len(unknown_all), gaps=gaps,
        failed=failed, failed_total=failed_total, accuracy=accuracy,
        popular=popular, sentiment=sentiment, tokens=tokens,
        total_sessions=total_sessions, total_messages=total_messages,
    )
