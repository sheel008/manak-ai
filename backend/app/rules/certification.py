"""Deterministic certification-rule lookup and QCO mapping integration."""
import json
import os
from typing import Any, Dict, List, Optional

from app.core import config, database

_QCO_CACHE: Optional[List[Dict[str, Any]]] = None
_QCO_BY_IS: Dict[str, Dict[str, Any]] = {}


def _load_qco_data():
    global _QCO_CACHE, _QCO_BY_IS
    if _QCO_CACHE is not None:
        return

    _QCO_CACHE = []
    _QCO_BY_IS = {}

    # Prefer qco_mapping.json if available
    qco_file = getattr(config, "QCO_MAPPING_FILE", None) or os.path.join(config.DATA_DIR, "qco_mapping.json")
    if os.path.exists(qco_file):
        try:
            with open(qco_file, "r", encoding="utf-8") as f:
                _QCO_CACHE = json.load(f)
            for it in _QCO_CACHE:
                std_num = it.get("mandatory_standard") or it.get("applicable_is_number")
                if std_num:
                    _QCO_BY_IS[std_num] = it
                    _QCO_BY_IS[std_num.upper()] = it
                    _QCO_BY_IS[std_num.replace(" ", "").replace(":", "").upper()] = it
                    root = std_num.split(":")[0].strip()
                    _QCO_BY_IS[root] = it
                    _QCO_BY_IS[root.upper()] = it
                    _QCO_BY_IS[root.replace(" ", "").upper()] = it
        except Exception:
            pass

    # Fallback / merge with certification_rules.json
    if os.path.exists(config.CERTIFICATION_RULES_FILE):
        try:
            with open(config.CERTIFICATION_RULES_FILE, "r", encoding="utf-8") as f:
                rules = json.load(f)
                if not _QCO_CACHE:
                    _QCO_CACHE = rules
                for r in rules:
                    num = r.get("applicable_is_number") or r.get("mandatory_standard")
                    if num:
                        _QCO_BY_IS[num] = r
                        _QCO_BY_IS[num.upper()] = r
                        _QCO_BY_IS[num.replace(" ", "").replace(":", "").upper()] = r
                        root = num.split(":")[0].strip()
                        _QCO_BY_IS[root] = r
                        _QCO_BY_IS[root.upper()] = r
                        _QCO_BY_IS[root.replace(" ", "").upper()] = r
        except Exception:
            pass


def get_qco_details(is_number: str) -> Optional[Dict[str, Any]]:
    """Lookup statutory QCO order metadata for a given IS number."""
    _load_qco_data()
    if not is_number:
        return None
    clean = is_number.replace(" ", "").replace(":", "").upper()
    root = is_number.split(":")[0].strip()
    root_clean = root.replace(" ", "").upper()

    res = (
        _QCO_BY_IS.get(is_number)
        or _QCO_BY_IS.get(clean)
        or _QCO_BY_IS.get(root)
        or _QCO_BY_IS.get(root_clean)
        or _QCO_BY_IS.get(is_number.upper())
    )
    if res:
        normalized = dict(res)
        if "mandatory" not in normalized:
            normalized["mandatory"] = bool(normalized.get("is_qco_mandatory", True))
        if "product" not in normalized:
            normalized["product"] = normalized.get("product_name", "")
        if "mandatory_standard" not in normalized:
            normalized["mandatory_standard"] = normalized.get("applicable_is_number", is_number)
        return normalized

    # Check standards.json for QCO flag
    stds_file = getattr(config, "STANDARDS_FILE", None) or os.path.join(config.DATA_DIR, "standards.json")
    if os.path.exists(stds_file):
        try:
            with open(stds_file, "r", encoding="utf-8") as f:
                stds = json.load(f)
            for s in stds:
                if s.get("is_number") == is_number or s.get("is_number", "").split(":")[0] == root:
                    if s.get("is_qco_mandatory") or s.get("qco_required"):
                        return {
                            "product": s.get("title"),
                            "mandatory_standard": s.get("is_number"),
                            "qco_name": f"{s.get('title')} (Quality Control) Order",
                            "ministry": "Ministry of Commerce and Industry / Line Ministry",
                            "effective_date": s.get("qco_enforcement_date") or "2023-01-01",
                            "mandatory": True,
                            "remarks": f"Compulsory BIS certification mark (ISI Mark) mandated under Section 16 of the BIS Act, 2016 for {s.get('is_number')}."
                        }
        except Exception:
            pass

    return None


def lookup_product(product_name: str) -> Optional[Dict[str, Any]]:
    """
    Match a product name (or its substring) against certification_rules by
    product_name and aliases. Fully deterministic.
    """
    query = (product_name or "").strip().lower()
    if not query:
        return None

    # Try database first
    rows = []
    try:
        conn = database.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM certification_rules ORDER BY id")
                rows = cur.fetchall()
        finally:
            conn.close()
    except Exception:
        pass

    # In-memory fallback
    if not rows:
        _load_qco_data()
        rows = _QCO_CACHE or []

    for row in rows:
        name = (row.get("product_name") or row.get("product") or "").lower()
        aliases = [a.lower() for a in (row.get("aliases") or [])]
        all_terms = [name] + aliases
        # Direct contains match either direction
        for term in all_terms:
            if term and (term in query or query in term):
                return {
                    "product_name": row.get("product_name") or row.get("product"),
                    "aliases": row.get("aliases", []),
                    "is_qco_mandatory": bool(row.get("is_qco_mandatory", row.get("mandatory", True))),
                    "applicable_is_number": row.get("applicable_is_number") or row.get("mandatory_standard"),
                    "enforcement_date": row.get("enforcement_date") or row.get("effective_date"),
                }
        # Fuzzy: most query words appear in the name/aliases combined text
        query_words = [w for w in query.split() if len(w) > 2]
        if query_words:
            combined = " ".join(all_terms)
            hits = [w for w in query_words if w in combined]
            if len(hits) >= max(1, int(len(query_words) * 0.6)):
                return {
                    "product_name": row.get("product_name") or row.get("product"),
                    "aliases": row.get("aliases", []),
                    "is_qco_mandatory": bool(row.get("is_qco_mandatory", row.get("mandatory", True))),
                    "applicable_is_number": row.get("applicable_is_number") or row.get("mandatory_standard"),
                    "enforcement_date": row.get("enforcement_date") or row.get("effective_date"),
                }
    return None


def is_qco_applicable(standard: Optional[Dict[str, Any]] = None, is_number: Optional[str] = None) -> bool:
    """Canonical determination of whether a standard is subject to mandatory QCO certification.

    Checks:
      1. standard metadata flag `is_qco_mandatory`
      2. standard metadata flag `qco_required`
      3. canonical certification rules mapping via get_qco_details(is_number)
    """
    if standard:
        if bool(standard.get("is_qco_mandatory")) or bool(standard.get("qco_required")):
            return True
        is_num = standard.get("is_number") or is_number
    else:
        is_num = is_number

    if is_num:
        details = get_qco_details(is_num)
        if details and bool(details.get("mandatory")):
            return True

    return False
