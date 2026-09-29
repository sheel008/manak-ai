"""Resolve normative references and compute related standards using DB or related_standards.json graph."""
import json
import os
from typing import Any, Dict, List

from app.core import config, database

_RELATED_GRAPH: Dict[str, Any] = {}
_STANDARDS_MAP: Dict[str, Any] = {}


def _load_related_data():
    global _RELATED_GRAPH, _STANDARDS_MAP
    if _RELATED_GRAPH:
        return

    rel_file = getattr(config, "RELATED_STANDARDS_FILE", None) or os.path.join(config.DATA_DIR, "related_standards.json")
    if os.path.exists(rel_file):
        try:
            with open(rel_file, "r", encoding="utf-8") as f:
                _RELATED_GRAPH = json.load(f)
        except Exception:
            pass

    if os.path.exists(config.STANDARDS_FILE):
        try:
            with open(config.STANDARDS_FILE, "r", encoding="utf-8") as f:
                stds = json.load(f)
                _STANDARDS_MAP = {s["is_number"]: s for s in stds}
                # Also strip spaces
                for s in stds:
                    _STANDARDS_MAP[s["is_number"].replace(" ", "").replace(":", "")] = s
        except Exception:
            pass


def resolve_references(is_numbers):
    """Return [ {is_number,title,category} ] for each referenced standard number."""
    if not is_numbers:
        return []

    _load_related_data()

    # Try DB query first
    try:
        conn = database.get_connection()
        try:
            result = []
            for num in is_numbers:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT is_number, title, category FROM standards WHERE is_number = %s",
                        (num,),
                    )
                    row = cur.fetchone()
                if row:
                    result.append({"is_number": row["is_number"], "title": row["title"], "category": row["category"]})
                else:
                    std = _STANDARDS_MAP.get(num) or _STANDARDS_MAP.get(num.replace(" ", "").replace(":", ""))
                    if std:
                        result.append({"is_number": std["is_number"], "title": std["title"], "category": std["category"]})
                    else:
                        result.append({"is_number": num, "title": None, "category": None})
            return result
        finally:
            conn.close()
    except Exception:
        # In-memory resolution
        result = []
        for num in is_numbers:
            std = _STANDARDS_MAP.get(num) or _STANDARDS_MAP.get(num.replace(" ", "").replace(":", ""))
            if std:
                result.append({"is_number": std["is_number"], "title": std["title"], "category": std["category"]})
            else:
                result.append({"is_number": num, "title": None, "category": None})
        return result


def compute_related_standards(is_number, limit=5):
    """
    Other standards that share at least one normative reference with this standard.
    Real SQL query against the data, with in-memory graph fallback.
    """
    _load_related_data()

    def _relation_type(title):
        t = (title or "").lower()
        if any(w in t for w in ("test", "method", "determination", "measurement", "sampling")):
            return "TESTING_RELATED"
        if any(w in t for w in ("safe", "protect", "fire", "hazard", "security")):
            return "SAFETY_RELATED"
        if any(w in t for w in ("install", "practice", "wiring", "guide", "erection")):
            return "INSTALLATION_RELATED"
        if any(w in t for w in ("term", "glossary", "vocab", "definition")):
            return "TERMINOLOGY_RELATED"
        return "GENERAL_RELATED"

    # Try DB query first
    try:
        conn = database.get_connection()
        try:
            with conn.cursor() as cur:
                # Get this standard's references
                cur.execute("SELECT normative_references FROM standards WHERE is_number = %s", (is_number,))
                self_row = cur.fetchone()
                if self_row:
                    self_refs = set(self_row["normative_references"] or [])
                    cur.execute("SELECT is_number, title, category, normative_references FROM standards WHERE is_number <> %s", (is_number,))
                    rows = cur.fetchall()

                    related = []
                    for row in rows:
                        refs = set(row["normative_references"] or [])
                        shared = refs & self_refs
                        if is_number in refs or row["is_number"] in self_refs:
                            shared = shared | {is_number}
                        if shared:
                            related.append({
                                "is_number": row["is_number"],
                                "title": row["title"],
                                "category": row["category"],
                                "shared_references": sorted(shared),
                            })
                    related.sort(key=lambda r: len(r["shared_references"]), reverse=True)
                    if related:
                        return [
                            {
                                "is_number": r["is_number"],
                                "title": r["title"],
                                "category": r["category"],
                                "relation_type": _relation_type(r["title"]),
                                "shared_references": r["shared_references"],
                            }
                            for r in related[:limit]
                        ]
        finally:
            conn.close()
    except Exception:
        pass

    # Use precomputed related_standards.json graph
    graph_entries = _RELATED_GRAPH.get(is_number) or _RELATED_GRAPH.get(is_number.replace(" ", "").replace(":", "")) or []
    if graph_entries:
        results = []
        for g in graph_entries[:limit]:
            results.append({
                "is_number": g["is_number"],
                "title": g.get("title"),
                "category": g.get("category"),
                "relation_type": _relation_type(g.get("title", "")),
                "shared_references": [is_number],
            })
        return results

    # Fallback to standards map
    self_std = _STANDARDS_MAP.get(is_number)
    if self_std:
        refs = self_std.get("normative_references") or self_std.get("related_standards") or []
        res = []
        for r in refs[:limit]:
            match = _STANDARDS_MAP.get(r)
            res.append({
                "is_number": r,
                "title": match["title"] if match else f"Standard {r}",
                "category": match["category"] if match else self_std.get("category"),
                "relation_type": _relation_type(match["title"] if match else ""),
                "shared_references": [r],
            })
        return res

    return []


# Alias for backward and forward compatibility
get_related_standards = compute_related_standards

