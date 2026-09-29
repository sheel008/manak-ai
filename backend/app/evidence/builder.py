"""Evidence construction, why-recommended synthesis and template-based explanation generation (no LLM)."""
from typing import Any, Dict, List, Optional


def build_evidence(standard: Dict[str, Any], matched_specs: List[Dict[str, Any]], overlapping_keywords: List[str]) -> Dict[str, Any]:
    """Build the evidence object from stored source_excerpt + matched values."""
    return {
        "source_excerpt": standard.get("source_excerpt") or "",
        "matched_specifications": matched_specs,
        "overlapping_keywords": overlapping_keywords,
    }


def generate_why_recommended(
    standard: Dict[str, Any],
    matched_specs: Optional[List[Dict[str, Any]]] = None,
    overlapping_keywords: Optional[List[str]] = None,
    similarity_score: float = 0.0,
    confidence: float = 0.0,
    query: Optional[str] = None,
    **kwargs: Any,
) -> str:
    """Generate concise, actionable explainability text for procurement officials."""
    reasons = []

    # 1. Spec overlap
    if matched_specs:
        spec_items = [
            m if isinstance(m, str) else f"{m.get('field', 'param')}: {m.get('value')}"
            for m in matched_specs[:3]
        ]
        reasons.append(f"Direct match with procurement parameters ({', '.join(spec_items)})")

    # 2. Keyword overlap
    if overlapping_keywords:
        reasons.append(f"Identified core technical domain keywords ({', '.join(overlapping_keywords[:3])})")

    # 3. Department and sector alignment
    dept = standard.get("department")
    sector = standard.get("sector")
    if dept:
        reasons.append(f"Aligned under BIS {dept} division ({sector or 'Standard Series'})")

    # 4. Mandatory QCO requirement
    if standard.get("is_qco_mandatory"):
        reasons.append("Statutory compliance: covered under mandatory Quality Control Order (QCO) requiring ISI mark")

    if not reasons:
        sim_pct = round(similarity_score if similarity_score > 1.0 else similarity_score * 100)
        reasons.append(f"Semantic vector search retrieved highest contextual similarity ({sim_pct}%) to technical scope")

    return "; ".join(reasons) + "."


def generate_explanation(
    standard: Dict[str, Any],
    matched_specs: List[Dict[str, Any]],
    overlapping_keywords: List[str],
    keyword_score: float,
    specification_score: float,
    similarity_score: float,
) -> str:
    """
    Generate plain template text grounded in the values that produced the match.
    matched_specs entries are {"value": raw, "field": key, "stored": "key: val"}.
    Never calls any external AI API.
    """
    parts = []

    # Values the query specified that matched this standard's specifications
    query_values = []
    for m in matched_specs:
        v = m.get("value")
        if v and v not in query_values:
            query_values.append(v)

    kw_values = overlapping_keywords[:4]

    if query_values:
        vals = ", ".join(query_values)
        parts.append(f"the query specified {vals} which are present in this standard's specifications")

    if kw_values and keyword_score >= 40:
        parts.append(f"with strong keyword overlap on {', '.join(kw_values)}")

    if not parts:
        # Fallback: rely on semantic similarity only
        sim_pct = round(similarity_score if similarity_score > 1.0 else similarity_score * 100)
        parts.append(
            f"this standard matched based on semantic similarity to the query "
            f"(score {sim_pct}%) without specific keyword or specification overlap"
        )

    if standard.get("is_qco_mandatory"):
        parts.append("the standard is under a mandatory QCO requiring BIS certification")

    explanation = parts[0][0].upper() + parts[0][1:]
    if len(parts) > 1:
        explanation += ", and " + ", ".join(parts[1:])
    explanation += "."
    return explanation
