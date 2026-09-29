"""Full search pipeline: retrieve, rerank, enrich, build evidence, abstain."""
import uuid
from typing import Optional, List, Dict, Any

from app.core import config, database
from app.retrieval import vector_search, rerank
from app.rules import related as related_rules, certification as cert_rules
from app.evidence import builder as evidence_builder
from app.schemas import (
    SearchResponse, StandardResult, Evidence, NormativeReference,
    RelatedStandard, VersionInfo, Amendment,
)


def _version_info(row):
    history = []
    for a in (row.get("amendment_history") or []):
        if isinstance(a, dict):
            history.append(Amendment(
                amendment_number=a.get("amendment_number", ""),
                date=a.get("date", ""),
                description=a.get("description", ""),
            ))
    last = row.get("last_amended")
    return VersionInfo(
        version=row.get("version"),
        last_amended=str(last) if last else None,
        amendment_history=history,
    )


def _cert_info(row):
    qco_details = cert_rules.get_qco_details(row.get("is_number"))
    is_qco = cert_rules.is_qco_applicable(row)
    enf_date = str(row["qco_enforcement_date"]) if row.get("qco_enforcement_date") else (qco_details.get("effective_date") if qco_details else None)
    return {
        "status": "REQUIRED" if is_qco else "NOT_IDENTIFIED",
        "is_qco_mandatory": is_qco,
        "applicable_is_number": row.get("is_number"),
        "enforcement_date": enf_date,
        "scheme": "BIS Product Certification / CRS" if is_qco else None,
        "ministry": qco_details.get("ministry") if qco_details else None,
        "qco_name": qco_details.get("qco_name") if qco_details else None,
    }


def log_search(query: str, top_result_is_number: str = None, department: str = None, result_count: int = 0):
    """Log a successful (non-abstained) search to search_logs."""
    try:
        conn = database.get_connection()
        conn.autocommit = True
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO search_logs (query, top_result_is_number, department, result_count)
                       VALUES (%s, %s, %s, %s)""",
                    (
                        query,
                        top_result_is_number,
                        department or "Ministry of Commerce & Industry",
                        result_count,
                    ),
                )
        finally:
            conn.close()
    except Exception:
        # Logging failure should not disrupt the search response
        pass


def run_search(
    query_text: str,
    department: Optional[str] = None,
    category: Optional[str] = None,
    sector: Optional[str] = None,
    qco_required: Optional[bool] = None,
    top_k: Optional[int] = None,
    min_confidence: Optional[float] = None,
) -> SearchResponse:
    """
    Runs the whole pipeline and returns a SearchResponse.
    Supports department filtering, category filtering, sector filtering,
    QCO mandatory filtering, top_k overrides and minimum confidence thresholding.
    """
    request_id = uuid.uuid4().hex[:12]
    query_text = (query_text or "").strip()

    # 1. Vector retrieval (configurable K, default top 20 candidates for reranking)
    retrieval_k = max(20, (top_k or config.FINAL_TOP_K) * 4)
    try:
        candidates = vector_search.vector_search(
            query_text,
            top_k=retrieval_k,
            department=department,
            category=category,
            sector=sector,
            qco_required=qco_required,
        )
    except TypeError:
        try:
            candidates = vector_search.vector_search(
                query_text,
                top_k=retrieval_k,
                department=department,
                category=category,
            )
        except TypeError:
            candidates = vector_search.vector_search(query_text, top_k=retrieval_k)

    # Apply strict filter verification on retrieved candidates
    if sector:
        candidates = [c for c in candidates if vector_search.matches_sector(sector, c.get("sector"))]
    if qco_required:
        candidates = [c for c in candidates if cert_rules.is_qco_applicable(c)]

    if not candidates:
        return _abstain(request_id, query_text)

    query_tokens = rerank.tokenize(query_text)
    query_specs = rerank.extract_specs(query_text)

    # 2. Multi-signal deterministic reranking
    scored = []
    for c in candidates:
        kw_score = rerank.keyword_overlap_score(query_tokens, c)
        spec_score, matched = rerank.specification_match_score(query_specs, c)
        cat_score = rerank.category_overlap_score(query_tokens, c)
        dept_score = rerank.department_match_score(department, c)
        qco_score = rerank.qco_boost_score(c)
        rel_boost = rerank.related_standards_boost_score(c)

        final_score, sim_100 = rerank.multisignal_rerank_score(
            similarity=c["similarity"],
            keyword=kw_score,
            spec=spec_score,
            category=cat_score,
            department=dept_score,
            qco_boost=qco_score,
            related_boost=rel_boost,
        )

        # Boost if query explicitly specifies IS number or search weight boost
        boost = float(c.get("search_weight_boost") or 1.0)
        final_score = min(100.0, round(final_score * boost, 1))

        # Confidence percentage (0-100)
        confidence = final_score

        scored.append({
            "row": c,
            "sim": c["similarity"],
            "sim_100": sim_100,
            "kw": kw_score,
            "spec": spec_score,
            "cat": cat_score,
            "dept": dept_score,
            "qco": qco_score,
            "rel": rel_boost,
            "final": final_score,
            "confidence": confidence,
            "matched_specs": matched,
        })

    scored.sort(key=lambda s: s["final"], reverse=True)

    # 3. Abstention check
    if scored and scored[0]["final"] < config.ABSTAIN_THRESHOLD:
        return _abstain(request_id, query_text)

    # 4. Optional minimum confidence filter
    if min_confidence is not None:
        scored = [s for s in scored if s["confidence"] >= min_confidence]
        if not scored:
            return _abstain(request_id, query_text)

    # 5. Trim to top-k
    final_k = top_k or config.FINAL_TOP_K
    top = scored[:final_k]

    results = []
    for rank, item in enumerate(top, start=1):
        row = item["row"]
        # Related info
        resolved = related_rules.resolve_references(row.get("normative_references") or [])
        related = related_rules.compute_related_standards(row["is_number"], limit=5)
        # Overlapping keywords
        row_toks = set(rerank.tokenize(row["title"] + " " + (row.get("scope") or "")))
        overlapping = sorted(set(query_tokens) & row_toks)
        # Evidence + explanation + why recommended
        evidence = Evidence(
            source_excerpt=row.get("source_excerpt") or "",
            matched_specifications=item["matched_specs"],
            overlapping_keywords=overlapping,
        )
        explanation = evidence_builder.generate_explanation(
            row, item["matched_specs"], overlapping,
            item["kw"], item["spec"], item["sim"],
        )
        why_recommended = evidence_builder.generate_why_recommended(
            row, item["matched_specs"], overlapping,
            item["sim"], item["confidence"],
        )
        qco_details = cert_rules.get_qco_details(row["is_number"])

        results.append(StandardResult(
            rank=rank,
            is_number=row["is_number"],
            title=row["title"],
            category=row.get("category", "General"),
            sub_category=row.get("sub_category"),
            scope=row.get("scope") or row.get("description") or "",
            department=row.get("department"),
            sector=row.get("sector"),
            relevance_score=item["final"],
            confidence=item["confidence"],
            similarity_score=item["sim_100"],
            keyword_score=item["kw"],
            specification_score=item["spec"],
            department_score=item["dept"],
            is_qco_mandatory=cert_rules.is_qco_applicable(row),
            qco_required=cert_rules.is_qco_applicable(row),
            qco_enforcement_date=str(row["qco_enforcement_date"]) if row.get("qco_enforcement_date") else None,
            why_recommended=why_recommended,
            qco_info=qco_details,
            evidence=evidence,
            explanation=explanation,
            normative_references=[
                NormativeReference(**r) for r in resolved
            ],
            related_standards=[
                RelatedStandard(
                    is_number=r["is_number"],
                    title=r.get("title"),
                    category=r.get("category"),
                ) for r in related
            ],
            version_info=_version_info(row),
            certification=_cert_info(row),
        ))

    top_is_number = results[0].is_number if results else None
    log_search(
        query=query_text,
        top_result_is_number=top_is_number,
        department=department,
        result_count=len(results),
    )

    return SearchResponse(
        request_id=request_id,
        query=query_text,
        abstained=False,
        abstention_reason=None,
        results=results,
        threshold=config.ABSTAIN_THRESHOLD,
    )


def _abstain(request_id, query_text):
    return SearchResponse(
        request_id=request_id,
        query=query_text,
        abstained=True,
        abstention_reason=(
            "No confident match was found for this query against the available "
            "standards corpus. Manual research is recommended before referencing "
            "any standard in a tender specification."
        ),
        results=[],
        threshold=config.ABSTAIN_THRESHOLD,
    )


# Session counter for dashboard stats (total searches this session)
_search_count = {"n": 0}


def increment_search_count():
    _search_count["n"] += 1


def get_search_count():
    return _search_count["n"]
