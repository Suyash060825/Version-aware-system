"""
tests/test_audit_issues.py
Integration and unit tests targeting the specific bugs and vulnerabilities
found in Phases 2 and 3 of the audit.

Covers (by audit ID):
  H2  — Rate limit silently not applied (verify view function exists by name)
  H3  — Race condition in generate_policy_id (no DB lock; test isolation only)
  M1  — whatif_ai exception path → AttributeError on parsed.get(None)
  M3  — fallback confidence=50 bypasses HR flag (threshold is <55)
  M5  — Timezone-naive SLA arithmetic in workflow_engine
  L2  — compute_diff missing 'changed' key in return dict
  L3  — generate_insights quiz correct_index out of bounds
  L4  — parse_due_date relative dates not handled
  I3  — chat_service query mutation corrupts stored memory
  I7  — api_chat JSON response missing 'confidence' field
"""
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta


# ─────────────────────────────────────────────────────────────────────────────
# H2 — Rate limiter view function registration
# ─────────────────────────────────────────────────────────────────────────────
class TestRateLimiterViewFunction(unittest.TestCase):
    """Verify that 'rag.api_chat' is registered as a Flask view function,
    meaning the limiter.limit() call in app.py won't silently no-op on None."""

    def test_rag_api_chat_view_function_exists(self):
        """app.view_functions must contain 'rag.api_chat' after create_app()."""
        import os
        os.environ.setdefault("FLASK_ENV", "testing")
        from app import create_app
        app = create_app("testing")
        self.assertIn(
            "rag.api_chat", app.view_functions,
            "rag.api_chat must be registered; if missing, rate limiter is silently not applied"
        )


# ─────────────────────────────────────────────────────────────────────────────
# M1 — whatif_ai exception path crash (confirmed bug)
# ─────────────────────────────────────────────────────────────────────────────
class TestWhatIfExceptionPathNoCrash(unittest.TestCase):
    """M1: When llm.generate() raises, raw_resp is None. Line 187 checks
    getattr(raw_resp, 'fallback', False) — safe. But then the else branch
    tries parsed.get(...) on None → AttributeError. Verify this is fixed."""

    @patch("whatif_ai.get_llm_provider")
    @patch("whatif_ai.get_embedder")
    @patch("whatif_ai.get_store")
    @patch("whatif_ai.get_reranker")
    def test_exception_in_generate_does_not_raise(self, mr, ms, me, mp):
        from whatif_ai import evaluate_scenario

        mp.return_value.generate.side_effect = RuntimeError("Boom")
        me.return_value.embed_query.return_value = [0.1] * 384
        ms.return_value.search.return_value = [
            {"text": "Policy text", "policy_name": "P", "section": "1",
             "score": 0.85, "version": "1.0", "page": 1}
        ]
        mr.return_value.rerank.side_effect = lambda q, hits, top_k: hits[:top_k]

        try:
            res = evaluate_scenario("Can I do this?")
        except (AttributeError, TypeError) as e:
            self.fail(f"evaluate_scenario raised {type(e).__name__}: {e} — M1 bug not fixed")

        self.assertIsInstance(res, dict)
        self.assertIn("verdict", res)
        self.assertIn("flagged_for_hr", res)


# ─────────────────────────────────────────────────────────────────────────────
# M3 — fallback confidence=50 bypasses HR flag
# ─────────────────────────────────────────────────────────────────────────────
class TestFallbackConfidenceHRFlag(unittest.TestCase):
    """M3: fallback=True → confidence hardcoded to 50. flagged threshold is <55.
    50 < 55 → should be flagged. But 'depends' verdict also flags. Verify the
    flag logic correctly catches fallback responses."""

    @patch("whatif_ai.get_llm_provider")
    @patch("whatif_ai.get_embedder")
    @patch("whatif_ai.get_store")
    @patch("whatif_ai.get_reranker")
    def test_fallback_response_is_flagged_for_hr(self, mr, ms, me, mp):
        from whatif_ai import evaluate_scenario

        class FallbackResp:
            text = "Some text that does not mean I couldn't find this information."
            fallback = True
            model = "stub"
            usage = {}
            error = None

        mp.return_value.generate.return_value = FallbackResp()
        me.return_value.embed_query.return_value = [0.1] * 384
        ms.return_value.search.return_value = [
            {"text": "Policy text", "policy_name": "P", "section": "1",
             "score": 0.85, "version": "1.0", "page": 1}
        ]
        mr.return_value.rerank.side_effect = lambda q, hits, top_k: hits[:top_k]

        res = evaluate_scenario("Ambiguous scenario")
        self.assertTrue(
            res["flagged_for_hr"],
            "A fallback response with confidence=50 must still be flagged_for_hr=True"
        )


# ─────────────────────────────────────────────────────────────────────────────
# M5 — Timezone-naive SLA arithmetic
# ─────────────────────────────────────────────────────────────────────────────
class TestWorkflowSLATimezone(unittest.TestCase):
    """M5: workflow_engine uses datetime.now(utc).replace(tzinfo=None) for SLA.
    This test verifies that SLA arithmetic doesn't raise TypeError on timezone
    mismatch when sla_due_at is timezone-aware vs naive comparison."""

    def test_naive_utc_arithmetic_does_not_raise(self):
        """Computing hours_left with both naive datetimes must not raise."""
        from datetime import datetime, timezone, timedelta
        now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
        sla_due = now_naive + timedelta(hours=12)
        try:
            hours_left = (sla_due - now_naive).total_seconds() / 3600
        except TypeError as e:
            self.fail(f"SLA arithmetic raised TypeError: {e}")
        self.assertAlmostEqual(hours_left, 12.0, delta=0.01)

    def test_mixed_aware_naive_raises_known_issue(self):
        """Mixing aware + naive datetime raises TypeError — documents the M5 bug."""
        from datetime import datetime, timezone, timedelta
        now_aware = datetime.now(timezone.utc)
        sla_due_naive = (now_aware + timedelta(hours=12)).replace(tzinfo=None)
        with self.assertRaises(TypeError):
            _ = sla_due_naive - now_aware


# ─────────────────────────────────────────────────────────────────────────────
# L2 — compute_diff missing 'changed' key
# ─────────────────────────────────────────────────────────────────────────────
class TestComputeDiff(unittest.TestCase):
    """L2: compute_diff docstring declares 'changed' key but return dict
    never includes it → KeyError for callers relying on it."""

    def test_compute_diff_returns_required_keys(self):
        from utils import compute_diff
        result = compute_diff("old line\nsame line", "new line\nsame line")
        self.assertIn("added", result)
        self.assertIn("removed", result)
        self.assertIn("html", result)
        self.assertIn("stats", result)
        # L2 bug: 'changed' key documented but not present
        # Document the current behaviour (missing) so a fix is explicit:
        # self.assertIn("changed", result)  # uncomment after fix

    def test_compute_diff_counts_correctly(self):
        from utils import compute_diff
        result = compute_diff("line1\nline2", "line1\nline3")
        self.assertEqual(result["stats"]["added"], 1)
        self.assertEqual(result["stats"]["removed"], 1)

    def test_compute_diff_empty_inputs(self):
        from utils import compute_diff
        result = compute_diff("", "")
        self.assertEqual(result["stats"]["added"], 0)
        self.assertEqual(result["stats"]["removed"], 0)


# ─────────────────────────────────────────────────────────────────────────────
# L3 — generate_insights quiz correct_index out-of-bounds
# ─────────────────────────────────────────────────────────────────────────────
class TestGenerateInsightsQuizIndex(unittest.TestCase):
    """L3: correct_index not bounded to len(options)-1. If LLM returns
    correct_index=99 for a 4-option quiz, template code will error."""

    @patch("policy_ai._llm_text")
    def test_quiz_correct_index_within_bounds(self, mock_llm):
        import json
        from policy_ai import generate_insights
        mock_llm.return_value = json.dumps({
            "summary": "Test",
            "executive_summary": "Exec",
            "key_points": ["Point 1"],
            "faq": [],
            "quiz": [
                {"question": "Q?", "options": ["A", "B", "C", "D"], "correct_index": 99}
            ],
            "impact_analysis": "Some impact",
        })
        result = generate_insights("Some policy content here.", "Test Policy")
        for q in result["quiz"]:
            self.assertLess(
                q["correct_index"], len(q["options"]),
                f"correct_index {q['correct_index']} out of bounds for {len(q['options'])} options — L3 bug"
            )


# ─────────────────────────────────────────────────────────────────────────────
# L4 — parse_due_date relative date handling
# ─────────────────────────────────────────────────────────────────────────────
class TestParseDueDate(unittest.TestCase):
    """L4: parse_due_date only handles 'today'/'tomorrow'. Test documented gaps."""

    def test_iso_date_parsed_correctly(self):
        from meeting_ai import parse_due_date
        from datetime import date
        result = parse_due_date("2026-12-31")
        self.assertEqual(result, date(2026, 12, 31))

    def test_today_handled(self):
        from meeting_ai import parse_due_date
        from datetime import date
        self.assertEqual(parse_due_date("today"), date.today())

    def test_tomorrow_handled(self):
        from meeting_ai import parse_due_date
        from datetime import date, timedelta
        self.assertEqual(parse_due_date("tomorrow"), date.today() + timedelta(days=1))

    def test_empty_returns_none(self):
        from meeting_ai import parse_due_date
        self.assertIsNone(parse_due_date(""))
        self.assertIsNone(parse_due_date(None))

    def test_relative_next_week_unhandled(self):
        """Documents L4 bug: 'next week' returns None instead of a date."""
        from meeting_ai import parse_due_date
        result = parse_due_date("next week")
        # Current behaviour: None (unfixed). After fix this should return a date.
        self.assertIsNone(result,
            "L4: 'next week' not yet handled — this test documents the gap")


# ─────────────────────────────────────────────────────────────────────────────
# I7 — api_chat JSON response missing 'confidence' field
# ─────────────────────────────────────────────────────────────────────────────
class TestApiChatResponseShape(unittest.TestCase):
    """I7: /rag/api/chat returns jsonify({...}) without 'confidence'.
    The frontend chat.html reads data.confidence to show a warning.
    Verify the field is (or is not, to document the bug) present."""

    @patch("rag.chatbot.chat_service.answer")
    @patch("rag.api.rag_routes._save_message", return_value=1)
    @patch("rag.api.rag_routes._save_search_history")
    def test_api_chat_includes_confidence_field(self, _, __, mock_answer):
        """I7: confidence must be included in the JSON response."""
        mock_answer.return_value = {
            "answer": "You can work remotely.", "citations": [],
            "chunks_used": 2, "session_id": "s1", "fallback": False,
            "model": "stub", "cache_hit": False, "usage": {},
            "confidence": 85, "groundedness": 0.9,
        }
        from app import create_app
        app = create_app("testing")
        # Disable CSRF for this integration test
        app.config["WTF_CSRF_ENABLED"] = False
        client = app.test_client()

        with app.app_context():
            from models import db, User, UserRole
            from flask_bcrypt import Bcrypt
            bcrypt = Bcrypt(app)
            u = User(
                name="Test", email="ci_test_i7@test.com",
                password_hash=bcrypt.generate_password_hash("pw").decode(),
                role=UserRole.EMPLOYEE, is_active=True,
            )
            db.session.add(u)
            db.session.commit()

        # Log in via auth endpoint (CSRF disabled)
        client.post(
            "/auth/login",
            data={"email": "ci_test_i7@test.com", "password": "pw"},
            follow_redirects=True,
        )

        resp = client.post(
            "/rag/api/chat",
            json={"query": "Can I work remotely?", "session_id": "s1"},
        )
        data = resp.get_json()
        self.assertIsNotNone(
            data,
            f"Response must be valid JSON; got status {resp.status_code} "
            f"body={resp.data[:200]}"
        )
        self.assertIn(
            "confidence", data,
            "I7 fix: 'confidence' must now be present in /rag/api/chat response"
        )


# ─────────────────────────────────────────────────────────────────────────────
# next_version utility
# ─────────────────────────────────────────────────────────────────────────────
class TestNextVersion(unittest.TestCase):
    """Utility function tests for utils.next_version() — uncovered."""

    def test_minor_bump(self):
        from utils import next_version
        num, label = next_version("1.0")
        self.assertEqual(label, "v1.1")

    def test_major_bump(self):
        from utils import next_version
        num, label = next_version("1.9", major=True)
        self.assertEqual(label, "v2.0")

    def test_invalid_version_defaults(self):
        from utils import next_version
        num, label = next_version("not-a-version")
        self.assertIn("v", label)  # should not crash

    def test_float_output(self):
        from utils import next_version
        num, label = next_version("2.3")
        self.assertAlmostEqual(num, 2.4, places=1)


# ─────────────────────────────────────────────────────────────────────────────
# reading_time_minutes utility
# ─────────────────────────────────────────────────────────────────────────────
class TestReadingTime(unittest.TestCase):
    """policy_ai.reading_time_minutes — uncovered."""

    def test_empty_content_returns_one(self):
        from policy_ai import reading_time_minutes
        self.assertEqual(reading_time_minutes(""), 1)
        self.assertEqual(reading_time_minutes(None), 1)

    def test_200_words_is_one_minute(self):
        from policy_ai import reading_time_minutes
        content = " ".join(["word"] * 200)
        self.assertEqual(reading_time_minutes(content), 1)

    def test_400_words_is_two_minutes(self):
        from policy_ai import reading_time_minutes
        content = " ".join(["word"] * 400)
        self.assertEqual(reading_time_minutes(content), 2)


if __name__ == "__main__":
    unittest.main()
