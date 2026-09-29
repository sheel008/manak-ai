"""Unit tests for Ask MANAK-AI Intent Router."""
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

from app.services.intent_router import classify_intent, build_conversational_response, Intent, DEFAULT_FOLLOW_UPS


def test_intent_routing():
    test_cases = [
        # Greeting tests
        ("hi", Intent.GREETING),
        ("hello", Intent.GREETING),
        ("hey", Intent.GREETING),
        ("good morning", Intent.GREETING),
        ("good evening", Intent.GREETING),
        ("good afternoon", Intent.GREETING),
        ("नमस्ते", Intent.GREETING),
        ("வணக்கம்", Intent.GREETING),

        # Procurement recommendation tests
        ("What standard applies to LED street lights?", Intent.PROCUREMENT_RECOMMENDATION),
        ("What BIS standard applies to LED street lights?", Intent.PROCUREMENT_RECOMMENDATION),
        ("Which BIS standard applies to cement?", Intent.PROCUREMENT_RECOMMENDATION),
        ("Which standard applies to cement?", Intent.PROCUREMENT_RECOMMENDATION),
        ("What standard should I use for transformers?", Intent.PROCUREMENT_RECOMMENDATION),
        ("PVC Pipe for drinking water", Intent.PROCUREMENT_RECOMMENDATION),
        ("TMT Steel Bar", Intent.PROCUREMENT_RECOMMENDATION),

        # Standard tests
        ("What is IS 16503:2017?", Intent.BIS_STANDARD_QUERY),
        ("Tell me about IS 16503:2017", Intent.BIS_STANDARD_QUERY),
        ("Explain IS 456", Intent.BIS_STANDARD_QUERY),

        # QCO tests
        ("Is BIS certification mandatory for IS 16503:2017?", Intent.QCO_QUERY),
        ("Does this product require QCO compliance?", Intent.QCO_QUERY),
        ("Is ISI mandatory for helmets?", Intent.QCO_QUERY),
        ("Find QCO for Pressure Cooker", Intent.QCO_QUERY),

        # Technical specification tests
        ("What are the technical specifications of IS 16503:2017?", Intent.TECHNICAL_SPECIFICATION_QUERY),
        ("What are the technical requirements of IS 16503:2017?", Intent.TECHNICAL_SPECIFICATION_QUERY),

        # Mixed test (must NOT be greeting)
        ("Hi, which BIS standard applies to transformers?", Intent.PROCUREMENT_RECOMMENDATION),
        ("Hello, what is IS 16503:2017?", Intent.BIS_STANDARD_QUERY),
        ("Hey, is certification mandatory for helmets?", Intent.QCO_QUERY),

        # Out-of-domain tests
        ("write a python program for factorial", Intent.UNKNOWN),
        ("write a python program", Intent.UNKNOWN),
        ("who is the president of france", Intent.UNKNOWN),
        ("recipe for chocolate cake", Intent.UNKNOWN),

        # General conversation tests
        ("who are you?", Intent.GENERAL_CONVERSATION),
        ("what can you do?", Intent.GENERAL_CONVERSATION),
        ("thank you", Intent.GENERAL_CONVERSATION),
        ("bye", Intent.GENERAL_CONVERSATION),
    ]

    for q, expected in test_cases:
        intent, meta = classify_intent(q)
        assert intent == expected, f"Query '{q}' classified as {intent}, expected {expected}"
        print(f"PASSED: '{q}' -> {intent}")

    # Test greeting responses
    hi_resp = build_conversational_response(Intent.GREETING, {"greeting_type": "hi"}, "hi", "en")
    assert "👋 Hello! I'm MANAK-AI" in hi_resp
    assert "Finding applicable BIS Standards" in hi_resp
    assert "What would you like to check?" in hi_resp

    # Test out of domain response
    ood_resp = build_conversational_response(Intent.UNKNOWN, {}, "write a python program", "en")
    assert "specialized in Bureau of Indian Standards" in ood_resp

    print("ALL INTENT CLASSIFICATION TESTS PASSED SUCCESSFULLY!")


def test_handle_chat_routing():
    # Mock vector_search and database so test runs without database driver
    import types
    from unittest.mock import patch

    # Mock psycopg2 if not present
    if "psycopg2" not in sys.modules:
        mock_pg = types.ModuleType("psycopg2")
        mock_pg.extras = types.ModuleType("psycopg2.extras")
        mock_pg.extras.RealDictCursor = object
        mock_pg.extras.Json = object
        mock_pg.pool = types.ModuleType("psycopg2.pool")
        sys.modules["psycopg2"] = mock_pg
        sys.modules["psycopg2.extras"] = mock_pg.extras
        sys.modules["psycopg2.pool"] = mock_pg.pool

    # Mock sentence_transformers / embedding if not present
    if "app.services.embedding" not in sys.modules:
        mock_emb = types.ModuleType("app.services.embedding")
        mock_emb.embed_query = lambda t: [0.1] * 384
        mock_emb.embed_texts = lambda xs: [[0.1] * 384 for _ in xs]
        sys.modules["app.services.embedding"] = mock_emb

    def _should_not_be_called(*args, **kwargs):
        raise AssertionError("Vector search was called when it should have been skipped!")

    mock_vector = types.ModuleType("app.retrieval.vector_search")
    mock_vector.vector_search = _should_not_be_called
    sys.modules["app.retrieval.vector_search"] = mock_vector

    from app.services.chat_service import handle_chat

    # 1. GREETING TEST: "hi" must NOT trigger vector search
    res_hi = handle_chat("hi")
    assert res_hi["intent"] == "GREETING"
    assert len(res_hi["recommendations"]) == 0
    assert res_hi["qco"] is None
    assert "👋 Hello! I'm MANAK-AI" in res_hi["answer"]
    assert len(res_hi["follow_up"]) == 3
    print("PASSED: handle_chat('hi') returned greeting without vector search!")

    # 2. GREETING TEST: "hello"
    res_hello = handle_chat("hello")
    assert res_hello["intent"] == "GREETING"
    assert len(res_hello["recommendations"]) == 0
    assert res_hello["qco"] is None
    print("PASSED: handle_chat('hello') returned greeting without vector search!")

    # 3. GREETING TEST: "hey"
    res_hey = handle_chat("hey")
    assert res_hey["intent"] == "GREETING"
    assert len(res_hey["recommendations"]) == 0
    print("PASSED: handle_chat('hey') returned greeting without vector search!")

    # 4. GREETING TEST: "good morning"
    res_gm = handle_chat("good morning")
    assert res_gm["intent"] == "GREETING"
    assert len(res_gm["recommendations"]) == 0
    print("PASSED: handle_chat('good morning') returned greeting without vector search!")

    # 5. GREETING TEST: "good evening"
    res_ge = handle_chat("good evening")
    assert res_ge["intent"] == "GREETING"
    assert len(res_ge["recommendations"]) == 0
    print("PASSED: handle_chat('good evening') returned greeting without vector search!")

    # 6. OUT-OF-DOMAIN TEST: "write a python program for factorial"
    res_ood = handle_chat("write a python program for factorial")
    assert res_ood["intent"] == "UNKNOWN"
    assert len(res_ood["recommendations"]) == 0
    assert "specialized in Bureau of Indian Standards" in res_ood["answer"]
    print("PASSED: handle_chat('write a python program for factorial') returned out-of-domain message without vector search!")

    # 7. GENERAL CONVERSATION TEST: "who are you?"
    res_who = handle_chat("who are you?")
    assert res_who["intent"] == "GENERAL_CONVERSATION"
    assert len(res_who["recommendations"]) == 0
    print("PASSED: handle_chat('who are you?') returned general conversation without vector search!")

    # 8. MULTILINGUAL GREETING: "नमस्ते"
    res_hi_lang = handle_chat("नमस्ते", lang="hi")
    assert res_hi_lang["intent"] == "GREETING"
    assert len(res_hi_lang["recommendations"]) == 0
    assert "नमस्ते! मैं मानक-एआई" in res_hi_lang["answer"]
    print("PASSED: handle_chat('नमस्ते', lang='hi') returned Hindi greeting without vector search!")

    # 9. DOMAIN QUERY ROUTING TEST:
    # "Hi, which BIS standard applies to transformers?" MUST route to procurement and call vector search!
    called_vector = False
    def _mock_success_vector(query, top_k=10):
        nonlocal called_vector
        called_vector = True
        return [{
            "is_number": "IS 2026",
            "title": "Power Transformers",
            "category": "Electrotechnical",
            "similarity": 0.92,
            "scope": "Specifications for power transformers",
            "source_excerpt": "Scope and testing for power transformers",
        }]

    mock_vector.vector_search = _mock_success_vector
    res_mixed = handle_chat("Hi, which BIS standard applies to transformers?")
    assert called_vector is True, "Vector search was NOT called for mixed procurement query!"
    assert res_mixed["intent"] == "PROCUREMENT_RECOMMENDATION"
    assert len(res_mixed["recommendations"]) > 0
    assert "Section 1 — Recommendation" in res_mixed["answer"]
    print("PASSED: handle_chat('Hi, which BIS standard applies to transformers?') reached vector search and returned full recommendation!")

    print("ALL HANDLE_CHAT ROUTING TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    test_intent_routing()
    test_handle_chat_routing()

