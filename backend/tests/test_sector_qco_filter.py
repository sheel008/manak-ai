"""Unit and integration tests for M-01: Sector and QCO search filter integration."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.search_service import run_search
from app.retrieval.vector_search import matches_sector
from app.rules import certification as cert_rules


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_1_normal_search_unrestricted():
    """TEST 1: Normal search with no sector and no qco_required."""
    resp = run_search("LED street lighting 100W IP65")
    assert not resp.abstained, "Normal search should not abstain"
    assert len(resp.results) > 0, "Normal search should return results"


def test_2_search_with_valid_sector():
    """TEST 2: Search with a valid sector returns only matching sector standards."""
    sector_test = "Infrastructure & Construction"
    resp = run_search("cement concrete structural", sector=sector_test)
    assert not resp.abstained, "Sector search should not abstain"
    assert len(resp.results) > 0, "Sector search should return results"
    for r in resp.results:
        assert matches_sector(sector_test, r.sector), (
            f"Standard {r.is_number} sector '{r.sector}' does not match '{sector_test}'"
        )


def test_3_search_with_qco_required_true():
    """TEST 3: Search with qco_required=True returns only QCO applicable standards."""
    resp = run_search("steel deformed bar", qco_required=True)
    assert not resp.abstained, "QCO search should not abstain"
    assert len(resp.results) > 0, "QCO search should return results"
    for r in resp.results:
        qco_det = cert_rules.get_qco_details(r.is_number)
        is_qco = r.is_qco_mandatory or r.qco_required or (qco_det and qco_det.get("mandatory"))
        assert is_qco, f"Standard {r.is_number} is not QCO mandatory"


def test_4_search_with_qco_required_false():
    """TEST 4: Search with qco_required=False does not restrict to QCO-only."""
    resp = run_search("concrete mix proportioning guidelines", qco_required=False)
    assert not resp.abstained
    assert len(resp.results) > 0
    # IS 10262 is not QCO mandatory and should be retrievable when qco_required=False
    numbers = [r.is_number for r in resp.results]
    assert any("10262" in n or "456" in n for n in numbers)


def test_5_search_sector_and_department():
    """TEST 5: Search with sector + department respects both filters."""
    dept_test = "Civil Engineering"
    sector_test = "Infrastructure & Construction"
    resp = run_search("concrete", department=dept_test, sector=sector_test)
    assert not resp.abstained
    for r in resp.results:
        assert matches_sector(sector_test, r.sector)
        if r.department:
            assert dept_test.lower() in r.department.lower() or r.department.lower() in dept_test.lower()


def test_6_search_sector_and_qco_required():
    """TEST 6: Search with sector + qco_required=True respects both simultaneously."""
    sector_test = "Construction & Infrastructure"
    resp = run_search("steel bar", sector=sector_test, qco_required=True)
    assert not resp.abstained
    assert len(resp.results) > 0
    for r in resp.results:
        assert matches_sector(sector_test, r.sector)
        qco_det = cert_rules.get_qco_details(r.is_number)
        assert r.is_qco_mandatory or r.qco_required or (qco_det and qco_det.get("mandatory"))


def test_7_search_sector_department_and_qco():
    """TEST 7: Search with sector + department + qco_required=True respects all three."""
    resp = run_search(
        "cement",
        department="Civil Engineering",
        sector="Construction & Infrastructure",
        qco_required=True,
    )
    assert not resp.abstained
    assert len(resp.results) > 0
    for r in resp.results:
        assert matches_sector("Construction & Infrastructure", r.sector)
        qco_det = cert_rules.get_qco_details(r.is_number)
        assert r.is_qco_mandatory or r.qco_required or (qco_det and qco_det.get("mandatory"))


def test_8_non_matching_sector_zero_results():
    """TEST 8: Non-matching sector returns zero results and abstains (does NOT return all standards)."""
    resp = run_search("cement concrete", sector="NonExistent Aerospace Rocket Propulsion Sector")
    assert len(resp.results) == 0, f"Expected 0 results, got {len(resp.results)}"
    assert resp.abstained is True, "Expected abstained=True"


def test_http_api_search_with_sector_and_qco(client):
    """Test full HTTP POST /api/search with sector and qco_required in payload."""
    res = client.post(
        "/api/search",
        json={
            "query": "cement",
            "sector": "Infrastructure & Construction",
            "qco_required": True,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert not data["abstained"]
    assert len(data["results"]) > 0
    for r in data["results"]:
        assert matches_sector("Infrastructure & Construction", r["sector"])
        assert r["is_qco_mandatory"] or r["qco_required"]


def test_9_qco_source_of_truth_gap_covered():
    """TEST 9: Standard where is_qco_mandatory=False and qco_required=False in metadata

    but cert_rules.get_qco_details(is_number).mandatory=True (e.g. IS 2189:2008)
    must still be eligible and returned when qco_required=True.
    """
    import json
    import os
    from app.core import config

    # Verify that IS 2189:2008 has metadata flags as False in standards.json
    with open(config.STANDARDS_FILE, "r", encoding="utf-8") as f:
        stds = json.load(f)
    is2189 = next((s for s in stds if s["is_number"] == "IS 2189:2008"), None)
    assert is2189 is not None, "IS 2189:2008 not found in standards.json"
    assert is2189.get("is_qco_mandatory") is False
    assert is2189.get("qco_required") is False

    # Verify that cert_rules recognizes it as mandatory QCO
    qco_details = cert_rules.get_qco_details("IS 2189:2008")
    assert qco_details is not None
    assert qco_details.get("mandatory") is True

    # Search with qco_required=True
    resp = run_search("Automatic Fire Detection and Alarm System", qco_required=True)
    assert not resp.abstained, "Search should not abstain"
    assert len(resp.results) > 0, "Search should return results"

    is_numbers = [r.is_number for r in resp.results]
    assert "IS 2189:2008" in is_numbers, f"IS 2189:2008 should be returned under qco_required=True; got {is_numbers}"

    # Verify returned result sets is_qco_mandatory and qco_required to True
    res_2189 = next(r for r in resp.results if r.is_number == "IS 2189:2008")
    assert res_2189.is_qco_mandatory is True
    assert res_2189.qco_required is True

