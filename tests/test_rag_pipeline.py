"""
tests/test_rag_pipeline.py
Integration test for full RAG pipeline with stubbed ChromaDB and stub LLMProvider.
Asserts role/department filtering and citation assembly.
"""
import unittest
from unittest.mock import patch, MagicMock
from rag.chatbot.chat_service import answer
from rag.llm_provider import LLMResponse, LLMProvider


class StubLLMProvider(LLMProvider):
    def generate(self, prompt, *, system=None, max_tokens=1024, temperature=0.2, stream=False, **kwargs):
        return LLMResponse(
            text="According to the Engineering Remote Work policy, engineers can work 3 days remotely.",
            model="stub-model",
            fallback=False
        )

    def embed(self, texts):
        return [[0.1] * 384 for _ in texts]

    def health_check(self):
        return True


class TestRAGPipelineIntegration(unittest.TestCase):

    @patch("rag.chatbot.chat_service.get_llm_provider")
    @patch("rag.chatbot.chat_service.get_embedder")
    @patch("rag.chatbot.chat_service.get_store")
    @patch("rag.chatbot.chat_service.get_reranker")
    @patch("rag.chatbot.chat_service.get_history")
    @patch("rag.chatbot.chat_service.add_message")
    @patch("rag.chatbot.chat_service.get_cache")
    def test_rag_pipeline_department_filtering_and_citation(
        self,
        mock_get_cache,
        mock_add_msg,
        mock_get_hist,
        mock_reranker,
        mock_store,
        mock_embedder,
        mock_get_provider
    ):
        print("Starting test...")
        # Setup mocks
        mock_get_cache.return_value.get.return_value = None
        mock_get_cache.return_value.use_redis = False
        mock_get_provider.return_value = StubLLMProvider()

        mock_embedder_inst = MagicMock()
        mock_embedder_inst.embed_query.return_value = [0.1] * 384
        mock_embedder.return_value = mock_embedder_inst

        mock_store_inst = MagicMock()
        mock_store_inst.search.return_value = [
            {
                "id": "chunk-1",
                "text": "Engineering staff may request up to 3 remote days per week with manager approval.",
                "policy_id": 10,
                "policy_name": "Engineering Remote Work Policy",
                "version": "1.0",
                "section": "3.1 Remote Days",
                "page": 2,
                "department": "Engineering",
                "score": 0.85
            }
        ]
        mock_store.return_value = mock_store_inst

        mock_rerank_inst = MagicMock()
        mock_rerank_inst.rerank.side_effect = lambda query, hits, top_k: hits[:top_k]
        mock_reranker.return_value = mock_rerank_inst

        mock_get_hist.return_value = []

        # Execute RAG answer query with employee role in Engineering department
        res = answer(
            query="How many remote days are allowed for engineers?",
            session_id="test-session-123",
            user_role="employee",
            user_department="Engineering"
        )

        # Assert search was called with proper department restriction: ["Engineering", ""]
        print("RESULT:", res)
        mock_store_inst.search.assert_called_once()
        _, kwargs = mock_store_inst.search.call_args
        self.assertEqual(kwargs.get("allowed_departments"), ["Engineering", "", "Human Resources", "IT", "Legal"])

        # Assert response structure
        self.assertFalse(res["fallback"])
        self.assertEqual(res["chunks_used"], 1)
        self.assertEqual(res["model"], "stub-model")
        self.assertIn("3 days remotely", res["answer"])
        self.assertEqual(len(res["citations"]), 1)
        self.assertEqual(res["citations"][0]["policy_name"], "Engineering Remote Work Policy")


if __name__ == "__main__":
    unittest.main()
