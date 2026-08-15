"""
tests/test_llm_provider.py
Unit tests for LLMProvider implementations using a mocked HTTP layer (urllib / openai).
"""
import unittest
from unittest.mock import patch, MagicMock
from rag.llm_provider import (
    OllamaProvider,
    VLLMProvider,
    ExtractiveProvider,
    get_llm_provider,
    LLMResponse,
)


class TestOllamaProvider(unittest.TestCase):
    def setUp(self):
        self.provider = OllamaProvider(base_url="http://localhost:11434", model="llama3.1:8b")

    @patch("requests.Session.post")
    def test_ollama_generate_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {"content": "According to the remote work policy, employees may work 2 days remotely."},
            "prompt_eval_count": 120,
            "eval_count": 25
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        prompt = [{"role": "user", "content": "What is the remote work policy?"}]
        res = self.provider.generate(prompt)

        self.assertIsInstance(res, LLMResponse)
        self.assertIn("remote work policy", res.text)
        self.assertFalse(res.fallback)
        self.assertEqual(res.usage["prompt_tokens"], 120)

    @patch("requests.Session.post")
    def test_ollama_generate_failure_triggers_fallback(self, mock_post):
        mock_post.side_effect = Exception("Connection refused")
        prompt = "POLICY EXCERPTS:\n\n[Excerpt 1]\nPolicy: HR | Page: 1\nEmployees get 20 leave days.\n\nQUESTION: How many leave days?"
        res = self.provider.generate(prompt)

        self.assertIsInstance(res, LLMResponse)
        self.assertTrue(res.fallback)
        self.assertIn("Ollama error", res.error)

    @patch("urllib.request.urlopen")
    def test_ollama_health_check(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        self.assertTrue(self.provider.health_check())


class TestVLLMProvider(unittest.TestCase):
    def setUp(self):
        self.provider = VLLMProvider(base_url="http://localhost:8000/v1", model="llama3-8b")

    @patch("requests.Session.post")
    def test_vllm_generate_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "The travel policy covers up to $100 for meals."}}],
            "usage": {"prompt_tokens": 80, "completion_tokens": 15}
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        res = self.provider.generate("What is the meal allowance?")
        self.assertEqual(res.text, "The travel policy covers up to $100 for meals.")
        self.assertFalse(res.fallback)

    @patch("urllib.request.urlopen")
    def test_vllm_health_check(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response
        self.assertTrue(self.provider.health_check())


class TestExtractiveProvider(unittest.TestCase):
    def setUp(self):
        self.provider = ExtractiveProvider()

    def test_extractive_fallback_extracts_best_sentence(self):
        prompt = (
            "POLICY EXCERPTS:\n\n"
            "[Excerpt 1]\n"
            "Policy: Health & Safety | Version: 1.0 | Section: 2.1 | Page: 4\n"
            "Employees must wear safety goggles in designated laboratory zones.\n\n"
            "QUESTION: Where must safety goggles be worn?"
        )
        res = self.provider.generate(prompt)
        self.assertTrue(res.fallback)
        self.assertIn("laboratory zones", res.text)

    def test_extractive_fallback_refusal(self):
        prompt = (
            "POLICY EXCERPTS:\n\n"
            "[Excerpt 1]\n"
            "Policy: Dress Code | Version: 1.0 | Section: General | Page: 1\n"
            "Business casual attire is required Monday through Thursday.\n\n"
            "QUESTION: What is the policy on rocket propulsion systems?"
        )
        res = self.provider.generate(prompt)
        self.assertTrue(res.fallback)
        self.assertEqual(res.text, "I couldn't find this information in the available policies.")


class TestFactory(unittest.TestCase):
    @patch.dict("os.environ", {"LLM_BACKEND": "ollama"})
    def test_factory_returns_ollama(self):
        provider = get_llm_provider(force_reload=True)
        self.assertIsInstance(provider, OllamaProvider)

    @patch.dict("os.environ", {"LLM_BACKEND": "vllm"})
    def test_factory_returns_vllm(self):
        provider = get_llm_provider(force_reload=True)
        self.assertIsInstance(provider, VLLMProvider)


if __name__ == "__main__":
    unittest.main()
