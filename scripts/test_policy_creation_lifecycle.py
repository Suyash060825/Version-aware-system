#!/usr/bin/env python3
"""
Comprehensive Policy Creation Lifecycle Test
Tests all pathways of policy creation to ensure uniform compilation,
chunking, fact extraction, canonical QA synthesis, BM25 indexing, FAISS vector
indexing, and real-time dashboard metric updates.
"""
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from models import (
    db, User, UserRole, Policy, PolicyVersion, PolicyStatus,
    PolicyChunkV2, PolicyFact, CanonicalQuestion, CompiledAnswer,
    CompilationJob
)
from rag.retrieval.sparse import PersistentBM25Index
from rag.qa.qa_index import CanonicalQAIndex
from rag.vectordb.chroma import get_store


class TestPolicyCreationLifecycle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.app.config["WTF_CSRF_ENABLED"] = False
        cls.client = cls.app.test_client()

        with cls.app.app_context():
            admin_user = User.query.filter(User.role.in_([UserRole.ADMIN, UserRole.HR])).first()
            if not admin_user:
                raise RuntimeError("No admin/hr user found in database.")
            cls.admin_id = admin_user.id
            cls.admin_email = admin_user.email

            # Clean up prior test runs
            test_titles = [
                "Automated Lifecycle Test Policy Alpha",
                "Copy of Automated Lifecycle Test Policy Alpha",
                "Healthcare Benefits Guidelines",
            ]
            for t in test_titles:
                for old_p in Policy.query.filter_by(title=t).all():
                    for v in old_p.versions:
                        PolicyChunkV2.query.filter_by(policy_id=old_p.id, version_id=v.id).delete()
                        PolicyFact.query.filter_by(policy_id=old_p.id, version_id=v.id).delete()
                        q_ids = [q.id for q in CanonicalQuestion.query.filter_by(policy_id=old_p.id, version_id=v.id).all()]
                        if q_ids:
                            CompiledAnswer.query.filter(CompiledAnswer.question_id.in_(q_ids)).delete(synchronize_session=False)
                            CanonicalQuestion.query.filter_by(policy_id=old_p.id, version_id=v.id).delete()
                        CompilationJob.query.filter_by(policy_id=old_p.id, version_id=v.id).delete()
                        db.session.delete(v)
                    db.session.delete(old_p)
            db.session.commit()

            # Ensure indexes are refreshed
            PersistentBM25Index().rebuild_from_db()
            CanonicalQAIndex().rebuild_from_db()

    def _login(self):
        with self.client.session_transaction() as sess:
            sess["_user_id"] = str(self.admin_id)
            sess["_fresh"] = True

    def _get_dashboard_counts(self):
        with self.app.app_context():
            policies_total = Policy.query.count()
            active_policies = Policy.query.filter_by(status=PolicyStatus.ACTIVE).count()
            total_chunks = PolicyChunkV2.query.count()
            total_facts = PolicyFact.query.count()
            total_qas = CanonicalQuestion.query.count()
            indexed_policies = db.session.query(PolicyChunkV2.policy_id).distinct().count()

            bm25 = PersistentBM25Index()
            bm25_count = len(bm25._corpus)

            qa_index = CanonicalQAIndex()
            faiss_count = ((qa_index._base_index.ntotal if qa_index._base_index else 0) +
                           (qa_index._delta_index.ntotal if qa_index._delta_index else 0))

            return {
                "policies_total": policies_total,
                "active_policies": active_policies,
                "total_chunks": total_chunks,
                "total_facts": total_facts,
                "total_qas": total_qas,
                "indexed_policies": indexed_policies,
                "bm25_count": bm25_count,
                "faiss_count": faiss_count,
            }

    def test_01_create_policy_standard_form(self):
        """Method 1: Create policy via /admin/policies/new form."""
        self._login()
        base = self._get_dashboard_counts()
        print(f"\n[TEST 1] Baseline metrics: chunks={base['total_chunks']}, facts={base['total_facts']}, qas={base['total_qas']}, indexed={base['indexed_policies']}, faiss={base['faiss_count']}")

        resp = self.client.post("/admin/policies/new", data={
            "title": "Automated Lifecycle Test Policy Alpha",
            "description": "Verification of automatic indexing upon policy creation.",
            "content": (
                "Section 1: General Leave Policy.\n"
                "All full-time employees are entitled to 25 days annual leave per calendar year.\n"
                "Employees are also granted 12 days sick leave with full compensation.\n\n"
                "Section 2: Remote Work Allowances.\n"
                "Eligible team members may work remotely up to 3 days per week.\n"
                "The company provides Rs. 2,500 internet reimbursement per month for remote connectivity."
            ),
            "priority": "high",
            "confidentiality": "internal",
            "effective_date": "2026-09-01",
        }, follow_redirects=False)
        self.assertEqual(resp.status_code, 302)

        after = self._get_dashboard_counts()
        print(f"[TEST 1] After creation: chunks={after['total_chunks']} (+{after['total_chunks'] - base['total_chunks']}), facts={after['total_facts']} (+{after['total_facts'] - base['total_facts']}), qas={after['total_qas']} (+{after['total_qas'] - base['total_qas']})")

        self.assertGreater(after["policies_total"], base["policies_total"])
        self.assertGreater(after["total_chunks"], base["total_chunks"])
        self.assertGreater(after["total_facts"], base["total_facts"])
        self.assertGreater(after["total_qas"], base["total_qas"])
        self.assertGreater(after["indexed_policies"], base["indexed_policies"])
        self.assertGreater(after["bm25_count"], base["bm25_count"])
        self.assertGreater(after["faiss_count"], base["faiss_count"])

        # Check compilation job
        with self.app.app_context():
            p = Policy.query.filter_by(title="Automated Lifecycle Test Policy Alpha").first()
            self.assertIsNotNone(p)
            v = p.versions.first()
            self.assertIsNotNone(v)
            cjob = CompilationJob.query.filter_by(policy_id=p.id, version_id=v.id).first()
            self.assertIsNotNone(cjob)
            self.assertEqual(cjob.stage, "ready")
            self.assertGreater(cjob.chunk_count, 0)
            self.assertGreater(cjob.fact_count, 0)
            self.assertGreater(cjob.qa_count, 0)

        # Check /admin/ dashboard response contains updated counters
        admin_resp = self.client.get("/admin/")
        self.assertEqual(admin_resp.status_code, 200)
        html = admin_resp.data.decode("utf-8")
        self.assertIn(f"{after['total_chunks']}</div>\n      <div class=\"stat-label\">Semantic chunks</div>", html)
        self.assertIn("Automated Lifecycle Test Policy Alpha", html)

    def test_02_create_policy_from_file_extract(self):
        """Method 2: Extract text from uploaded document then create policy."""
        self._login()
        base = self._get_dashboard_counts()

        # Step A: Hit extract-file
        file_content = (
            "Section 1: Healthcare Benefits.\n"
            "The organization provides Rs. 500,000 base medical insurance cover for all permanent staff.\n"
            "An annual OPD limit of Rs. 15,000 is reimbursed upon receipt submission.\n\n"
            "Section 2: Separation Guidelines.\n"
            "Employees in senior roles are subject to a notice period of 90 days prior to departure."
        ).encode("utf-8")
        
        extract_resp = self.client.post("/admin/policies/extract-file", data={
            "file": (io.BytesIO(file_content), "healthcare_benefits.txt")
        }, content_type="multipart/form-data")
        self.assertEqual(extract_resp.status_code, 200)
        extract_data = extract_resp.get_json()
        self.assertTrue(extract_data.get("success"))
        self.assertIn("Healthcare Benefits", extract_data.get("content"))

        # Step B: Submit form with extracted content
        resp = self.client.post("/admin/policies/new", data={
            "title": extract_data.get("suggested_title", "Healthcare Benefits Guidelines"),
            "description": "Extracted from healthcare_benefits.txt",
            "content": extract_data.get("content"),
            "priority": "medium",
            "confidentiality": "internal",
        }, follow_redirects=False)
        self.assertEqual(resp.status_code, 302)

        after = self._get_dashboard_counts()
        print(f"[TEST 2] File-extract created: chunks={after['total_chunks']} (+{after['total_chunks'] - base['total_chunks']}), facts={after['total_facts']} (+{after['total_facts'] - base['total_facts']})")
        self.assertGreater(after["total_chunks"], base["total_chunks"])
        self.assertGreater(after["total_facts"], base["total_facts"])
        self.assertGreater(after["total_qas"], base["total_qas"])

    def test_03_create_new_version(self):
        """Method 3: Create a new version of an existing policy (/admin/policies/<id>/versions/new)."""
        self._login()
        with self.app.app_context():
            p = Policy.query.filter_by(title="Automated Lifecycle Test Policy Alpha").first()
            policy_id = p.id

        base = self._get_dashboard_counts()

        resp = self.client.post(f"/admin/policies/{policy_id}/versions/new", data={
            "content": (
                "Section 1: General Leave Policy (Amended).\n"
                "All full-time employees are entitled to 30 days annual leave per calendar year.\n"
                "Employees are also granted 14 days sick leave with full compensation.\n"
                "Parental benefits include maternity: 26 weeks and paternity: 4 weeks.\n\n"
                "Section 2: Remote Work and Travel.\n"
                "Eligible team members may work remotely up to 4 days per week.\n"
                "Daily allowance is Rs. 1,500 for metro cities and Rs. 1,000 for non-metro cities."
            ),
            "summary": "Increased annual leave to 30 days, sick leave to 14 days, remote allowance to 4 days.",
            "change_reason": "Enhanced global wellness benefits",
            "bump_type": "minor",
        }, follow_redirects=False)
        self.assertEqual(resp.status_code, 302)

        after = self._get_dashboard_counts()
        print(f"[TEST 3] New version created: chunks={after['total_chunks']} (+{after['total_chunks'] - base['total_chunks']}), facts={after['total_facts']} (+{after['total_facts'] - base['total_facts']})")
        self.assertGreater(after["total_chunks"], base["total_chunks"])
        self.assertGreater(after["total_facts"], base["total_facts"])

        with self.app.app_context():
            p = db.session.get(Policy, policy_id)
            active_ver = p.versions.filter_by(is_active=True).first()
            self.assertEqual(active_ver.version_label, "v1.1")
            cjob = CompilationJob.query.filter_by(policy_id=policy_id, version_id=active_ver.id).first()
            self.assertIsNotNone(cjob)
            self.assertEqual(cjob.stage, "ready")

    def test_04_duplicate_policy(self):
        """Method 4: Duplicate an existing policy (/admin/policies/<id>/duplicate)."""
        self._login()
        with self.app.app_context():
            p = Policy.query.filter_by(title="Automated Lifecycle Test Policy Alpha").first()
            policy_id = p.id

        base = self._get_dashboard_counts()

        resp = self.client.post(f"/admin/policies/{policy_id}/duplicate", follow_redirects=False)
        self.assertEqual(resp.status_code, 302)

        after = self._get_dashboard_counts()
        print(f"[TEST 4] Duplicated policy: chunks={after['total_chunks']} (+{after['total_chunks'] - base['total_chunks']}), facts={after['total_facts']} (+{after['total_facts'] - base['total_facts']})")
        self.assertGreater(after["policies_total"], base["policies_total"])
        self.assertGreater(after["total_chunks"], base["total_chunks"])
        self.assertGreater(after["total_facts"], base["total_facts"])
        self.assertGreater(after["indexed_policies"], base["indexed_policies"])

        with self.app.app_context():
            dup = Policy.query.filter_by(title="Copy of Automated Lifecycle Test Policy Alpha").first()
            self.assertIsNotNone(dup)
            v = dup.versions.filter_by(is_active=True).first()
            self.assertIsNotNone(v)
            cjob = CompilationJob.query.filter_by(policy_id=dup.id, version_id=v.id).first()
            self.assertIsNotNone(cjob)
            self.assertEqual(cjob.stage, "ready")

    def test_05_apply_ai_content_version(self):
        """Method 5: Apply AI Assistant edits creating a new version (/admin/policies/<id>/ai/apply)."""
        self._login()
        with self.app.app_context():
            p = Policy.query.filter_by(title="Automated Lifecycle Test Policy Alpha").first()
            policy_id = p.id

        base = self._get_dashboard_counts()

        resp = self.client.post(f"/admin/policies/{policy_id}/ai/apply", data={
            "content": (
                "Section 1: AI Enhanced Operations & Leaves.\n"
                "All engineers are allotted 28 days annual leave and 15 days sick leave.\n"
                "Work schedule allows core hours (10:00 AM - 4:00 PM) with 15 minutes grace period.\n\n"
                "Section 2: Travel & Lodging.\n"
                "For domestic travel, maximum Rs. 4,000 for domestic travel per night is reimbursed."
            ),
            "summary": "AI modernized operational schedules, hotel limits, and leave allocations.",
            "bump_type": "major"
        }, follow_redirects=False)
        self.assertEqual(resp.status_code, 302)

        after = self._get_dashboard_counts()
        print(f"[TEST 5] AI content applied: chunks={after['total_chunks']} (+{after['total_chunks'] - base['total_chunks']}), facts={after['total_facts']} (+{after['total_facts'] - base['total_facts']})")
        self.assertGreater(after["total_chunks"], base["total_chunks"])
        self.assertGreater(after["total_facts"], base["total_facts"])

        with self.app.app_context():
            p = db.session.get(Policy, policy_id)
            active_ver = p.versions.filter_by(is_active=True).first()
            self.assertEqual(active_ver.version_label, "v2.0")
            cjob = CompilationJob.query.filter_by(policy_id=policy_id, version_id=active_ver.id).first()
            self.assertIsNotNone(cjob)
            self.assertEqual(cjob.stage, "ready")

    def test_06_rag_dashboard_kpis_reflect_all_changes(self):
        """Verify that /rag/admin/dashboard displays true live counters and recent jobs."""
        self._login()
        counts = self._get_dashboard_counts()

        rag_resp = self.client.get("/rag/admin/dashboard")
        self.assertEqual(rag_resp.status_code, 200)
        html = rag_resp.data.decode("utf-8")

        # Verify indexed policies card shows true count
        self.assertIn(f"<div class=\"stat-val\">{counts['indexed_policies']}</div><div class=\"stat-label\">Indexed policies</div>", html)
        # Verify chunk count card shows true count
        self.assertIn(f"<div class=\"stat-val\">{counts['total_chunks']}</div><div class=\"stat-label\">Total chunks</div>", html)
        # Verify recent jobs table includes the newly compiled policies
        self.assertIn("Automated Lifecycle Test Policy Alpha", html)
        print(f"[TEST 6] RAG Dashboard rendered accurately with {counts['indexed_policies']} indexed policies and {counts['total_chunks']} chunks.")


if __name__ == "__main__":
    unittest.main()
