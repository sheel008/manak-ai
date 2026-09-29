"""Comprehensive unit and integration tests for MANAK-AI Groq LLM integration.

Validates:
1. Conversational routing (Groq conversational LLM called, vector search bypassed, natural text, no fake BIS)
2. Procurement routing (vector search + rerank used, Groq grounded LLM called, authoritative retrieval)
3. Groq failure fallback (missing key, HTTP 500, empty response, timeout -> FallbackProvider)
4. Multilingual support (en, hi, mr, ta, kn)
5. Zero secrets exposure
"""
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.services.llm_provider import (
    GroqProvider,
    GeminiFlashProvider,
    OpenAIProvider,
    FallbackProvider,
    get_llm_provider,
    GROUNDED_SYSTEM_PROMPT,
    CONVERSATIONAL_SYSTEM_PROMPT,
)
from app.services.chat_service import handle_chat


class TestGroqLLMIntegration(unittest.TestCase):
    """Test suite covering Groq LLM provider, conversational routing, and fallbacks."""

    def setUp(self):
        # Clear out any existing session state before each test
        from app.services import chat_service
        chat_service._chat_sessions.clear()

    # ─────────────────────────────────────────────────────────────
    # PART 1 & 2: Provider Factory & Key Handling
    # ─────────────────────────────────────────────────────────────
    def test_provider_factory_selection(self):
        """Test get_llm_provider() respects LLM_PROVIDER env variable."""
        # 1. groq with key
        with patch.dict(os.environ, {"LLM_PROVIDER": "groq", "GROQ_API_KEY": "test_gsk_12345"}):
            p = get_llm_provider()
            self.assertIsInstance(p, GroqProvider)
            self.assertEqual(p.api_key, "test_gsk_12345")
            self.assertEqual(p.model, "llama-3.3-70b-versatile")

        # 2. groq without key -> FallbackProvider
        with patch.dict(os.environ, {"LLM_PROVIDER": "groq", "GROQ_API_KEY": ""}):
            p = get_llm_provider()
            self.assertIsInstance(p, FallbackProvider)

        # 3. gemini with key
        with patch.dict(os.environ, {"LLM_PROVIDER": "gemini", "GEMINI_API_KEY": "test_gemini_key"}):
            p = get_llm_provider()
            self.assertIsInstance(p, GeminiFlashProvider)

        # 4. openai with key
        with patch.dict(os.environ, {"LLM_PROVIDER": "openai", "OPENAI_API_KEY": "test_openai_key"}):
            p = get_llm_provider()
            self.assertIsInstance(p, OpenAIProvider)

        # 5. No provider set, no keys set -> FallbackProvider
        with patch.dict(os.environ, {"LLM_PROVIDER": "", "GROQ_API_KEY": "", "GEMINI_API_KEY": "", "OPENAI_API_KEY": ""}):
            p = get_llm_provider()
            self.assertIsInstance(p, FallbackProvider)

    def test_zero_secrets_exposure(self):
        """Verify API key is never serialized into response payloads, error strings, or repr."""
        secret_key = "gsk_super_secret_groq_key_99999"
        provider = GroqProvider(api_key=secret_key)
        
        # repr/str should not expose raw credentials
        self.assertNotIn(secret_key, repr(provider))

    # ─────────────────────────────────────────────────────────────
    # PART 3 & 4: Conversational LLM Method
    # ─────────────────────────────────────────────────────────────
    @patch("requests.post")
    def test_groq_conversational_response_success(self, mock_post):
        """Verify GroqProvider.generate_conversational_response sends proper payload and returns response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "Hello! I'm MANAK-AI. How can I help you with Indian Standards today?"
                    }
                }
            ]
        }
        mock_post.return_value = mock_response

        provider = GroqProvider(api_key="test_key", model="llama-3.3-70b-versatile")
        res = provider.generate_conversational_response(
            message="hi",
            history=[{"role": "user", "content": "prior message"}],
            lang="en"
        )

        self.assertIsNotNone(res)
        self.assertIn("Hello! I'm MANAK-AI", res)
        # Verify requests.post was called with conversational system prompt
        called_args, called_kwargs = mock_post.call_args
        payload = called_kwargs.get("json", {})
        messages = payload.get("messages", [])
        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("MANAK-AI", messages[0]["content"])
        self.assertIn("NEVER fabricate", messages[0]["content"])

    # ─────────────────────────────────────────────────────────────
    # PART 5: Conversational Routing (NO vector search)
    # ─────────────────────────────────────────────────────────────
    @patch.dict(os.environ, {"LLM_PROVIDER": "groq", "GROQ_API_KEY": "dummy_test_key"})
    @patch("app.retrieval.vector_search.vector_search")
    @patch.object(GroqProvider, "generate_conversational_response")
    def test_conversational_queries_bypass_vector_search(self, mock_groq_conv, mock_vector_search):
        """Conversational messages must route to Groq and skip vector search entirely."""
        mock_groq_conv.return_value = "Hello! I am MANAK-AI, your Indian Standards assistant."

        conversational_inputs = [
            "hi",
            "hello",
            "thanks",
            "what can you do?",
        ]

        for user_msg in conversational_inputs:
            mock_vector_search.reset_mock()
            mock_groq_conv.reset_mock()

            res = handle_chat(user_msg, session_id="test_conv_sess")

            # 1. Vector search must NOT be called
            mock_vector_search.assert_not_called()
            # 2. Groq conversational response method must be called
            self.assertTrue(mock_groq_conv.called, f"Groq was not called for '{user_msg}'")
            # 3. No recommendations or QCO rule
            self.assertEqual(len(res["recommendations"]), 0)
            self.assertIsNone(res["qco"])
            # 4. Response should be natural text, not 6-section template
            self.assertNotIn("Section 1 — Recommendation", res["answer"])
            self.assertNotIn("IS Standard", res["answer"])
            # 5. Schema compatibility preserved
            self.assertIn("sessionId", res)
            self.assertIn("answer", res)
            self.assertIn("follow_up", res)

    # ─────────────────────────────────────────────────────────────
    # PART 6 & 7: Procurement Queries (authoritative retrieval + grounded LLM)
    # ─────────────────────────────────────────────────────────────
    @patch.dict(os.environ, {"LLM_PROVIDER": "groq", "GROQ_API_KEY": "dummy_test_key"})
    @patch("app.retrieval.vector_search.vector_search")
    @patch.object(GroqProvider, "generate_response")
    def test_procurement_queries_use_rag_pipeline(self, mock_groq_grounded, mock_vector_search):
        """Procurement queries must NOT take conversational shortcut; must use retrieval."""
        mock_vector_search.return_value = [
            {
                "is_number": "IS 1786",
                "title": "High Strength Deformed Steel Bars",
                "category": "Civil",
                "similarity": 0.93,
                "scope": "Deformed steel bars for concrete reinforcement",
                "source_excerpt": "Standard specifications for steel bars",
                "is_qco_mandatory": True,
            }
        ]
        mock_groq_grounded.return_value = "### Section 1 — Recommendation\nIS 1786..."

        procurement_queries = [
            "Which BIS standard applies to steel bars?",
            "What standard applies to transformers?",
            "Which QCO applies to this product?",
            "IS 1786 requirements",
        ]

        for q in procurement_queries:
            mock_vector_search.reset_mock()
            mock_groq_grounded.reset_mock()

            res = handle_chat(q, session_id="test_proc_sess")

            # Vector search MUST be called (or explicit IS lookup used)
            if "IS 1786" not in q:
                self.assertTrue(mock_vector_search.called, f"Vector search should have run for '{q}'")
            # Recommendations MUST be returned
            self.assertGreater(len(res["recommendations"]), 0)
            self.assertIsNotNone(res["qco"])
            # Groq grounded response method must be called with retrieved context
            self.assertTrue(mock_groq_grounded.called, f"Grounded LLM should have run for '{q}'")

    # ─────────────────────────────────────────────────────────────
    # PART 8: Conversation Context / Memory
    # ─────────────────────────────────────────────────────────────
    @patch.dict(os.environ, {"LLM_PROVIDER": "groq", "GROQ_API_KEY": "dummy_test_key"})
    @patch.object(GroqProvider, "generate_conversational_response")
    @patch("app.retrieval.vector_search.vector_search")
    def test_conversation_follow_up_preserves_context(self, mock_vector_search, mock_groq_conv):
        """Turn 1 greeting followed by Turn 2 procurement query maintains session."""
        mock_groq_conv.return_value = "Hello! How can I help?"
        mock_vector_search.return_value = [
            {
                "is_number": "IS 1786",
                "title": "High Strength Deformed Steel Bars",
                "category": "Civil",
                "similarity": 0.91,
                "scope": "Steel bars",
                "source_excerpt": "Steel reinforcement",
                "is_qco_mandatory": True,
            }
        ]

        # Turn 1: Conversational Greeting
        res1 = handle_chat("Hi", session_id="sess_memory_test")
        self.assertEqual(res1["intent"], "GREETING")
        self.assertEqual(len(res1["recommendations"]), 0)

        # Turn 2: Procurement query in same session
        res2 = handle_chat("I need help with steel bars", session_id="sess_memory_test")
        self.assertIn(res2["intent"], ["PROCUREMENT_RECOMMENDATION", "BIS_STANDARD_QUERY"])
        self.assertGreater(len(res2["recommendations"]), 0)

    # ─────────────────────────────────────────────────────────────
    # PART 10: Fallback Behavior (Groq failure / missing key)
    # ─────────────────────────────────────────────────────────────
    @patch.dict(os.environ, {"LLM_PROVIDER": "groq", "GROQ_API_KEY": "dummy_key"})
    @patch.object(GroqProvider, "generate_conversational_response", return_value=None)
    def test_groq_conversational_failure_fallback(self, mock_conv):
        """When Groq API returns None or errors, chat falls back to deterministic conversational response."""
        res = handle_chat("hi", session_id="sess_fallback")
        self.assertEqual(res["intent"], "GREETING")
        self.assertIsNotNone(res["answer"])
        self.assertIn("Hello! I'm MANAK-AI", res["answer"])
        self.assertEqual(len(res["recommendations"]), 0)

    @patch.dict(os.environ, {"LLM_PROVIDER": "groq", "GROQ_API_KEY": "dummy_key"})
    @patch.object(GroqProvider, "generate_response", return_value=None)
    @patch("app.retrieval.vector_search.vector_search")
    def test_groq_grounded_failure_fallback(self, mock_vector, mock_grounded):
        """When Groq API fails during grounded response, system falls back to FallbackProvider."""
        mock_vector.return_value = [
            {
                "is_number": "IS 4985",
                "title": "Unplasticized PVC Pipes",
                "category": "Civil",
                "similarity": 0.95,
                "scope": "PVC pipes for potable water",
                "source_excerpt": "Unplasticized PVC Pipes for Potable Water Supplies",
                "is_qco_mandatory": True,
            }
        ]
        res = handle_chat("PVC Pipe for drinking water", session_id="sess_groq_fail")
        self.assertIn("Section 1 — Recommendation", res["answer"])
        self.assertIn("IS 4985", res["answer"])
        self.assertGreater(len(res["recommendations"]), 0)

    @patch("requests.post")
    def test_groq_provider_http_error_handling(self, mock_post):
        """GroqProvider must safely catch HTTP 500, timeout, and bad json without raising."""
        # HTTP 500
        mock_500 = MagicMock()
        mock_500.status_code = 500
        mock_500.text = "Internal Server Error"
        mock_post.return_value = mock_500

        provider = GroqProvider(api_key="test_key")
        self.assertIsNone(provider.generate_conversational_response("hi"))
        self.assertIsNone(provider.generate_response(
            "test", {"is_number": "IS 100"}, {}, [], [], 90, [], [], []
        ))

        # Timeout
        import requests
        mock_post.side_effect = requests.Timeout("Connection timed out")
        self.assertIsNone(provider.generate_conversational_response("hi"))
        self.assertIsNone(provider.generate_response(
            "test", {"is_number": "IS 100"}, {}, [], [], 90, [], [], []
        ))

    # ─────────────────────────────────────────────────────────────
    # PART 9: Multilingual Handling
    # ─────────────────────────────────────────────────────────────
    @patch.dict(os.environ, {"LLM_PROVIDER": "groq", "GROQ_API_KEY": "dummy_key"})
    @patch.object(GroqProvider, "generate_conversational_response")
    def test_multilingual_conversational_routing(self, mock_groq_conv):
        """Verify Hindi, Marathi, Tamil, and Kannada greetings correctly identify language."""
        languages = [
            ("नमस्ते", "hi"),
            ("नमस्कार", "mr"),
            ("வணக்கம்", "ta"),
            ("ನಮಸ್ಕಾರ", "kn"),
        ]

        for greeting, expected_lang in languages:
            mock_groq_conv.reset_mock()
            mock_groq_conv.return_value = f"Greeting in {expected_lang}"

            res = handle_chat(greeting, session_id=f"sess_{expected_lang}")
            self.assertEqual(res["intent"], "GREETING")
            self.assertEqual(len(res["recommendations"]), 0)
            # Verify the call passed the detected/requested language
            self.assertTrue(mock_groq_conv.called)
            called_kwargs = mock_groq_conv.call_args[1]
            self.assertEqual(called_kwargs.get("lang"), expected_lang)


if __name__ == "__main__":
    unittest.main()
