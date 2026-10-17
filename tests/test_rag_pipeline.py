"""
tests/test_rag_pipeline.py
Integration test for full RAG pipeline compatibility facade.
Asserts role/department proxy conversion, QueryEngine delegation, and response assembly.
"""
import unittest
from unittest.mock import patch, MagicMock
from rag.chatbot.chat_service import answer
from rag.engine.query_engine import QueryResult

class TestRAGPipelineIntegration(unittest.TestCase):

    @patch("rag.chatbot.chat_service.get_query_engine")
    def test_rag_pipeline_department_filtering_and_citation(
        self,
        mock_get_engine
    ):
        mock_engine = MagicMock()
        mock_engine.answer.return_value = QueryResult(
            answer="According to the Engineering Remote Work Policy (v1.0, 3.1 Remote Days):\nEngineering staff may request up to 3 remote days per week with manager approval.",
            citations=[{
                "chunk_id": "chunk-1",
                "policy_id": 10,
                "policy_name": "Engineering Remote Work Policy",
                "version": "1.0",
                "section": "3.1 Remote Days",
                "page": 2
            }],
            policy_versions=["1.0"],
            latency_ms=12.5,
            llm_used=False,
            retrieval_count=1,
            reranker_used=False,
            abstained=False,
            model="stub-model",
            confidence=1.0,
            route="HYBRID_RAG"
        )
        mock_get_engine.return_value = mock_engine

        # Execute RAG answer query with employee role in Engineering department
        res = answer(
            query="How many remote days are allowed for engineers?",
            session_id="test-session-123",
            user_role="employee",
            user_department="Engineering"
        )

        mock_engine.answer.assert_called_once()
        call_args, call_kwargs = mock_engine.answer.call_args
        self.assertEqual(call_args[0], "How many remote days are allowed for engineers?")
        user_proxy = call_kwargs.get("user")
        self.assertIsNotNone(user_proxy)
        self.assertEqual(user_proxy.role, "employee")
        self.assertEqual(user_proxy.department.name, "Engineering")

        # Assert response structure
        self.assertFalse(res["fallback"])
        self.assertEqual(res["chunks_used"], 1)
        self.assertEqual(res["model"], "stub-model")
        self.assertIn("3 remote days", res["answer"])
        self.assertEqual(len(res["citations"]), 1)
        self.assertEqual(res["citations"][0]["policy_name"], "Engineering Remote Work Policy")
        self.assertEqual(res["confidence"], 100)


if __name__ == "__main__":
    unittest.main()
