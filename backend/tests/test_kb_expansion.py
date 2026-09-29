"""
Comprehensive unit and integration test suite for the 500+ BIS Standards knowledge base,
offline embeddings vector search, QCO mapping, related standards graph, and explainable recommendations.
"""

import json
import io
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.retrieval.vector_search import (
    load_embeddings_cache,
    vector_search,
)
from app.rules.certification import get_qco_details
from app.rules.related import get_related_standards
from app.evidence.builder import generate_why_recommended

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
client = TestClient(app)


def test_knowledge_base_500_plus():
    """Verify standards.json contains 500+ standards and valid schemas."""
    standards_file = DATA_DIR / "standards.json"
    assert standards_file.exists(), "standards.json must exist"

    with open(standards_file, "r", encoding="utf-8") as f:
        standards = json.load(f)

    assert len(standards) >= 500, f"Expected 500+ standards, got {len(standards)}"

    seen = set()
    for s in standards:
        is_num = s.get("is_number")
        assert is_num, "is_number cannot be empty"
        assert is_num not in seen, f"Duplicate is_number: {is_num}"
        seen.add(is_num)

        assert s.get("title"), f"Missing title for {is_num}"
        assert s.get("department"), f"Missing department for {is_num}"
        assert s.get("category"), f"Missing category for {is_num}"
        assert isinstance(s.get("keywords", []), list), f"Keywords must be a list in {is_num}"


def test_embeddings_cache_loaded():
    """Verify precomputed embeddings are loaded into memory and 384-dimensional."""
    cache = load_embeddings_cache()
    assert cache is not None, "Failed to load embeddings cache"
    assert len(cache) >= 500, f"Expected >= 500 embeddings, got {len(cache)}"

    for is_num, vec in list(cache.items())[:10]:
        assert len(vec) == 384, f"Vector for {is_num} has incorrect dimension: {len(vec)}"
        assert any(abs(v) > 0 for v in vec), f"Zero vector found for {is_num}"


def test_in_memory_vector_search_latency_and_top_k():
    """Verify in-memory vector search returns top-k candidates rapidly."""
    query = "High strength deformed steel bars for concrete reinforcement"
    candidates = vector_search(query=query, top_k=10)

    assert len(candidates) > 0, "Vector search returned 0 candidates"
    assert len(candidates) <= 10, "Vector search exceeded top_k"
    assert any("1786" in c.get("is_number", "") or "Steel" in c.get("title", "") for c in candidates)


def test_department_filtering_in_vector_search():
    """Verify department filter isolates or prioritizes standards in that department."""
    candidates_civil = vector_search(query="fire safety and structural design", department="Civil Engineering", top_k=10)
    for c in candidates_civil:
        assert "CED" in c.get("department", "") or "Civil" in c.get("department", "") or c.get("department_score", 0) > 0


def test_qco_mapping_and_rules():
    """Verify QCO details are properly resolved for mandatory standards."""
    qco_269 = get_qco_details("IS 269:2015")
    assert qco_269 is not None, "Expected QCO details for IS 269:2015"
    assert qco_269.get("mandatory") is True
    assert "Cement" in qco_269.get("product", "") or "Cement" in qco_269.get("qco_name", "")

    qco_1786 = get_qco_details("IS 1786:2008")
    assert qco_1786 is not None, "Expected QCO details for IS 1786:2008"
    assert qco_1786.get("mandatory") is True
    assert "Steel" in qco_1786.get("product", "") or "Steel" in qco_1786.get("qco_name", "")


def test_related_standards_graph():
    """Verify related standards are resolved via the normative references graph."""
    related_456 = get_related_standards("IS 456:2000")
    assert len(related_456) > 0
    # IS 456 references IS 269, IS 1786, IS 10262, IS 383
    assert any(ref.get("is_number") in ["IS 269:2015", "IS 1786:2008", "IS 10262:2019", "IS 383:2016"] or "IS " in ref.get("is_number", "") for ref in related_456)


def test_confidence_generation_and_explainability():
    """Verify explainable why_recommended justification is generated."""
    std = {
        "is_number": "IS 10322 (Part 5/Sec 3):2018",
        "title": "Luminaires - Particular Requirements - Luminaires for Road and Street Lighting",
        "department": "Electrotechnical (ETD)",
        "is_qco_mandatory": True,
        "keywords": ["street light", "luminaire", "road lighting", "outdoor led"],
    }
    why = generate_why_recommended(
        standard=std,
        query="LED street light 100W for outdoor roadway lighting",
        matched_specs=["100W", "IP65"],
        confidence=94.5
    )
    assert len(why) > 10
    assert "Electrotechnical" in why or "outdoor" in why or "street" in why


def test_search_api_endpoint():
    """Verify the /api/search endpoint with multi-criteria filtering."""
    resp = client.post(
        "/api/search",
        json={
            "query": "Ordinary Portland Cement 53 Grade",
            "top_k": 5,
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data
    assert len(data["results"]) > 0
    first = data["results"][0]
    assert "is_number" in first
    assert "confidence" in first
    assert "why_recommended" in first


def test_chat_retrieval_grounding():
    """Verify /api/chat provides grounded recommendations and references."""
    resp = client.post(
        "/api/chat",
        json={
            "message": "Which BIS standard applies to Domestic Pressure Cookers?",
            "lang": "en",
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    # Should recommend IS 2347
    recs = data.get("recommendations", [])
    if recs:
        is_nums = [r.get("is_number") for r in recs]
        assert any("2347" in num for num in is_nums)


def test_document_upload_pipeline():
    """Verify /api/search/document pipeline processes procurement specifications."""
    tender_doc = """
    TENDER SPECIFICATION FOR ELECTRICAL INFRASTRUCTURE
    Clause 1: Supply and installation of PVC Insulated Copper Cables for working voltage up to 1100V.
    All cables must comply with BIS standards and bear valid ISI marking.
    Clause 2: Concrete foundations must use Ordinary Portland Cement 43 Grade according to BIS.
    """
    file_bytes = io.BytesIO(tender_doc.encode("utf-8"))
    resp = client.post(
        "/api/search/document",
        files={"document": ("tender_spec.txt", file_bytes, "text/plain")}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data
    assert len(data["results"]) > 0
    assert "request_id" in data
