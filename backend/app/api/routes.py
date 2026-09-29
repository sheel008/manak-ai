"""FastAPI router exposing the MANAK-AI API endpoints."""
import uuid
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import PlainTextResponse

from app.core import database, config
from app.schemas import (
    SearchRequest, SearchResponse, CertificationCheckRequest,
    ReviewCreate, CompareRequest, SavedItemCreate, ChatRequest,
)
from app.services.search_service import (
    run_search, increment_search_count, get_search_count,
)
from app.services.chat_service import handle_chat
from app.rules import certification as cert_rules, related as related_rules


router = APIRouter()


@router.get("/health")
def health():
    """Health check endpoint returning service status."""
    return {"status": "ok"}


def _get_standard_by_number(is_number: str):
    conn = database.get_connection()
    try:
        with conn.cursor() as cur:
            fields = """
                is_number, title, category, sub_category, scope,
                specifications, normative_references, is_qco_mandatory,
                qco_enforcement_date, version, last_amended,
                amendment_history, source_excerpt,
                department, sector, qco_required, search_weight_boost,
                keywords, description, status, source, provenance,
                related_standards, revision_year, international_equivalent, title_hindi
            """
            cur.execute(
                f"SELECT {fields} FROM standards WHERE is_number = %s",
                (is_number,),
            )
            row = cur.fetchone()
            if not row:
                cur.execute(
                    f"""SELECT {fields}
                        FROM standards
                        WHERE REPLACE(REPLACE(is_number, ' ', ''), ':', '') = REPLACE(REPLACE(%s, ' ', ''), ':', '')
                        LIMIT 1""",
                    (is_number,),
                )
                row = cur.fetchone()
            return row
    finally:
        conn.close()


# ── POST /api/search ──
@router.post("/search", response_model=SearchResponse)
def search(req: SearchRequest):
    if not req.query or not req.query.strip():
        raise HTTPException(400, "Search query cannot be empty.")
    if len(req.query) > 5000:
        raise HTTPException(400, "Search query exceeds maximum length of 5000 characters.")
    increment_search_count()
    return run_search(
        req.query,
        department=req.department,
        category=req.category,
        sector=req.sector,
        qco_required=req.qco_required,
        top_k=req.top_k,
        min_confidence=req.min_confidence,
    )


def chunk_document_text(
    text: str,
    chunk_size: Optional[int] = None,
    overlap: Optional[int] = None,
    max_chunks: Optional[int] = None,
) -> List[str]:
    """Chunk document text into overlapping segments up to max_chunks budget."""
    if not text or len(text) <= 3000:
        return []
    cs = chunk_size or config.DOC_CHUNK_SIZE
    ov = overlap or config.DOC_CHUNK_OVERLAP
    mc = max_chunks or config.DOC_MAX_CHUNKS
    stride = max(1, cs - ov)
    chunks = []
    start = 0
    while start < len(text) and len(chunks) < mc:
        end = min(len(text), start + cs)
        chunk_slice = text[start:end].strip()
        if len(chunk_slice) > 100:
            chunks.append(chunk_slice)
        start += stride
    return chunks


# ── POST /api/search/document ──
@router.post("/search/document", response_model=SearchResponse)
async def search_document(
    document: UploadFile = File(...),
    department: Optional[str] = Form(None),
):
    filename = document.filename or ""
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    content = await document.read()

    MAX_FILE_SIZE = 15 * 1024 * 1024  # 15 MB
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(413, "Uploaded file exceeds maximum limit of 15 MB.")
    if len(content) == 0:
        raise HTTPException(400, "Uploaded file is empty (0 bytes).")

    if ext == "txt":
        text = content.decode("utf-8", errors="ignore")
    elif ext == "pdf":
        text = _extract_pdf(content)
    elif ext == "docx":
        text = _extract_docx(content)
    else:
        raise HTTPException(400, "Unsupported file format. Please upload a PDF, DOCX, or TXT file.")

    if not text or not text.strip():
        raise HTTPException(422, "No extractable text found in the document")

    increment_search_count()

    # Clause-level chunking for long procurement documents (> 3000 chars)
    if len(text) > 3000:
        chunks = chunk_document_text(text)

        seen_standards = {}
        for ch in chunks:
            chunk_resp = run_search(ch, department=department)
            if not chunk_resp.abstained:
                for r in chunk_resp.results:
                    if (
                        r.is_number not in seen_standards
                        or (r.relevance_score or 0) > (seen_standards[r.is_number].relevance_score or 0)
                    ):
                        seen_standards[r.is_number] = r

        all_results = list(seen_standards.values())
        if all_results:
            all_results.sort(key=lambda x: (x.relevance_score or 0), reverse=True)
            trimmed = all_results[:5]
            for idx, item in enumerate(trimmed, start=1):
                item.rank = idx
            return SearchResponse(
                request_id=uuid.uuid4().hex[:12],
                query=f"Procurement Document: {filename} ({len(chunks)} clauses analyzed)",
                abstained=False,
                abstention_reason=None,
                results=trimmed,
                threshold=40.0,
            )

    resp = run_search(text, department=department)
    if resp.abstained or not resp.results:
        # Fallback: analyze individual non-empty substantive lines/clauses
        lines = [line.strip() for line in text.split("\n") if len(line.strip()) >= 25]
        for line in lines[:6]:
            sub_resp = run_search(line, department=department)
            if not sub_resp.abstained and sub_resp.results:
                return sub_resp
    return resp



def _extract_pdf(content):
    try:
        import io
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(content))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception:
        try:
            import pdfplumber
            import io
            text = []
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                for page in pdf.pages:
                    text.append(page.extract_text() or "")
            return "\n".join(text)
        except Exception:
            return ""


def _extract_docx(content):
    try:
        from docx import Document
        import io
        doc = Document(io.BytesIO(content))
        return "\n".join(p.text for p in doc.paragraphs)
    except Exception:
        return ""


# ── Standards Comparison ──
def _compare_standards(is_numbers: List[str]):
    if not is_numbers or len(is_numbers) < 2:
        raise HTTPException(400, "Provide an array of 2-3 IS numbers to compare")

    results = []
    for num in is_numbers[:5]:
        row = _get_standard_by_number(num)
        if row:
            d = dict(row)
            if d.get("qco_enforcement_date"):
                d["qco_enforcement_date"] = str(d["qco_enforcement_date"])
            if d.get("last_amended"):
                d["last_amended"] = str(d["last_amended"])
            results.append(d)
        else:
            results.append({"is_number": num, "error": "Not found"})
    return {"comparison": results}


@router.get("/standards/compare")
def compare_standards_get(ids: Optional[str] = Query(None)):
    if not ids or not ids.strip():
        raise HTTPException(400, "ids query parameter is required (e.g. ?ids=IS269,IS456)")
    is_numbers = [i.strip() for i in ids.split(",") if i.strip()]
    return _compare_standards(is_numbers)


@router.post("/standards/compare")
def compare_standards_post(req: CompareRequest):
    return _compare_standards(req.is_numbers)


# ── GET /api/standards/{is_number}/related ──
@router.get("/standards/{is_number}/related")
def get_related_standards(is_number: str, limit: int = 12):
    row = _get_standard_by_number(is_number)
    if not row:
        raise HTTPException(404, "Standard not found")
    related = related_rules.compute_related_standards(row["is_number"], limit=limit)
    return {
        "standard": row["is_number"],
        "related": related,
        "computed_from": "Shared normative references and co-occurrence analysis",
    }


# ── GET /api/standards/{is_number} ──
@router.get("/standards/{is_number}")
def get_standard(is_number: str):
    row = _get_standard_by_number(is_number)
    if not row:
        raise HTTPException(404, "Standard not found")
    resolved = related_rules.resolve_references(row.get("normative_references") or [])
    data = dict(row)
    data["normative_references_resolved"] = resolved
    data["related_standards"] = related_rules.compute_related_standards(row["is_number"], limit=5)
    return data


# ── GET /api/qco/list ──
@router.get("/qco/list")
def list_qco():
    conn = database.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT cr.id, cr.product_name, cr.aliases, cr.is_qco_mandatory,
                          cr.applicable_is_number, cr.enforcement_date,
                          COALESCE(s.category, 'Other') AS product_category,
                          s.title AS standard_title
                   FROM certification_rules cr
                   LEFT JOIN standards s ON (
                       cr.applicable_is_number = s.is_number
                       OR REPLACE(REPLACE(cr.applicable_is_number, ' ', ''), ':', '') = REPLACE(REPLACE(s.is_number, ' ', ''), ':', '')
                   )
                   WHERE cr.is_qco_mandatory = TRUE
                   ORDER BY cr.enforcement_date ASC NULLS LAST, cr.product_name ASC"""
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    formatted_rows = []
    grouped = {}
    for r in rows:
        item = {
            "id": r["id"],
            "product_name": r["product_name"],
            "aliases": r.get("aliases") or [],
            "is_qco_mandatory": bool(r.get("is_qco_mandatory", True)),
            "applicable_is_number": r.get("applicable_is_number"),
            "enforcement_date": str(r["enforcement_date"]) if r.get("enforcement_date") else None,
            "product_category": r.get("product_category") or "Other",
            "standard_title": r.get("standard_title"),
        }
        formatted_rows.append(item)
        cat = item["product_category"]
        if cat not in grouped:
            grouped[cat] = []
        grouped[cat].append(item)

    return {
        "total": len(formatted_rows),
        "rules": formatted_rows,
        "categories": grouped,
    }


# ── POST /api/certification-check and POST /api/qco-check ──
@router.post("/certification-check")
def certification_check(req: CertificationCheckRequest):
    match = cert_rules.lookup_product(req.product_name)
    if not match:
        return {
            "found": False,
            "product_name": req.product_name,
            "message": "No matching product found in the certification rules. "
                       "Certification status could not be established from the configured knowledge base.",
        }
    return {
        "found": True,
        "product_name": match["product_name"],
        "is_qco_mandatory": match["is_qco_mandatory"],
        "applicable_is_number": match["applicable_is_number"],
        "enforcement_date": str(match["enforcement_date"]) if match.get("enforcement_date") else None,
        "aliases": match["aliases"],
    }


@router.post("/qco-check")
def qco_check(req: CertificationCheckRequest):
    return certification_check(req)


# ── History ──
@router.get("/history")
def get_history(limit: int = 50, offset: int = 0, department: Optional[str] = None):
    conn = database.get_connection()
    try:
        with conn.cursor() as cur:
            if department:
                cur.execute(
                    """SELECT id, query, top_result_is_number, department, result_count, created_at
                       FROM search_logs
                       WHERE department = %s
                       ORDER BY created_at DESC
                       LIMIT %s OFFSET %s""",
                    (department, limit, offset),
                )
            else:
                cur.execute(
                    """SELECT id, query, top_result_is_number, department, result_count, created_at
                       FROM search_logs
                       ORDER BY created_at DESC
                       LIMIT %s OFFSET %s""",
                    (limit, offset),
                )
            rows = cur.fetchall()
    finally:
        conn.close()

    return [
        {
            "id": r["id"],
            "query": r["query"],
            "top_result_is_number": r.get("top_result_is_number"),
            "department": r.get("department"),
            "result_count": r.get("result_count", 0),
            "created_at": r["created_at"].isoformat() if r.get("created_at") else None,
            "timestamp": r["created_at"].isoformat() if r.get("created_at") else None,
        }
        for r in rows
    ]


# ── Saved Items CRUD ──
@router.get("/saved")
def get_saved():
    conn = database.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, is_number, title, category, is_qco_mandatory, saved_at
                   FROM saved_items
                   ORDER BY saved_at DESC"""
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    return [
        {
            "id": r["id"],
            "is_number": r["is_number"],
            "title": r["title"],
            "category": r.get("category"),
            "is_qco_mandatory": bool(r.get("is_qco_mandatory", False)),
            "saved_at": r["saved_at"].isoformat() if r.get("saved_at") else None,
            "saved_date": r["saved_at"].isoformat()[:10] if r.get("saved_at") else None,
        }
        for r in rows
    ]


@router.post("/saved", status_code=201)
def create_saved(item: SavedItemCreate):
    is_num = (item.is_number or "").strip()
    if not is_num:
        raise HTTPException(400, "is_number is required")

    std = _get_standard_by_number(is_num)
    if not std:
        raise HTTPException(404, "Standard not found")

    canonical_num = std["is_number"]
    conn = database.get_connection()
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM saved_items WHERE is_number = %s", (canonical_num,))
            if cur.fetchone():
                raise HTTPException(409, "Already saved")

            cur.execute(
                """INSERT INTO saved_items (is_number, title, category, is_qco_mandatory)
                   VALUES (%s, %s, %s, %s)
                   RETURNING id, is_number, title, category, is_qco_mandatory, saved_at""",
                (canonical_num, std["title"], std.get("category"), bool(std.get("is_qco_mandatory", False))),
            )
            row = cur.fetchone()
    finally:
        conn.close()

    return {
        "id": row["id"],
        "is_number": row["is_number"],
        "title": row["title"],
        "category": row.get("category"),
        "is_qco_mandatory": bool(row.get("is_qco_mandatory", False)),
        "saved_at": row["saved_at"].isoformat() if row.get("saved_at") else None,
        "saved_date": row["saved_at"].isoformat()[:10] if row.get("saved_at") else None,
    }


@router.delete("/saved/{is_number}")
def delete_saved(is_number: str):
    conn = database.get_connection()
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(
                """DELETE FROM saved_items
                   WHERE is_number = %s
                      OR REPLACE(REPLACE(is_number, ' ', ''), ':', '') = REPLACE(REPLACE(%s, ' ', ''), ':', '')
                   RETURNING id""",
                (is_number, is_number),
            )
            deleted = cur.fetchone()
            if not deleted:
                raise HTTPException(404, "Not found in saved list")
    finally:
        conn.close()

    return {"message": "Removed from saved"}


# ── Departments ──
@router.get("/departments")
def get_departments():
    conn = database.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, officer_name, designation FROM departments ORDER BY id ASC")
            rows = cur.fetchall()
    finally:
        conn.close()

    return [
        {
            "id": r["id"],
            "name": r["name"],
            "officer_name": r.get("officer_name"),
            "designation": r.get("designation"),
        }
        for r in rows
    ]


# ── Dashboard Trends ──
@router.get("/dashboard/trends")
def get_dashboard_trends():
    conn = database.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT DATE(created_at) AS search_date, COUNT(*) AS count
                   FROM search_logs
                   WHERE created_at >= CURRENT_DATE - INTERVAL '6 days'
                   GROUP BY DATE(created_at)
                   ORDER BY search_date ASC"""
            )
            daily_rows = cur.fetchall()

            cur.execute(
                """SELECT s.category, COUNT(*) AS count
                   FROM search_logs sl
                   JOIN standards s ON (
                       sl.top_result_is_number = s.is_number
                       OR REPLACE(REPLACE(sl.top_result_is_number, ' ', ''), ':', '') = REPLACE(REPLACE(s.is_number, ' ', ''), ':', '')
                   )
                   WHERE s.category IS NOT NULL
                   GROUP BY s.category
                   ORDER BY count DESC
                   LIMIT 5"""
            )
            cat_rows = cur.fetchall()
    finally:
        conn.close()

    daily_dict = {str(r["search_date"]): r["count"] for r in daily_rows}
    today = datetime.now().date()
    searches_per_day = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        d_str = str(d)
        searches_per_day.append({
            "date": d_str,
            "day": d.strftime("%a"),
            "count": daily_dict.get(d_str, 0),
        })

    top_categories = [
        {"category": r["category"], "count": r["count"]}
        for r in cat_rows
    ]

    return {
        "searches_per_day": searches_per_day,
        "top_categories": top_categories,
    }


# ── POST /api/reviews ──
@router.post("/reviews")
def create_review(req: ReviewCreate):
    if req.decision not in ("accept", "reject", "flag"):
        raise HTTPException(400, "decision must be accept, reject, or flag")
    conn = database.get_connection()
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO reviews (request_id, is_number, decision) VALUES (%s,%s,%s) RETURNING *",
                (req.request_id, req.is_number, req.decision),
            )
            row = cur.fetchone()
    finally:
        conn.close()
    return dict(row)


# ── GET /api/reviews/{request_id} ──
@router.get("/reviews/{request_id}")
def get_reviews(request_id: str):
    conn = database.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT request_id, is_number, decision, reviewed_at FROM reviews WHERE request_id = %s ORDER BY id",
                (request_id,),
            )
            rows = cur.fetchall()
    finally:
        conn.close()
    return {"request_id": request_id, "reviews": [dict(r) for r in rows]}


# ── Exporting ──
def _export_single_standard(standard: dict) -> str:
    lines = [
        "═" * 60,
        "BUREAU OF INDIAN STANDARDS",
        "Standard Reference Document",
        "═" * 60,
        "",
        f"IS Number:          {standard['is_number']}",
        f"Title:              {standard['title']}",
    ]
    if standard.get("category"):
        lines.append(f"Category:           {standard['category']}")
    if standard.get("sub_category"):
        lines.append(f"Sub-Category:       {standard['sub_category']}")
    if standard.get("version"):
        lines.append(f"Version:            {standard['version']}")
    if standard.get("last_amended"):
        lines.append(f"Last Amended:       {standard['last_amended']}")
    lines.extend([
        "",
        "─" * 60,
        "SCOPE",
        "─" * 60,
        standard.get("scope") or "N/A",
        "",
        "─" * 60,
        "QCO STATUS",
        "─" * 60,
        f"Mandatory Certification: {'YES' if standard.get('is_qco_mandatory') else 'NO'}",
    ])
    if standard.get("qco_enforcement_date"):
        lines.append(f"Enforcement Date:        {standard['qco_enforcement_date']}")
    if standard.get("is_qco_mandatory"):
        lines.append("Certification Body:      Bureau of Indian Standards (BIS)")
        lines.append("Scheme:                  Compulsory Registration Scheme (CRS)")
    lines.extend([
        "",
        "─" * 60,
        "SPECIFICATIONS",
        "─" * 60,
    ])
    specs = standard.get("specifications") or {}
    if specs:
        for k, v in specs.items():
            label = k.replace("_", " ").title()
            lines.append(f"  {label:<30} {v}")
    else:
        lines.append("  None specified")
    lines.extend([
        "",
        "─" * 60,
        "NORMATIVE REFERENCES",
        "─" * 60,
    ])
    refs = standard.get("normative_references") or []
    if refs:
        for ref in refs:
            lines.append(f"  {ref}")
    else:
        lines.append("  None specified")
    lines.extend([
        "",
        "─" * 60,
        "AMENDMENT HISTORY",
        "─" * 60,
    ])
    amends = standard.get("amendment_history") or []
    if amends:
        for amd in amends:
            if isinstance(amd, dict):
                lines.append(f"  {amd.get('amendment_number', '')} ({amd.get('date', '')}): {amd.get('description', '')}")
    else:
        lines.append("  None specified")
    lines.extend([
        "",
        "═" * 60,
        f"Generated on: {datetime.now().strftime('%d %B %Y')}",
        "Source: BIS Standards Intelligence Engine",
        "═" * 60,
    ])
    return "\n".join(lines)


def _export_request_reviews(request_id: str) -> str:
    conn = database.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT is_number FROM reviews WHERE request_id = %s AND decision = 'accept'", (request_id,)
            )
            accepted = [row["is_number"] for row in cur.fetchall()]
    finally:
        conn.close()

    lines = ["═" * 60]
    lines.append("MANAK-AI — TENDER-READY STANDARDS REFERENCE BLOCK")
    lines.append("Recommendation engine for Indian Standards in procurement")
    lines.append("═" * 60)
    lines.append("")
    lines.append(f"Request ID: {request_id}")
    lines.append(f"Generated:  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")
    lines.append("NOTE: AI-assisted recommendations — verify all references before use.")
    lines.append("")

    if not accepted:
        lines.append("No accepted standards recorded for this request.")
        lines.append("")
        return "\n".join(lines)

    for idx, is_num in enumerate(accepted, start=1):
        row = _get_standard_by_number(is_num)
        if not row:
            continue
        lines.append("─" * 60)
        lines.append(f"{idx}. {row['is_number']} — {row['title']}")
        lines.append("─" * 60)
        lines.append(f"   Category:      {row['category']}")
        lines.append(f"   Sub-category:  {row['sub_category'] or 'N/A'}")
        lines.append(f"   Version:       {row['version'] or 'N/A'}")
        lines.append(f"   Last amended:  {row['last_amended'] or 'N/A'}")
        lines.append("")
        lines.append("   SCOPE:")
        lines.append("   " + (row['scope'] or 'N/A').replace("\n", "\n   "))
        lines.append("")
        lines.append(f"   QCO mandatory: {'YES' if row['is_qco_mandatory'] else 'NO'}")
        if row.get("qco_enforcement_date"):
            lines.append(f"   Enforcement:   {row['qco_enforcement_date']}")
        lines.append("")

    lines.append("═" * 60)
    return "\n".join(lines)


# Explicit route for GeM payload export
@router.post("/export/gem-payload/{is_number}")
def export_gem_payload(is_number: str):
    std = _get_standard_by_number(is_number)
    if not std:
        raise HTTPException(404, "Standard not found")

    gem_payload = {
        "schema_version": "2.1",
        "timestamp": datetime.now().isoformat(),
        "source_system": "BIS_MANAK_AI",
        "tender_parameters": {
            "category_name": std.get("category"),
            "item_name": std.get("title"),
            "reference_standard": std.get("is_number"),
            "compliance_required": True,
            "mandatory_certification": {
                "agency": "BIS",
                "scheme": "CRS",
                "qco_applicable": True,
            } if std.get("is_qco_mandatory") else {
                "qco_applicable": False,
            },
            "specifications": std.get("specifications") or {},
            "testing_requirements": [],
        },
    }
    return gem_payload


# Dual-purpose export route: handles single standard export (if standard exists)
# OR request-based accepted-standards tender reference block.
@router.post("/export/{identifier}", response_class=PlainTextResponse)
def export(identifier: str):
    std = _get_standard_by_number(identifier)
    if std:
        text = _export_single_standard(std)
        filename = f"{std['is_number'].replace(' ', '_').replace(':', '_')}_reference.txt"
        return PlainTextResponse(
            text,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    return _export_request_reviews(identifier)


# ── GET /api/dashboard/stats ──
@router.get("/dashboard/stats")
def dashboard_stats():
    conn = database.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS c FROM standards")
            std_count = cur.fetchone()["c"]

            cur.execute("SELECT COUNT(*) AS c FROM certification_rules")
            qco_rules_count = cur.fetchone()["c"]

            cur.execute(
                """SELECT COUNT(*) AS c FROM certification_rules
                   WHERE enforcement_date IS NOT NULL
                     AND enforcement_date >= CURRENT_DATE
                     AND enforcement_date <= (CURRENT_DATE + INTERVAL '30 days')"""
            )
            qco_30 = cur.fetchone()["c"]
            cur.execute(
                """SELECT product_name, applicable_is_number, enforcement_date
                   FROM certification_rules
                   WHERE enforcement_date IS NOT NULL
                     AND enforcement_date >= CURRENT_DATE
                     AND enforcement_date <= (CURRENT_DATE + INTERVAL '30 days')
                   ORDER BY enforcement_date"""
            )
            details = cur.fetchall()

            cur.execute("SELECT COUNT(*) AS c FROM saved_items")
            saved_row = cur.fetchone()
            saved_count = saved_row["c"] if saved_row else 0

            cur.execute(
                """SELECT COUNT(*) AS c FROM search_logs
                   WHERE created_at >= date_trunc('month', CURRENT_DATE)"""
            )
            search_row = cur.fetchone()
            searches_month = search_row["c"] if search_row else 0
    finally:
        conn.close()

    total_session = get_search_count()
    deadline_details = [
        {
            "product_name": d["product_name"],
            "applicable_is_number": d["applicable_is_number"],
            "enforcement_date": str(d["enforcement_date"]),
        }
        for d in details
    ]

    return {
        # Original FastAPI response fields
        "total_searches_session": total_session,
        "total_standards": std_count,
        "total_qco_rules": qco_rules_count,
        "qco_deadlines_next_30d": qco_30,
        "qco_deadline_details": deadline_details,
        # Express parity fields
        "searchesThisMonth": max(searches_month, total_session),
        "standardsSaved": saved_count,
        "qcoRules": qco_rules_count,
        "qcoDeadlines": qco_30,
        "tendersInProgress": 5,
        "qcoDeadlineDetails": deadline_details,
    }


@router.post("/chat")
def chat(req: ChatRequest):
    message = (req.message or "").strip()
    if not message:
        raise HTTPException(400, "Message is required")

    history = req.history or []
    lang = (req.lang or "en").lower()
    return handle_chat(message, req.sessionId, history, lang=lang)


