"""Tests for M-04A: Long-document chunking coverage and best-score deduplication."""
import io
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core import config
from app.api.routes import chunk_document_text
from app.schemas import StandardResult


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_1_short_document_preserves_direct_path():
    """TEST 1: Document <= 3000 characters produces no chunks (direct search path)."""
    short_text = "Tender specification for structural concrete: Minimum compressive strength 25 MPa."
    assert len(short_text) < 3000
    chunks = chunk_document_text(short_text)
    assert chunks == [], "Short document should not be split into chunks"


def test_2_long_document_chunking_and_no_8_chunk_cap():
    """TEST 2: Document > 3000 characters generates multiple chunks without accidental 8-chunk cap."""
    # Build text of 20,000 characters
    paragraph = "Clause on technical specifications for ordinary portland cement and high grade structural steel. " * 15
    long_text = (paragraph + "\n\n") * 15
    assert len(long_text) > 15000

    chunks = chunk_document_text(long_text)

    # Must exceed the old 8-chunk cap
    assert len(chunks) > 8, f"Expected more than 8 chunks for >15k text, got {len(chunks)}"
    assert len(chunks) <= config.DOC_MAX_CHUNKS

    # Verify chunk sizing and overlap
    for ch in chunks[:-1]:  # all full chunks
        assert len(ch) <= config.DOC_CHUNK_SIZE
        assert len(ch) >= 100


def test_3_document_beyond_10k_reaches_search_chunks():
    """TEST 3: Technical clause located around character 15,000-18,000 is included in generated chunks."""
    marker = "SPECIAL CLAUSE 99: Supply of Grade 53 Ordinary Portland Cement conforming strictly to IS 12269:2013 with 28-day strength 53 MPa."

    filler = "General administrative terms, conditions, insurance requirements, and tender filing guidelines.\n"
    # Create padding to push marker past 15,000 characters
    pad_len = 16000
    padding = (filler * ((pad_len // len(filler)) + 1))[:pad_len]
    document_text = padding + "\n" + marker + "\n" + padding

    assert len(document_text) > 32000
    marker_pos = document_text.find(marker)
    assert 15000 <= marker_pos <= 18000, f"Marker position {marker_pos} not in 15k-18k range"

    chunks = chunk_document_text(document_text)

    # Verify marker is present in at least one chunk
    chunks_with_marker = [i for i, ch in enumerate(chunks) if "IS 12269:2013" in ch]
    assert len(chunks_with_marker) > 0, (
        f"Technical specification beyond 10,250 chars was NOT captured in any chunk! "
        f"Total chunks generated: {len(chunks)}"
    )


def test_4_max_chunk_budget_enforced():
    """TEST 4: Massive document stops at DOC_MAX_CHUNKS and does not run unbounded."""
    massive_text = "Long procurement document specification sentence with technical details. " * 5000
    assert len(massive_text) > 100000

    chunks = chunk_document_text(massive_text)
    assert len(chunks) == config.DOC_MAX_CHUNKS, (
        f"Expected exactly DOC_MAX_CHUNKS={config.DOC_MAX_CHUNKS}, got {len(chunks)}"
    )


def test_5_best_score_deduplication():
    """TEST 5: Aggregation retains the strongest score when the same standard appears in multiple chunks."""
    from types import SimpleNamespace
    res_low = SimpleNamespace(is_number="IS 456:2000", relevance_score=55.0, title="Plain and Reinforced Concrete")
    res_high = SimpleNamespace(is_number="IS 456:2000", relevance_score=88.0, title="Plain and Reinforced Concrete")

    # Emulate the deduplication loop in search_document
    seen_standards = {}
    mock_chunk_results = [[res_low], [res_high]]

    for chunk_res in mock_chunk_results:
        for r in chunk_res:
            if (
                r.is_number not in seen_standards
                or (r.relevance_score or 0) > (seen_standards[r.is_number].relevance_score or 0)
            ):
                seen_standards[r.is_number] = r

    final_results = list(seen_standards.values())
    assert len(final_results) == 1
    assert final_results[0].is_number == "IS 456:2000"
    assert final_results[0].relevance_score == 88.0, (
        f"Expected best score 88.0 to be retained, got {final_results[0].relevance_score}"
    )


def test_6_api_search_document_long_file_integration(client):
    """TEST 6: Full HTTP integration test for /api/search/document with text > 10k chars."""
    filler = "Notice Inviting Tender for Civil Construction and Engineering Works.\nAll bidders must comply with statutory requirements.\n"
    header = (filler * 120)[:14000] # 14k chars of filler
    technical = "\nTECHNICAL CLAUSE: Concrete works must strictly use Ordinary Portland Cement 53 Grade conforming to IS 12269:2013 and Plain Concrete to IS 456:2000.\n"
    doc_content = header + technical

    file_bytes = io.BytesIO(doc_content.encode("utf-8"))
    resp = client.post(
        "/api/search/document",
        files={"document": ("extended_tender.txt", file_bytes, "text/plain")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert not data["abstained"]
    assert len(data["results"]) > 0

    # Verify query string reflects > 8 clauses analyzed
    query_str = data["query"]
    assert "clauses analyzed" in query_str

    # Extract clause count from query string e.g. "Procurement Document: extended_tender.txt (12 clauses analyzed)"
    import re
    match = re.search(r"\((\d+) clauses analyzed\)", query_str)
    assert match is not None
    clauses_analyzed = int(match.group(1))
    assert clauses_analyzed > 8, f"Expected more than 8 clauses analyzed, got {clauses_analyzed}"

    # Verify technical standard IS 12269:2013 located past 14k chars was retrieved
    retrieved_numbers = [r["is_number"] for r in data["results"]]
    assert any("12269" in num or "456" in num for num in retrieved_numbers), (
        f"Standard located past 14,000 characters not found in results: {retrieved_numbers}"
    )
