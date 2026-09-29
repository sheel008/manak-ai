"""Tests for M-02: PostgreSQL Schema & Data-Model Alignment."""
import json
import os
import pytest
from app.core import config, database
from app.services.search_service import run_search
from app.retrieval.vector_search import matches_sector, vector_search
from app.rules import certification as cert_rules


@pytest.fixture(scope="module")
def db_conn():
    conn = database.get_connection()
    yield conn
    conn.close()


def test_1_postgres_schema_contains_canonical_fields(db_conn):
    """Test 1: PostgreSQL standards table contains all required canonical fields."""
    with db_conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name, data_type, udt_name
            FROM information_schema.columns
            WHERE table_name = 'standards'
            """
        )
        cols = {r["column_name"]: r for r in cur.fetchall()}

    expected_fields = [
        "id",
        "is_number",
        "title",
        "category",
        "sub_category",
        "scope",
        "specifications",
        "normative_references",
        "is_qco_mandatory",
        "qco_enforcement_date",
        "version",
        "last_amended",
        "amendment_history",
        "source_excerpt",
        "embedding",
        # Canonical M-02 fields
        "department",
        "sector",
        "qco_required",
        "search_weight_boost",
        "keywords",
        "description",
        "status",
        "source",
        "provenance",
        "related_standards",
        "revision_year",
        "international_equivalent",
        "title_hindi",
    ]

    for field in expected_fields:
        assert field in cols, f"Required column '{field}' missing from PostgreSQL standards table"

    # Verify types
    assert cols["embedding"]["udt_name"] == "vector"
    assert cols["specifications"]["udt_name"] == "jsonb"
    assert cols["amendment_history"]["udt_name"] == "jsonb"
    assert cols["keywords"]["udt_name"] == "_text"
    assert cols["related_standards"]["udt_name"] == "_text"
    assert cols["is_qco_mandatory"]["udt_name"] == "bool"
    assert cols["qco_required"]["udt_name"] == "bool"


def test_2_embedding_dimensions_are_384(db_conn):
    """Test 2: PostgreSQL accepts and stores 384-dimensional pgvector embeddings."""
    with db_conn.cursor() as cur:
        cur.execute(
            """
            SELECT is_number, vector_dims(embedding) AS dim
            FROM standards
            WHERE embedding IS NOT NULL
            LIMIT 10
            """
        )
        rows = cur.fetchall()
        assert len(rows) > 0, "No standards with embeddings found in database"
        for r in rows:
            assert r["dim"] == 384, f"Standard {r['is_number']} has dimension {r['dim']} != 384"


def test_3_standard_metadata_survives_seed(db_conn):
    """Test 3: Exactly 528 standards in JSON survive seed into PostgreSQL with full metadata."""
    with open(config.STANDARDS_FILE, "r", encoding="utf-8") as f:
        standards_json = json.load(f)

    with db_conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS total FROM standards")
        total_in_db = cur.fetchone()["total"]
        assert total_in_db == len(standards_json) == 528

        # Test random sample
        sample = standards_json[0]
        cur.execute(
            "SELECT * FROM standards WHERE is_number = %s",
            (sample["is_number"],),
        )
        db_row = cur.fetchone()
        assert db_row is not None
        assert db_row["title"] == sample["title"]
        assert db_row["category"] == sample["category"]
        assert db_row["department"] == sample["department"]
        assert db_row["sector"] == sample["sector"]


def test_4_sector_metadata_survives_seed(db_conn):
    """Test 4: Sector metadata is populated for all 528 standards without nulls."""
    with db_conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*) AS total,
                   COUNT(sector) AS with_sector
            FROM standards
            """
        )
        counts = cur.fetchone()
        assert counts["total"] == 528
        assert counts["with_sector"] == 528


def test_5_department_metadata_survives_seed(db_conn):
    """Test 5: Department metadata is populated for all 528 standards and 14 BIS departments seeded."""
    with db_conn.cursor() as cur:
        cur.execute("SELECT COUNT(department) AS with_dept FROM standards")
        assert cur.fetchone()["with_dept"] == 528

        cur.execute("SELECT COUNT(*) AS dept_count FROM departments")
        assert cur.fetchone()["dept_count"] == 14


def test_6_qco_metadata_survives_seed_and_aligns(db_conn):
    """Test 6: QCO metadata aligns with canonical rules in certification.py."""
    with db_conn.cursor() as cur:
        # Check IS 2189:2008 (the canonical statutory gap standard)
        cur.execute(
            """
            SELECT is_number, is_qco_mandatory, qco_required
            FROM standards
            WHERE is_number = 'IS 2189:2008'
            """
        )
        row = cur.fetchone()
        assert row is not None
        assert row["is_qco_mandatory"] is True
        assert row["qco_required"] is True


def test_7_vector_search_returns_all_canonical_fields(db_conn):
    """Test 7: vector_search returns candidates with all canonical fields populated."""
    candidates = vector_search("cement concrete", top_k=5)
    assert len(candidates) > 0
    first = candidates[0]
    required_keys = [
        "is_number", "title", "category", "scope", "department",
        "sector", "qco_required", "search_weight_boost", "keywords",
        "related_standards", "similarity"
    ]
    for k in required_keys:
        assert k in first, f"Missing key '{k}' in retrieved candidate"
    assert first["department"] is not None
    assert first["sector"] is not None
    assert isinstance(first["similarity"], float)


def test_8_end_to_end_search_with_postgres_integration():
    """Test 8: run_search works with live PostgreSQL database and respects all filters."""
    # Test with sector filter
    resp = run_search("cement concrete", sector="Construction & Infrastructure")
    assert not resp.abstained
    assert len(resp.results) > 0
    for r in resp.results:
        assert matches_sector("Construction & Infrastructure", r.sector)

    # Test with qco_required
    resp_qco = run_search("steel bar", qco_required=True)
    assert not resp_qco.abstained
    assert len(resp_qco.results) > 0
    for r in resp_qco.results:
        assert r.is_qco_mandatory or r.qco_required
