"""Offline Embedding Generation Pipeline.

Responsibilities:
- Reads backend/data/standards.json
- Generates 384-dimensional sentence embeddings using all-MiniLM-L6-v2
- Saves embeddings to backend/data/embeddings.json
- Stores: is_number, vector, checksum, generation timestamp
- Supports incremental updates: skips already-generated embeddings if checksum matches
- Never calls any external LLM or Gemini API
"""

import hashlib
import json
import os
import sys
import time
from datetime import datetime
from typing import Any, Dict, List

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
STANDARDS_FILE = os.path.join(DATA_DIR, "standards.json")
EMBEDDINGS_FILE = os.path.join(DATA_DIR, "embeddings.json")
MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384


def compute_checksum(standard: Dict[str, Any]) -> str:
    """Compute sha256 checksum over standard text fields that define its embedding."""
    raw = f"{standard.get('is_number', '')}|{standard.get('title', '')}|{standard.get('scope', '')}|{standard.get('category', '')}|{' '.join(standard.get('keywords', []))}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def build_embedding_text(standard: Dict[str, Any]) -> str:
    """Compose semantic representation for embedding."""
    title = standard.get("title", "")
    scope = standard.get("scope") or standard.get("description") or ""
    keywords = ", ".join(standard.get("keywords") or [])
    dept = standard.get("department", "")
    cat = standard.get("category", "")
    specs = standard.get("specifications") or {}
    spec_summary = ", ".join(f"{k}: {v}" for k, v in list(specs.items())[:5])
    return f"{standard.get('is_number', '')} {title}. Department: {dept}. Category: {cat}. Scope: {scope}. Key aspects: {keywords}. Specifications: {spec_summary}"


def generate_embeddings(force_recompute: bool = False):
    start_time = time.time()
    print("=" * 60)
    print("MANAK-AI: OFFLINE EMBEDDING GENERATION PIPELINE")
    print(f"Model: {MODEL_NAME} (Dimension: {EMBEDDING_DIM})")
    print("=" * 60)

    if not os.path.exists(STANDARDS_FILE):
        raise FileNotFoundError(f"Missing standards file: {STANDARDS_FILE}")

    with open(STANDARDS_FILE, "r", encoding="utf-8") as f:
        standards: List[Dict[str, Any]] = json.load(f)

    print(f"Loaded {len(standards)} standards from {STANDARDS_FILE}")

    # Load existing embeddings for incremental caching
    existing_store: Dict[str, Any] = {}
    if os.path.exists(EMBEDDINGS_FILE) and not force_recompute:
        try:
            with open(EMBEDDINGS_FILE, "r", encoding="utf-8") as f:
                old_data = json.load(f)
                if isinstance(old_data, dict):
                    existing_store = old_data.get("vectors") or {}
                    if not existing_store and "items" in old_data:
                        for it in old_data["items"]:
                            existing_store[it["is_number"]] = it
            print(f"Found existing cached embeddings: {len(existing_store)}")
        except Exception as e:
            print(f"Warning: Could not read existing embeddings ({e}). Generating fresh.")

    # Identify standards that need embedding
    to_embed = []
    to_embed_indices = []

    for idx, s in enumerate(standards):
        num = s["is_number"]
        csum = compute_checksum(s)
        cached = existing_store.get(num)
        if cached and cached.get("checksum") == csum and len(cached.get("vector") or []) == EMBEDDING_DIM:
            continue
        to_embed.append(s)
        to_embed_indices.append((idx, num, csum))

    print(f"Standards to embed (fresh or modified): {len(to_embed)}")
    print(f"Standards reused from cache: {len(standards) - len(to_embed)}")

    if to_embed:
        print(f"Loading SentenceTransformer('{MODEL_NAME}')...")
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(MODEL_NAME)
        print("✓ SentenceTransformer model ready")

        texts = [build_embedding_text(s) for s in to_embed]
        print(f"Generating vectors for {len(texts)} items...")
        vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=True)

        now_iso = datetime.now().isoformat()
        for (idx, num, csum), vec in zip(to_embed_indices, vectors):
            existing_store[num] = {
                "is_number": num,
                "vector": [round(float(v), 6) for v in vec],
                "checksum": csum,
                "generated_at": now_iso,
            }

    # Assemble output payload
    items_list = []
    for s in standards:
        num = s["is_number"]
        if num in existing_store:
            items_list.append(existing_store[num])

    output_payload = {
        "model": MODEL_NAME,
        "dimension": EMBEDDING_DIM,
        "total_standards": len(standards),
        "total_embeddings": len(items_list),
        "last_generated": datetime.now().isoformat(),
        "items": items_list,
        "standards": items_list,
        "vectors": existing_store,
    }

    with open(EMBEDDINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(output_payload, f, indent=2)

    elapsed = time.time() - start_time
    file_size_mb = os.path.getsize(EMBEDDINGS_FILE) / (1024 * 1024)
    print("\n" + "=" * 60)
    print("EMBEDDING GENERATION COMPLETE")
    print(f"Saved: {EMBEDDINGS_FILE}")
    print(f"Total Vectors: {len(items_list)} / {len(standards)}")
    print(f"Vector Dimension: {EMBEDDING_DIM}")
    print(f"File Size: {file_size_mb:.2f} MB")
    print(f"Elapsed Time: {elapsed:.2f} seconds")
    print("=" * 60)


if __name__ == "__main__":
    generate_embeddings()
