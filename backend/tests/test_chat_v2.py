"""Tests for MANAK-AI v2.0 RAG Chat Pipeline."""
import json
import os
import sys
import types
from unittest.mock import patch

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND)
DATA_DIR = os.path.join(BACKEND, "data")

# Use real embedding service if available, only fallback to mock if sentence_transformers is missing
try:
    import sentence_transformers
    import app.services.embedding
except ImportError:
    _mock_embedding = types.ModuleType("app.services.embedding")
    _mock_embedding.embed_query = lambda t: [0.1] * 384
    _mock_embedding.embed_texts = lambda xs: [[0.1] * 384 for _ in xs]
    sys.modules["app.services.embedding"] = _mock_embedding


def _load_standards():
    with open(os.path.join(DATA_DIR, "standards.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def _load_rules():
    with open(os.path.join(DATA_DIR, "certification_rules.json"), "r", encoding="utf-8") as f:
        return json.load(f)


STANDARDS = _load_standards()
RULES = _load_rules()


def _mock_vector_search(query, top_k=10):
    q_lower = query.lower()
    scored = []
    for s in STANDARDS:
        text = (s.get("title", "") + " " + s.get("scope", "") + " " + " ".join(s.get("keywords", []))).lower()
        sim = 0.3
        # Match tokens
        hits = sum(1 for w in q_lower.split() if w in text)
        if hits > 0:
            sim = min(0.85, 0.4 + (hits * 0.15))
        scored.append({**s, "similarity": sim})
    scored.sort(key=lambda x: x["similarity"], reverse=True)
    return scored[:top_k]


def _mock_db_connection():
    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def execute(self, sql, params=None):
            self.rows = []
            if "FROM standards" in sql and params:
                clean = params[0].replace("%", "").lower()
                for s in STANDARDS:
                    if clean in s["is_number"].lower().replace(" ", ""):
                        self.rows = [{**s, "similarity": 1.0}]
                        break
            elif "FROM certification_rules" in sql:
                self.rows = RULES

        def fetchone(self):
            return self.rows[0] if getattr(self, "rows", None) else None

        def fetchall(self):
            return getattr(self, "rows", [])

    conn = types.SimpleNamespace()
    conn.autocommit = False
    conn.cursor = lambda: FakeCursor()
    conn.close = lambda: None
    return conn


@patch("app.core.database.get_connection", _mock_db_connection)
@patch("app.retrieval.vector_search.vector_search", _mock_vector_search)
def test_all_10_mandatory_queries():
    from app.services.chat_service import handle_chat

    test_queries = [
        ("PVC Pipe", ["IS 4985"]),
        ("LED Street Light IP65 100W", ["IS 10322"]),
        ("OPC Cement Grade 43", ["IS 269"]),
        ("Motorcycle Helmet", ["IS 16515", "IS 2925"]),
        ("Pressure Cooker", ["IS 2347"]),
        ("Fire Extinguisher", ["IS 2878", "IS 15683"]),
        ("TMT Steel Bar", ["IS 1786"]),
        ("Water Thinned Emulsion Paint", ["IS 12062"]),
        ("Copper Electrical Wire", ["IS 694", "IS 3851"]),
        ("Solar PV Module", ["IS 14286", "IS 694", "IS 15885"]),
    ]

    for query, expected_prefixes in test_queries:
        res = handle_chat(query)
        assert res["query"] == query
        assert len(res["recommendations"]) > 0, f"No recommendations for {query}"
        top_rec = res["recommendations"][0]
        assert any(p in top_rec["is_number"] for p in expected_prefixes), (
            f"Expected one of {expected_prefixes} in {top_rec['is_number']} for query: {query}"
        )

        assert 0 <= top_rec["confidence"] <= 100
        assert "is_number" in top_rec
        assert "title" in top_rec
        assert "category" in top_rec
        assert "summary" in top_rec

        # Structured sections
        assert "qco" in res
        assert "mandatory" in res["qco"]
        assert "rule" in res["qco"]

        assert "related_standards" in res
        assert isinstance(res["related_standards"], list)

        assert "evidence" in res
        assert len(res["evidence"]) > 0
        assert "standard" in res["evidence"][0]
        assert "excerpt" in res["evidence"][0]

        assert "follow_up" in res
        assert len(res["follow_up"]) == 3

        # Grounded response structure
        answer = res["answer"]
        assert "Section 1 — Recommendation" in answer or "Recommendation" in answer
        assert "Section 2 — Why This Matches" in answer or "Why This Matches" in answer
        assert "Section 3 — Certification Status" in answer or "Certification Status" in answer
        assert "Section 4 — Related Standards" in answer or "Related Standards" in answer
        assert "Section 5 — Evidence" in answer or "Evidence" in answer
        assert "Section 6 — Suggested Follow-up Questions" in answer or "Suggested Follow-up Questions" in answer

        # Backward compatibility
        assert res["message"] == answer
        assert "sessionId" in res
        assert len(res["citations"]) > 0


@patch("app.core.database.get_connection", _mock_db_connection)
@patch("app.retrieval.vector_search.vector_search", _mock_vector_search)
def test_conversation_follow_up():
    from app.services.chat_service import handle_chat

    # Turn 1: query for PVC Pipe
    res1 = handle_chat("PVC Pipe for drinking water", session_id="test_sess_1")
    assert "IS 4985" in res1["recommendations"][0]["is_number"]

    # Turn 2: follow-up "Is certification mandatory?"
    res2 = handle_chat("Is certification mandatory?", session_id="test_sess_1")
    assert "IS 4985" in res2["recommendations"][0]["is_number"]
    assert "qco" in res2
    assert "mandatory" in res2["qco"]


@patch("app.core.database.get_connection", _mock_db_connection)
@patch("app.retrieval.vector_search.vector_search", _mock_vector_search)
def test_multilingual_chat():
    from app.services.chat_service import handle_chat

    # Hindi
    res_hi = handle_chat("PVC Pipe for drinking water", lang="hi")
    assert "खंड 1 — अनुशंसा" in res_hi["answer"]
    assert "IS 4985" in res_hi["answer"]  # IS number preserved
    assert len(res_hi["follow_up"]) == 3
    assert "क्या वर्तमान QCO" in res_hi["follow_up"][0]

    # Tamil
    res_ta = handle_chat("PVC Pipe for drinking water", lang="ta")
    assert "பிரிவு 1 — பரிந்துரை" in res_ta["answer"]
    assert "IS 4985" in res_ta["answer"]  # IS number preserved
    assert "தற்போதைய QCO" in res_ta["follow_up"][0]
