"""End-to-end HTTP smoke test of the FastAPI routes.

Uses the REAL search pipeline with mocked DB rows / vector search, verifying route
handlers, request validation, response serialization, and export text — all without a
live Postgres / pgvector server (which would require Docker).
"""
import io
import json
import os
import sys
import types
from datetime import datetime

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND)
DATA_DIR = os.path.join(BACKEND, "data")

# ---- Mock embedding module (avoid sentence-transformers) ----
_mock_embedding = types.ModuleType("app.services.embedding")
_mock_embedding.embed_query = lambda t: [0.1] * 384
_mock_embedding.embed_texts = lambda xs: [[0.1] * 384 for _ in xs]
sys.modules["app.services.embedding"] = _mock_embedding


class _Row(dict):
    """dict subclass mimicking psycopg2 RealDictRow (subscriptable + attribute access)."""
    def __init__(self, d):
        super().__init__(d)
        self.__dict__ = self


def _load_standards():
    with open(os.path.join(DATA_DIR, "standards.json"), "r", encoding="utf-8") as f:
        return json.load(f)


# Shared per-test state
STD_ROWS = {}          # is_number -> row (for detail/export)
REVIEWS_ACCEPTED = []  # is_numbers accepted for this request
CERT_MATCH = None
RULES_ROWS = []
SEARCH_LOGS = []
SAVED_ITEMS = {}       # is_number -> _Row
DEPARTMENTS = []


def _fake_cursor():
    class Cur:
        def __init__(self):
            self._rows = []
            self._sql = ""

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def execute(self, sql, params=None):
            self._sql = sql
            params = params or ()
            if "FROM standards WHERE is_number" in sql and params:
                std = STD_ROWS.get(params[0])
                self._rows = [std] if std else []
            elif "FROM standards" in sql and "REPLACE" in sql and params:
                stripped = params[0].replace(" ", "").replace(":", "")
                match = None
                for k, v in STD_ROWS.items():
                    if k.replace(" ", "").replace(":", "") == stripped:
                        match = v
                        break
                self._rows = [match] if match else []
            elif "COUNT(*) AS c FROM standards" in sql:
                self._rows = [_Row({"c": len(STD_ROWS)})]
            elif "INSERT INTO reviews" in sql:
                self._rows = [_Row({"request_id": params[0], "is_number": params[1], "decision": params[2]})]
            elif "decision = 'accept'" in sql:
                self._rows = [_Row({"is_number": i}) for i in REVIEWS_ACCEPTED]
            elif "COUNT(*) AS c FROM certification_rules" in sql:
                self._rows = [_Row({"c": len(RULES_ROWS)})]
            elif "FROM certification_rules" in sql:
                self._rows = RULES_ROWS
            elif "INSERT INTO search_logs" in sql:
                row = _Row({
                    "id": len(SEARCH_LOGS) + 1,
                    "query": params[0],
                    "top_result_is_number": params[1],
                    "department": params[2],
                    "result_count": params[3],
                    "created_at": datetime.now(),
                })
                SEARCH_LOGS.append(row)
                self._rows = [row]
            elif "DATE(created_at) AS search_date" in sql:
                self._rows = [_Row({"search_date": datetime.now().date(), "count": len(SEARCH_LOGS)})]
            elif "FROM search_logs sl" in sql and "GROUP BY s.category" in sql:
                counts = {}
                for log in SEARCH_LOGS:
                    top_std = STD_ROWS.get(log.get("top_result_is_number"))
                    if top_std and top_std.get("category"):
                        c = top_std["category"]
                        counts[c] = counts.get(c, 0) + 1
                self._rows = [_Row({"category": k, "count": v}) for k, v in counts.items()]
            elif "FROM search_logs" in sql and "department = %s" in sql:
                filtered = [r for r in SEARCH_LOGS if r.get("department") == params[0]]
                self._rows = filtered
            elif "FROM search_logs" in sql and "COUNT(*)" in sql:
                self._rows = [_Row({"c": len(SEARCH_LOGS)})]
            elif "FROM search_logs" in sql:
                self._rows = list(reversed(SEARCH_LOGS))
            elif "SELECT id FROM saved_items WHERE is_number" in sql:
                std_key = params[0]
                self._rows = [_Row({"id": SAVED_ITEMS[std_key]["id"]})] if std_key in SAVED_ITEMS else []
            elif "INSERT INTO saved_items" in sql:
                row = _Row({
                    "id": len(SAVED_ITEMS) + 1,
                    "is_number": params[0],
                    "title": params[1],
                    "category": params[2],
                    "is_qco_mandatory": params[3],
                    "saved_at": datetime.now(),
                })
                SAVED_ITEMS[params[0]] = row
                self._rows = [row]
            elif "COUNT(*) AS c FROM saved_items" in sql:
                self._rows = [_Row({"c": len(SAVED_ITEMS)})]
            elif "DELETE FROM saved_items" in sql:
                is_num = params[0]
                deleted = None
                for k in list(SAVED_ITEMS.keys()):
                    if k == is_num or k.replace(" ", "").replace(":", "") == is_num.replace(" ", "").replace(":", ""):
                        deleted = SAVED_ITEMS.pop(k)
                        break
                self._rows = [_Row({"id": deleted["id"]})] if deleted else []
            elif "FROM saved_items" in sql:
                self._rows = list(SAVED_ITEMS.values())
            elif "FROM departments" in sql:
                self._rows = DEPARTMENTS
            else:
                self._rows = []
            return self

        def fetchone(self):
            return self._rows[0] if self._rows else None

        def fetchall(self):
            return self._rows

    return Cur()


def _fake_connection():
    conn = types.SimpleNamespace()
    conn.autocommit = False
    conn.cursor = _fake_cursor
    conn.close = lambda: None
    return conn


def _build_app(monkeypatch):
    import app.core.database as db
    monkeypatch.setattr(db, "get_connection", _fake_connection)

    import app.retrieval.vector_search as vsmod
    def _fake_vector_search(q, top_k=None):
        return [{**s, "similarity": 0.8} for s in STD_ROWS.values()]
    monkeypatch.setattr(vsmod, "vector_search", _fake_vector_search)

    import app.rules.related as relmod
    monkeypatch.setattr(relmod, "resolve_references", lambda refs: [{"is_number": n, "title": "T", "category": "C"} for n in (refs or [])])
    monkeypatch.setattr(
        relmod,
        "compute_related_standards",
        lambda i, limit=12: [
            {"is_number": "IS 456:2000", "title": "Plain and reinforced concrete", "category": "Construction and Civil Engineering"}
        ],
    )

    import app.rules.certification as certmod
    monkeypatch.setattr(certmod, "lookup_product", lambda name: CERT_MATCH)

    from fastapi import FastAPI
    from app.api.routes import router
    app = FastAPI()
    app.include_router(router, prefix="/api")

    @app.get("/health")
    def root_health():
        return {"status": "ok"}

    from fastapi.testclient import TestClient
    return TestClient(app)



def test_search_endpoint(monkeypatch):
    global STD_ROWS, SEARCH_LOGS
    SEARCH_LOGS = []
    STD_ROWS = {s["is_number"]: s for s in _load_standards()}
    client = _build_app(monkeypatch)
    r = client.post("/api/search", json={"query": "LED street light IP65", "department": "Ministry of Power"})
    assert r.status_code == 200
    body = r.json()
    assert body["abstained"] is False
    assert len(body["results"]) >= 1
    top = body["results"][0]
    assert "is_number" in top and top["is_number"]
    assert top["evidence"]["matched_specifications"] is not None
    assert top["version_info"]["version"] is not None
    assert "status" in top["certification"]

    # Verify search was logged to search_logs
    assert len(SEARCH_LOGS) == 1
    assert SEARCH_LOGS[0]["query"] == "LED street light IP65"
    assert SEARCH_LOGS[0]["department"] == "Ministry of Power"
    assert SEARCH_LOGS[0]["top_result_is_number"] == top["is_number"]


def test_search_empty_query_400(monkeypatch):
    client = _build_app(monkeypatch)
    r = client.post("/api/search", json={"query": "   "})
    assert r.status_code == 400


def test_document_search_txt(monkeypatch):
    global STD_ROWS, SEARCH_LOGS
    SEARCH_LOGS = []
    STD_ROWS = {s["is_number"]: s for s in _load_standards()}
    client = _build_app(monkeypatch)
    r = client.post(
        "/api/search/document",
        files={"document": ("spec.txt", io.BytesIO(b"LED street light IP65 outdoor luminaire"), "text/plain")},
        data={"department": "Ministry of Textiles"},
    )
    assert r.status_code == 200
    assert r.json()["abstained"] is False
    assert len(r.json()["results"]) >= 1
    assert len(SEARCH_LOGS) >= 1
    assert SEARCH_LOGS[-1]["department"] == "Ministry of Textiles"


def test_document_unsupported_type_400(monkeypatch):
    client = _build_app(monkeypatch)
    r = client.post(
        "/api/search/document",
        files={"document": ("spec.xyz", io.BytesIO(b"hello"), "application/octet-stream")},
    )
    assert r.status_code == 400


def test_standards_detail(monkeypatch):
    global STD_ROWS
    STD_ROWS = {s["is_number"]: s for s in _load_standards()}
    key = next(k for k in STD_ROWS if "269" in k)
    client = _build_app(monkeypatch)
    r = client.get(f"/api/standards/{key.replace('/', '%2F').replace(':', '%3A').replace(' ', '%20')}")
    assert r.status_code == 200
    body = r.json()
    assert body["is_number"] == key
    assert "normative_references_resolved" in body
    assert "related_standards" in body


def test_standards_detail_404(monkeypatch):
    global STD_ROWS
    STD_ROWS = {}
    client = _build_app(monkeypatch)
    r = client.get("/api/standards/DOESNOTEXIST:1")
    assert r.status_code == 404


def test_certification_check_found(monkeypatch):
    global CERT_MATCH
    CERT_MATCH = {
        "product_name": "LED street light",
        "is_qco_mandatory": True,
        "applicable_is_number": "IS 10322:2018",
        "enforcement_date": "2025-06-01",
        "aliases": ["street light"],
    }
    client = _build_app(monkeypatch)
    r = client.post("/api/certification-check", json={"product_name": "LED street light"})
    assert r.status_code == 200
    assert r.json()["found"] is True
    assert r.json()["is_qco_mandatory"] is True


def test_certification_check_not_found(monkeypatch):
    global CERT_MATCH
    CERT_MATCH = None
    client = _build_app(monkeypatch)
    r = client.post("/api/certification-check", json={"product_name": "banana"})
    assert r.status_code == 200
    assert r.json()["found"] is False


def test_qco_check_parity_alias(monkeypatch):
    global CERT_MATCH
    CERT_MATCH = {
        "product_name": "LED street light",
        "is_qco_mandatory": True,
        "applicable_is_number": "IS 10322:2018",
        "enforcement_date": "2025-06-01",
        "aliases": ["street light"],
    }
    client = _build_app(monkeypatch)
    r = client.post("/api/qco-check", json={"product_name": "LED street light"})
    assert r.status_code == 200
    assert r.json()["found"] is True
    assert r.json()["applicable_is_number"] == "IS 10322:2018"


def test_reviews_post_and_validate(monkeypatch):
    client = _build_app(monkeypatch)
    r = client.post("/api/reviews", json={"request_id": "req-1", "is_number": "IS 1", "decision": "accept"})
    assert r.status_code == 200
    assert r.json()["decision"] == "accept"
    r = client.post("/api/reviews", json={"request_id": "req-1", "is_number": "IS 1", "decision": "bogus"})
    assert r.status_code == 400
    r = client.get("/api/reviews/req-1")
    assert r.status_code == 200
    assert r.json()["request_id"] == "req-1"


def test_export(monkeypatch):
    global STD_ROWS, REVIEWS_ACCEPTED
    STD_ROWS = {s["is_number"]: s for s in _load_standards()}
    key = next(k for k in STD_ROWS if "269" in k)
    REVIEWS_ACCEPTED = [key]
    client = _build_app(monkeypatch)
    r = client.post("/api/export/req-1")
    assert r.status_code == 200
    assert "TENDER-READY STANDARDS REFERENCE BLOCK" in r.text
    assert key in r.text


def test_export_single_standard(monkeypatch):
    global STD_ROWS
    STD_ROWS = {s["is_number"]: s for s in _load_standards()}
    key = next(k for k in STD_ROWS if "269" in k)
    client = _build_app(monkeypatch)
    r = client.post(f"/api/export/{key}")
    assert r.status_code == 200
    assert "BUREAU OF INDIAN STANDARDS" in r.text
    assert "Standard Reference Document" in r.text
    assert key in r.text
    assert "Content-Disposition" in r.headers
    assert "attachment; filename=" in r.headers["Content-Disposition"]


def test_export_gem_payload(monkeypatch):
    global STD_ROWS
    STD_ROWS = {s["is_number"]: s for s in _load_standards()}
    key = next(k for k in STD_ROWS if "269" in k)
    client = _build_app(monkeypatch)
    r = client.post(f"/api/export/gem-payload/{key}")
    assert r.status_code == 200
    payload = r.json()
    assert payload["schema_version"] == "2.1"
    assert payload["source_system"] == "BIS_MANAK_AI"
    assert payload["tender_parameters"]["reference_standard"] == key


def test_dashboard_stats(monkeypatch):
    global STD_ROWS, RULES_ROWS, SAVED_ITEMS, SEARCH_LOGS
    STD_ROWS = {s["is_number"]: s for s in _load_standards()}
    RULES_ROWS = [_Row({
        "product_name": "LED street light", "applicable_is_number": "IS 10322:2018",
        "enforcement_date": "2025-06-01",
    })]
    SAVED_ITEMS = {"IS 269:2015": _Row({"id": 1})}
    SEARCH_LOGS = [_Row({"id": 1})]
    client = _build_app(monkeypatch)
    r = client.get("/api/dashboard/stats")
    assert r.status_code == 200
    body = r.json()
    # Original FastAPI fields
    assert body["total_standards"] == len(STD_ROWS)
    assert body["qco_deadlines_next_30d"] == 1
    assert body["qco_deadline_details"][0]["product_name"] == "LED street light"
    # Express parity fields
    assert body["searchesThisMonth"] >= 1
    assert body["standardsSaved"] == 1
    assert "qcoDeadlines" in body
    assert body["qcoRules"] == len(RULES_ROWS)
    assert body["total_qco_rules"] == len(RULES_ROWS)


def test_compare_standards_get(monkeypatch):
    global STD_ROWS
    STD_ROWS = {s["is_number"]: s for s in _load_standards()}
    keys = list(STD_ROWS.keys())[:2]
    client = _build_app(monkeypatch)
    r = client.get(f"/api/standards/compare?ids={keys[0]},{keys[1]}")
    assert r.status_code == 200
    body = r.json()
    assert "comparison" in body
    assert len(body["comparison"]) == 2
    assert body["comparison"][0]["is_number"] == keys[0]


def test_compare_standards_post(monkeypatch):
    global STD_ROWS
    STD_ROWS = {s["is_number"]: s for s in _load_standards()}
    keys = list(STD_ROWS.keys())[:2]
    client = _build_app(monkeypatch)
    r = client.post("/api/standards/compare", json={"is_numbers": [keys[0], keys[1]]})
    assert r.status_code == 200
    body = r.json()
    assert len(body["comparison"]) == 2


def test_compare_standards_validation_400(monkeypatch):
    client = _build_app(monkeypatch)
    r = client.get("/api/standards/compare?ids=IS1")
    assert r.status_code == 400
    r = client.get("/api/standards/compare")
    assert r.status_code == 400
    r = client.post("/api/standards/compare", json={"is_numbers": ["IS1"]})
    assert r.status_code == 400


def test_qco_list(monkeypatch):
    global RULES_ROWS
    RULES_ROWS = [
        _Row({
            "id": 1,
            "product_name": "Cement",
            "aliases": ["OPC"],
            "is_qco_mandatory": True,
            "applicable_is_number": "IS 269:2015",
            "enforcement_date": "2024-01-01",
            "product_category": "Construction",
            "standard_title": "Ordinary Portland Cement",
        }),
        _Row({
            "id": 2,
            "product_name": "Steel Bars",
            "aliases": ["TMT"],
            "is_qco_mandatory": True,
            "applicable_is_number": "IS 1786:2008",
            "enforcement_date": "2024-06-01",
            "product_category": "Construction",
            "standard_title": "High strength deformed steel bars",
        }),
    ]
    client = _build_app(monkeypatch)
    r = client.get("/api/qco/list")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2
    assert len(body["rules"]) == 2
    assert "Construction" in body["categories"]
    assert len(body["categories"]["Construction"]) == 2


def test_standards_related(monkeypatch):
    global STD_ROWS
    STD_ROWS = {s["is_number"]: s for s in _load_standards()}
    key = next(k for k in STD_ROWS if "269" in k)
    client = _build_app(monkeypatch)
    r = client.get(f"/api/standards/{key}/related")
    assert r.status_code == 200
    body = r.json()
    assert body["standard"] == key
    assert len(body["related"]) >= 1


def test_standards_related_404(monkeypatch):
    global STD_ROWS
    STD_ROWS = {}
    client = _build_app(monkeypatch)
    r = client.get("/api/standards/NONEXISTENT/related")
    assert r.status_code == 404


def test_history_endpoint(monkeypatch):
    global SEARCH_LOGS
    SEARCH_LOGS = [
        _Row({"id": 1, "query": "cement", "top_result_is_number": "IS 269:2015", "department": "Ministry of Power", "result_count": 5, "created_at": datetime.now()}),
        _Row({"id": 2, "query": "steel", "top_result_is_number": "IS 1786:2008", "department": "Ministry of Textiles", "result_count": 3, "created_at": datetime.now()}),
    ]
    client = _build_app(monkeypatch)
    r = client.get("/api/history")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 2
    assert body[0]["query"] == "steel"  # Ordered by created_at DESC

    r_dept = client.get("/api/history?department=Ministry%20of%20Power")
    assert r_dept.status_code == 200
    body_dept = r_dept.json()
    assert len(body_dept) == 1
    assert body_dept[0]["department"] == "Ministry of Power"


def test_saved_items_crud(monkeypatch):
    global STD_ROWS, SAVED_ITEMS
    STD_ROWS = {s["is_number"]: s for s in _load_standards()}
    key = next(k for k in STD_ROWS if "269" in k)
    SAVED_ITEMS = {}
    client = _build_app(monkeypatch)

    # Save
    r = client.post("/api/saved", json={"is_number": key})
    assert r.status_code == 201
    saved_entry = r.json()
    assert saved_entry["is_number"] == key
    assert "saved_date" in saved_entry

    # Duplicate check
    r_dup = client.post("/api/saved", json={"is_number": key})
    assert r_dup.status_code == 409

    # List saved
    r_list = client.get("/api/saved")
    assert r_list.status_code == 200
    items = r_list.json()
    assert len(items) == 1
    assert items[0]["is_number"] == key

    # Delete
    r_del = client.delete(f"/api/saved/{key}")
    assert r_del.status_code == 200
    assert r_del.json()["message"] == "Removed from saved"

    # Delete again -> 404
    r_del2 = client.delete(f"/api/saved/{key}")
    assert r_del2.status_code == 404


def test_saved_items_validation_errors(monkeypatch):
    global STD_ROWS
    STD_ROWS = {}
    client = _build_app(monkeypatch)

    # Missing / empty
    r = client.post("/api/saved", json={"is_number": "   "})
    assert r.status_code == 400

    # Not found
    r = client.post("/api/saved", json={"is_number": "IS 99999"})
    assert r.status_code == 404


def test_dashboard_trends(monkeypatch):
    global SEARCH_LOGS, STD_ROWS
    STD_ROWS = {s["is_number"]: s for s in _load_standards()}
    key = next(k for k in STD_ROWS if "269" in k)
    SEARCH_LOGS = [
        _Row({"id": 1, "query": "cement", "top_result_is_number": key, "department": "Commerce", "result_count": 5, "created_at": datetime.now()}),
    ]
    client = _build_app(monkeypatch)
    r = client.get("/api/dashboard/trends")
    assert r.status_code == 200
    body = r.json()
    assert "searches_per_day" in body
    assert len(body["searches_per_day"]) == 7
    assert "top_categories" in body
    assert len(body["top_categories"]) >= 1


def test_departments(monkeypatch):
    global DEPARTMENTS
    DEPARTMENTS = [
        _Row({"id": 1, "name": "Ministry of Commerce & Industry", "officer_name": "Rajesh Kumar", "designation": "Senior Procurement Officer"}),
        _Row({"id": 2, "name": "Ministry of Power", "officer_name": "Amit Sharma", "designation": "Director of Standards"}),
    ]
    client = _build_app(monkeypatch)
    r = client.get("/api/departments")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 2
    assert body[0]["name"] == "Ministry of Commerce & Industry"
    assert body[0]["officer_name"] == "Rajesh Kumar"


def test_chat(monkeypatch):
    global STD_ROWS
    STD_ROWS = {s["is_number"]: s for s in _load_standards()}
    client = _build_app(monkeypatch)
    r = client.post("/api/chat", json={"message": "What is the standard for cement?"})
    assert r.status_code == 200
    body = r.json()
    assert "sessionId" in body
    assert "message" in body
    assert "citations" in body


def test_health(monkeypatch):
    client = _build_app(monkeypatch)
    r1 = client.get("/health")
    assert r1.status_code == 200
    assert r1.json() == {"status": "ok"}

    r2 = client.get("/api/health")
    assert r2.status_code == 200
    assert r2.json() == {"status": "ok"}


def test_canonical_readme_queries(monkeypatch):
    global STD_ROWS, SEARCH_LOGS
    SEARCH_LOGS = []
    STD_ROWS = {s["is_number"]: s for s in _load_standards()}
    client = _build_app(monkeypatch)

    canonical_queries = [
        "LED street light 100W IP65 outdoor",
        "Portland cement OPC 53 grade",
        "concrete mix design M20",
        "PVC insulated cables 1100V",
    ]
    for q in canonical_queries:
        r = client.post("/api/search", json={"query": q})
        assert r.status_code == 200, f"Query failed: {q}"
        data = r.json()
        assert data["abstained"] is False
        assert len(data["results"]) >= 1
        top = data["results"][0]
        assert top["relevance_score"] > 0
        assert top["similarity_score"] > 0
        assert top["is_number"]


def test_rapid_sequential_searches(monkeypatch):
    global STD_ROWS, SEARCH_LOGS
    SEARCH_LOGS = []
    STD_ROWS = {s["is_number"]: s for s in _load_standards()}
    client = _build_app(monkeypatch)

    # 15 rapid consecutive searches to simulate simultaneous judge queries
    for i in range(15):
        r = client.post("/api/search", json={"query": f"cables voltage test {i}"})
        assert r.status_code == 200
        assert r.json()["request_id"]


def test_document_validation_errors(monkeypatch):
    client = _build_app(monkeypatch)

    # 1. Unsupported extension (.exe)
    r_bad_ext = client.post(
        "/api/search/document",
        files={"document": ("malicious.exe", io.BytesIO(b"binary data"), "application/octet-stream")},
    )
    assert r_bad_ext.status_code == 400
    assert "Unsupported file format" in r_bad_ext.json()["detail"]

    # 2. Empty file (0 bytes)
    r_empty = client.post(
        "/api/search/document",
        files={"document": ("empty.txt", io.BytesIO(b""), "text/plain")},
    )
    assert r_empty.status_code == 400
    assert "empty" in r_empty.json()["detail"].lower()

    # 3. Oversized file (> 15 MB)
    large_payload = b"x" * (15 * 1024 * 1024 + 100)
    r_large = client.post(
        "/api/search/document",
        files={"document": ("large.txt", io.BytesIO(large_payload), "text/plain")},
    )
    assert r_large.status_code == 413
    assert "15 MB" in r_large.json()["detail"]


def test_empty_query_validation(monkeypatch):
    client = _build_app(monkeypatch)
    r = client.post("/api/search", json={"query": "   \n\t  "})
    assert r.status_code == 400
    assert "empty" in r.json()["detail"].lower()



