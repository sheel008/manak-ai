"""Vector search engine combining precomputed in-memory embeddings and pgvector.

Pipeline:
Query -> Embedding -> Vector Search (528 standards) -> Top-20 candidates -> Reranker -> Top-5 -> Evidence Builder

Features:
- Preloads backend/data/embeddings.json and standards.json once into memory.
- Fast numpy matrix cosine similarity (< 5ms latency).
- Database pgvector fallback/hybrid execution.
- Query vector caching with LRU cache.
- Department and category pre-filtering support.
"""

from functools import lru_cache
import json
import os
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from app.core import config, database
from app.services import embedding
from app.rules import certification as cert_rules

# In-memory storage for high-speed vector retrieval
_IS_INITIALIZED = False
_STANDARDS_CACHE: List[Dict[str, Any]] = []
_STANDARDS_BY_IS: Dict[str, Dict[str, Any]] = {}
_VECTORS_MATRIX: Optional[np.ndarray] = None
_STANDARDS_ORDER: List[Dict[str, Any]] = []
_VECTORS_BY_IS: Dict[str, List[float]] = {}


def load_embeddings_cache(force: bool = False) -> Dict[str, List[float]]:
    """Load precomputed embeddings and standards metadata into memory once."""
    global _IS_INITIALIZED, _STANDARDS_CACHE, _STANDARDS_BY_IS, _VECTORS_MATRIX, _STANDARDS_ORDER, _VECTORS_BY_IS

    if _IS_INITIALIZED and not force:
        return _VECTORS_BY_IS

    # 1. Load standards metadata
    if os.path.exists(config.STANDARDS_FILE):
        with open(config.STANDARDS_FILE, "r", encoding="utf-8") as f:
            _STANDARDS_CACHE = json.load(f)
        _STANDARDS_BY_IS = {s["is_number"]: s for s in _STANDARDS_CACHE}

    # 2. Load precomputed embeddings
    if os.path.exists(config.EMBEDDINGS_FILE):
        with open(config.EMBEDDINGS_FILE, "r", encoding="utf-8") as f:
            emb_payload = json.load(f)

        vectors_map = emb_payload.get("vectors") or {}
        if not vectors_map and "items" in emb_payload:
            for item in emb_payload["items"]:
                vectors_map[item["is_number"]] = item

        ordered_standards = []
        ordered_vectors = []

        for s in _STANDARDS_CACHE:
            num = s["is_number"]
            emb_entry = vectors_map.get(num)
            if emb_entry and "vector" in emb_entry and len(emb_entry["vector"]) == config.EMBEDDING_DIM:
                ordered_standards.append(s)
                ordered_vectors.append(emb_entry["vector"])

        if ordered_vectors:
            _VECTORS_MATRIX = np.array(ordered_vectors, dtype=np.float32)
            # Ensure vectors are normalized
            norms = np.linalg.norm(_VECTORS_MATRIX, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            _VECTORS_MATRIX = _VECTORS_MATRIX / norms
            _STANDARDS_ORDER = ordered_standards
            _VECTORS_BY_IS = {s["is_number"]: v for s, v in zip(ordered_standards, ordered_vectors)}

    _IS_INITIALIZED = True
    return _VECTORS_BY_IS


# Preload on import
try:
    load_embeddings_cache()
except Exception:
    pass


@lru_cache(maxsize=1024)
def _cached_embed_query(query_text: str) -> Tuple[float, ...]:
    """LRU cache for embedded query vectors."""
    vec = embedding.embed_query(query_text)
    return tuple(vec)


def matches_sector(query_sector: Optional[str], standard_sector: Optional[str]) -> bool:
    """Check if standard's sector matches query_sector using exact, substring, and token overlap."""
    if not query_sector:
        return True
    if not standard_sector:
        return False
    q = query_sector.lower().strip()
    s = standard_sector.lower().strip()
    if q == s or q in s or s in q:
        return True
    # Stop words to ignore during token overlap
    stops = {"&", "and", "or", "in", "of", "for", "the", "to", "a", "an"}
    import re
    q_words = set(re.findall(r"\b\w+\b", q)) - stops
    s_words = set(re.findall(r"\b\w+\b", s)) - stops
    if bool(q_words & s_words):
        return True
    # Domain mappings (e.g. Heavy Industry -> Metals & Mining, Industrial Machinery)
    if "heavy" in q and ("metals" in s or "machinery" in s or "mining" in s):
        return True
    return False


def in_memory_vector_search(
    query_text: str = None,
    top_k: int = 20,
    department: Optional[str] = None,
    category: Optional[str] = None,
    sector: Optional[str] = None,
    qco_required: Optional[bool] = None,
    query: Optional[str] = None,
    **kwargs,
) -> List[Dict[str, Any]]:
    """Perform in-memory matrix cosine similarity across precomputed embeddings."""
    load_embeddings_cache()
    query_text = query_text or query or ""

    if _VECTORS_MATRIX is None or len(_STANDARDS_ORDER) == 0:
        return []

    # Get normalized query vector
    q_tuple = _cached_embed_query(query_text)
    q_vec = np.array(q_tuple, dtype=np.float32)
    q_norm = np.linalg.norm(q_vec)
    if q_norm > 0:
        q_vec = q_vec / q_norm

    # Dot product gives cosine similarity
    similarities = np.dot(_VECTORS_MATRIX, q_vec)

    # Filter indices if department, category, sector, or qco_required filter is active
    filtered_indices = []
    dep_lower = department.lower().strip() if department else None
    cat_lower = category.lower().strip() if category else None
    sec_filter = sector.strip() if sector else None

    for i, s in enumerate(_STANDARDS_ORDER):
        if dep_lower:
            s_dep = (s.get("department") or "").lower()
            if dep_lower not in s_dep and s_dep not in dep_lower:
                continue
        if cat_lower:
            s_cat = (s.get("category") or "").lower()
            if cat_lower not in s_cat and s_cat not in cat_lower:
                continue
        if sec_filter:
            s_sec = s.get("sector") or ""
            if not matches_sector(sec_filter, s_sec):
                continue
        if qco_required:
            if not cert_rules.is_qco_applicable(s):
                continue
        filtered_indices.append(i)

    # If an active filter was requested but produced 0 matches, return empty (do NOT fallback to all standards)
    has_active_filter = bool(dep_lower or cat_lower or sec_filter or qco_required)
    if has_active_filter and not filtered_indices:
        return []

    if not filtered_indices:
        filtered_indices = list(range(len(_STANDARDS_ORDER)))

    # Sort candidates by similarity descending
    scored = [(idx, float(similarities[idx])) for idx in filtered_indices]
    scored.sort(key=lambda x: x[1], reverse=True)

    results = []
    for idx, sim in scored[:top_k]:
        row = dict(_STANDARDS_ORDER[idx])
        row["similarity"] = round(sim, 4)
        results.append(row)

    return results


def vector_search(
    query_text: str = None,
    top_k: int = None,
    department: Optional[str] = None,
    category: Optional[str] = None,
    sector: Optional[str] = None,
    qco_required: Optional[bool] = None,
    query: Optional[str] = None,
    **kwargs,
) -> List[Dict[str, Any]]:
    """Embed query and return top_k candidates by cosine similarity.

    Tries pgvector database first if connected, populated, and applicable;
    Smoothly falls back to in-memory precomputed vectors.
    """
    query_text = (query_text or query or "").strip()
    top_k = top_k or config.VECTOR_TOP_K
    if not query_text:
        return []

    try:
        conn = database.get_connection()
        try:
            with conn.cursor() as cur:
                # Test if table has rows and has been aligned
                cur.execute("SELECT COUNT(*) AS c FROM standards")
                cnt_row = cur.fetchone()
                if cnt_row and (cnt_row.get("c") or 0) > 0:
                    query_vec = list(_cached_embed_query(query_text))
                    where_clause = ""
                    where_params = []
                    has_active_filter = bool(department or category or sector or qco_required)

                    if department:
                        where_clause += " AND LOWER(department) LIKE %s"
                        where_params.append(f"%{department.lower()}%")
                    if category:
                        where_clause += " AND LOWER(category) LIKE %s"
                        where_params.append(f"%{category.lower()}%")
                    if qco_required:
                        where_clause += " AND (is_qco_mandatory = TRUE OR qco_required = TRUE)"
                    if sector:
                        import re
                        stops = {"&", "and", "or", "in", "of", "for", "the", "to", "a", "an"}
                        words = [w for w in re.findall(r"\b\w+\b", sector.lower()) if w not in stops]
                        sec_parts = ["LOWER(sector) LIKE %s" for _ in words]
                        if "heavy" in sector.lower():
                            sec_parts.append("(LOWER(sector) LIKE '%metals%' OR LOWER(sector) LIKE '%machinery%' OR LOWER(sector) LIKE '%mining%')")
                        if sec_parts:
                            where_clause += f" AND ({' OR '.join(sec_parts)})"
                            for w in words:
                                where_params.append(f"%{w}%")
                        else:
                            where_clause += " AND LOWER(sector) LIKE %s"
                            where_params.append(f"%{sector.lower().strip()}%")

                    params = [query_vec] + where_params + [query_vec, top_k]

                    cur.execute(
                        f"""
                        SELECT
                          is_number, title, category, sub_category, scope,
                          specifications, normative_references, is_qco_mandatory,
                          qco_enforcement_date, version, last_amended,
                          amendment_history, source_excerpt,
                          department, sector, qco_required, search_weight_boost,
                          keywords, description, status, source, provenance,
                          related_standards, revision_year, international_equivalent, title_hindi,
                          1 - (embedding <=> %s::vector) AS similarity
                        FROM standards
                        WHERE 1=1 {where_clause}
                        ORDER BY embedding <=> %s::vector
                        LIMIT %s
                        """,
                        tuple(params),
                    )
                    rows = cur.fetchall()
                    if rows:
                        for r in rows:
                            r["similarity"] = round(float(r["similarity"]), 4)
                        return rows
                    elif has_active_filter:
                        return []
        finally:
            conn.close()
    except Exception:
        # DB not available, mocked, or error: use in-memory precomputed vector search
        pass

    return in_memory_vector_search(
        query_text,
        top_k=top_k,
        department=department,
        category=category,
        sector=sector,
        qco_required=qco_required,
    )
