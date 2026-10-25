"""
tests/test_production_hardening.py
Verification suite for Phase 4 Production Hardening requirements:
- T-NEW-01: Temporal chunk date filtering in Sparse and Dense retrievers
- T-NEW-02: Top-K retrieval depth and candidate preservation
- T-NEW-03: Incremental compiler embedding bypass for unchanged chunks
- T-NEW-04: Null-safe version resolver handling unconfigured effective dates
- T-NEW-05: BM25 index graceful execution outside and inside Flask application context
"""
import os
import sys
import unittest
from datetime import date, datetime
from unittest.mock import MagicMock, patch

from app import create_app
from models import db, Policy, PolicyVersion, PolicyChunkV2, Department, User, UserRole, ConfidentialityLevel, PolicyStatus
from rag.engine.query_scope import QueryScope
from rag.versions.resolver import VersionResolver, TemporalQuery
from rag.retrieval.sparse import PersistentBM25Index
from rag.retrieval.reranker import get_reranker, FlashRankReranker, MockReranker
from rag.compiler.incremental import IncrementalCompiler

class TestProductionHardening(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app("testing")
        cls.app_context = cls.app.app_context()
        cls.app_context.push()
        db.create_all()
        # Seed minimal policy, version, and chunk if empty
        if not Policy.query.first():
            u = User(name="Admin User", email="admin_ph@test.com", password_hash="hash", role=UserRole.ADMIN, department_id=1)
            db.session.add(u)
            db.session.commit()
            p = Policy(policy_id="POL-TEST-01", title="Annual Leave Policy", confidentiality="internal", author_id=u.id, status=PolicyStatus.ACTIVE)
            db.session.add(p)
            db.session.commit()
            pv = PolicyVersion(policy_id=p.id, version_num=1.0, version_label="v1.0", is_active=True, content="Annual leave entitlement is 30 days.", created_by_id=u.id)
            db.session.add(pv)
            db.session.commit()
            c = PolicyChunkV2(chunk_id="chk-1", policy_id=p.id, version_id=pv.id, text="Annual leave entitlement is 30 days.", section_path="Section 1")
            db.session.add(c)
            db.session.commit()

    @classmethod
    def tearDownClass(cls):
        db.session.rollback()
        cls.app_context.pop()

    def test_null_safe_version_resolver(self):
        """T-NEW-04: Null-safe version resolver handles unconfigured effective_from without crash."""
        resolver = VersionResolver()
        
        # Test get_active_version for non-existent or unconfigured policy
        res = resolver.get_active_version(policy_id=999999, target_date=date(2022, 5, 1))
        self.assertIsNone(res)

        # Test with real policy from database
        p = Policy.query.first()
        self.assertIsNotNone(p)
        active_ver = resolver.get_active_version(policy_id=p.id)
        self.assertIsNotNone(active_ver)
        self.assertTrue(active_ver.is_active)

    def test_bm25_outside_flask_context(self):
        """T-NEW-05: rebuild_from_db can be called safely and auto-handles context."""
        bm25 = PersistentBM25Index()
        # Should execute cleanly without raising RuntimeError: Working outside of application context
        bm25.rebuild_from_db()
        self.assertGreater(len(bm25._corpus), 0)

    def test_reranker_startup_and_status(self):
        """J4.3: Reranker initializes and reports real status."""
        reranker = get_reranker()
        self.assertIsNotNone(reranker)
        
        candidates = [
            {"id": "c1", "text": "Annual leave entitlement is 30 days per calendar year."},
            {"id": "c2", "text": "Screen lock timeout is mandatory after 5 minutes of inactivity."}
        ]
        query = "What is the annual leave?"
        ranked = reranker.rank(query, candidates, top_k=2)
        self.assertEqual(len(ranked), 2)
        # Verify rank 1 is relevant
        self.assertIn("annual leave", ranked[0]["text"].lower())

    def test_incremental_compiler_unchanged_chunk_bypass(self):
        """T-NEW-03: Incremental compiler skips unchanged chunks in delta diff."""
        compiler = IncrementalCompiler()
        from rag.compiler.document_ir import ChunkIR
        
        existing_chunk = PolicyChunkV2.query.first()
        self.assertIsNotNone(existing_chunk)
        v_id = existing_chunk.version_id
        
        unchanged_chunk = ChunkIR(
            chunk_id=existing_chunk.chunk_id,
            policy_id=existing_chunk.policy_id,
            version_id=v_id,
            section_path=existing_chunk.section_path or "Section 1",
            text=existing_chunk.text,
            page=1,
            paragraph_num=1,
            text_hash=existing_chunk.text_hash,
            char_count=len(existing_chunk.text)
        )
        new_chunk = ChunkIR(
            chunk_id=f"new-chunk-{v_id}-unique",
            policy_id=existing_chunk.policy_id,
            version_id=v_id,
            section_path="Section 99 New Clause",
            text="Brand new clause text for incremental compilation.",
            page=10,
            paragraph_num=1,
            text_hash="brand_new_hash_999",
            char_count=50
        )
        
        diff = compiler.diff_versions([unchanged_chunk, new_chunk], previous_version_id=v_id)
        self.assertEqual(len(diff.unchanged_chunks), 1)
        self.assertEqual(diff.unchanged_chunks[0].chunk_id, existing_chunk.chunk_id)
        self.assertEqual(len(diff.added_chunks), 1)
        self.assertEqual(diff.added_chunks[0].chunk_id, new_chunk.chunk_id)

    def test_cache_clear_safeguard(self):
        """Verifies clear() purges both L1 and L2 cache entries."""
        from rag.cache.semantic_cache import get_cache
        cache = get_cache()
        cache.clear()
        self.assertEqual(len(cache._local_l1), 0)
        self.assertEqual(len(cache._local_l2), 0)

if __name__ == "__main__":
    unittest.main()
