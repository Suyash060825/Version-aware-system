import unittest
from unittest.mock import patch, MagicMock
from whatif_ai import evaluate_scenario, _heuristic_verdict
from utils import extract_json

class StubLLMResponse:
    def __init__(self, text, fallback=False):
        self.text = text
        self.fallback = fallback

class StubLLMProvider:
    def __init__(self, response_text, fallback=False):
        self.response_text = response_text
        self.fallback = fallback

    def generate(self, prompt, *, use_secondary=False, **kwargs):
        return StubLLMResponse(self.response_text, fallback=self.fallback)

class TestWhatIfAI(unittest.TestCase):

    def test_extract_json(self):
        # Valid JSON block
        text = '```json\n{"verdict": "compliant", "confidence": 95}\n```'
        res = extract_json(text)
        self.assertEqual(res, {"verdict": "compliant", "confidence": 95})

        # Embedded JSON
        text2 = 'Here is the result: {"verdict": "not_compliant", "confidence": 100}'
        res2 = extract_json(text2)
        self.assertEqual(res2, {"verdict": "not_compliant", "confidence": 100})
        
        # Invalid JSON
        self.assertIsNone(extract_json("Just text no json"))

    @patch("whatif_ai.get_llm_provider")
    @patch("whatif_ai.get_embedder")
    @patch("whatif_ai.get_store")
    @patch("whatif_ai.get_reranker")
    def test_evaluate_scenario_normal(self, mock_reranker, mock_store, mock_embedder, mock_get_provider):
        # Setup mocks
        mock_get_provider.return_value = StubLLMProvider('{"verdict": "compliant", "confidence": 90, "explanation": "It is allowed.", "required_actions": ["None"], "applicable_sections": ["Section 1"]}')
        
        mock_embedder_inst = MagicMock()
        mock_embedder_inst.embed_query.return_value = [0.1] * 384
        mock_embedder.return_value = mock_embedder_inst

        mock_store_inst = MagicMock()
        mock_store_inst.search.return_value = [
            {"text": "Policy text", "policy_name": "Test Policy", "section": "1", "score": 0.85, "version": "1.0", "page": 1}
        ]
        mock_store.return_value = mock_store_inst

        mock_rerank_inst = MagicMock()
        mock_rerank_inst.rerank.side_effect = lambda query, hits, top_k: hits[:top_k]
        mock_reranker.return_value = mock_rerank_inst

        # Run evaluate_scenario
        res = evaluate_scenario("Can I buy a laptop?", user_role="employee", user_department="Engineering")
        
        # Assertions
        self.assertEqual(res["verdict"], "compliant")
        self.assertEqual(res["confidence"], 90)
        self.assertEqual(res["chunks_used"], 1)
        self.assertFalse(res["flagged_for_hr"])
        self.assertEqual(len(res["citations"]), 1)
        
        # Verify department filtering
        mock_store_inst.search.assert_called_once()
        _, kwargs = mock_store_inst.search.call_args
        self.assertEqual(kwargs.get("allowed_departments"), ["Engineering", ""])

    @patch("whatif_ai.get_llm_provider")
    @patch("whatif_ai.get_embedder")
    @patch("whatif_ai.get_store")
    @patch("whatif_ai.get_reranker")
    def test_evaluate_scenario_fallback_llm(self, mock_reranker, mock_store, mock_embedder, mock_get_provider):
        # Setup LLM fallback mock
        mock_get_provider.return_value = StubLLMProvider('Some unstructured text fallback', fallback=True)
        
        mock_embedder.return_value.embed_query.return_value = [0.1] * 384
        
        mock_store.return_value.search.return_value = [
            {"text": "Policy text", "policy_name": "Test Policy", "section": "1", "score": 0.85}
        ]
        
        mock_reranker.return_value.rerank.side_effect = lambda query, hits, top_k: hits[:top_k]

        res = evaluate_scenario("Can I buy a laptop?")
        
        self.assertEqual(res["verdict"], "depends")
        self.assertEqual(res["confidence"], 40)
        self.assertTrue(res["flagged_for_hr"])

    @patch("whatif_ai.get_llm_provider")
    @patch("whatif_ai.get_embedder")
    @patch("whatif_ai.get_store")
    @patch("whatif_ai.get_reranker")
    def test_evaluate_scenario_no_chunks(self, mock_reranker, mock_store, mock_embedder, mock_get_provider):
        # Empty search results
        mock_embedder.return_value.embed_query.return_value = [0.1] * 384
        mock_store.return_value.search.return_value = []
        
        res = evaluate_scenario("Can I fly to Mars?")
        
        self.assertEqual(res["verdict"], "unclear")
        self.assertEqual(res["confidence"], 0)
        self.assertEqual(res["chunks_used"], 0)
        # Should be flagged for HR due to 'unclear'
        self.assertTrue(res["flagged_for_hr"])

if __name__ == "__main__":
    unittest.main()
