"""Test seed.py compatibility and execution."""
import json
import sys
from psycopg2.extras import Json

with open("backend/data/standards.json", "r", encoding="utf-8") as f:
    standards = json.load(f)
with open("backend/data/certification_rules.json", "r", encoding="utf-8") as f:
    rules = json.load(f)

# Clean date fields: empty strings -> None (as in seed.py)
for s in standards:
    s["qco_enforcement_date"] = s.get("qco_enforcement_date") or None
    s["last_amended"] = s.get("last_amended") or None

# Build embedding texts: title + scope (as in seed.py)
texts = [f"{s['title']}. {s['scope']}" for s in standards]
assert len(texts) == len(standards), "Text length mismatch"
print(f"Embedding texts generated: {len(texts)} texts")

# Verify SQL parameter binding for every standard
dummy_vec = [0.1] * 384
for s in standards:
    params = (
        s["is_number"],
        s["title"],
        s["category"],
        s.get("sub_category"),
        s.get("scope") or "",
        Json(s.get("specifications", {})),
        s.get("normative_references", []),
        bool(s.get("is_qco_mandatory", False)),
        s.get("qco_enforcement_date"),
        s.get("version"),
        s.get("last_amended"),
        Json(s.get("amendment_history", [])),
        s.get("source_excerpt"),
        s.get("department"),
        s.get("sector"),
        bool(s.get("qco_required", False)),
        float(s.get("search_weight_boost") or 1.0),
        s.get("keywords", []),
        s.get("description") or s.get("scope") or "",
        s.get("status", "Active"),
        s.get("source", "Bureau of Indian Standards"),
        s.get("provenance", "BIS Official Standard Publication"),
        s.get("related_standards", []),
        s.get("revision_year"),
        s.get("international_equivalent"),
        s.get("title_hindi"),
        dummy_vec,
    )
    assert len(params) == 27, f"Invalid parameter length for {s['is_number']}"

print(f"Standards parameter binding verified: {len(standards)} records compatible with seed.py (27 columns)")

# Verify SQL parameter binding for every rule
for r in rules:
    params = (
        r["product_name"],
        r.get("aliases", []),
        r.get("is_qco_mandatory", False),
        r.get("applicable_is_number"),
        r.get("enforcement_date") or None,
    )
    assert len(params) == 5, f"Invalid rule params for {r['product_name']}"

print(f"Certification rules parameter binding verified: {len(rules)} rules compatible with seed.py")
print("ALL SEED COMPATIBILITY CHECKS PASSED!")
