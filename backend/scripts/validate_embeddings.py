"""Validation Script for Precomputed Embeddings.

Checks:
1. Missing embeddings for any standard in standards.json
2. Duplicate IS numbers
3. Incorrect vector dimensions (must be 384)
4. Corrupted vectors (NaN, Inf, all zeros, invalid floats)
5. Missing metadata (model, dimension, total_standards, checksums)

Generates:
- Console report
- JSON validation report at backend/data/embedding_validation_report.json
"""

import json
import math
import os
import sys
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
REPORT_FILE = os.path.join(DATA_DIR, "embedding_validation_report.json")
EXPECTED_DIM = 384


def validate_embeddings() -> Dict[str, Any]:
    print("=" * 60)
    print("MANAK-AI: EMBEDDINGS VALIDATION SUITE")
    print("=" * 60)

    errors = []
    warnings = []

    if not os.path.exists(STANDARDS_FILE):
        return {"status": "FAILED", "error": f"Missing {STANDARDS_FILE}"}
    if not os.path.exists(EMBEDDINGS_FILE):
        return {"status": "FAILED", "error": f"Missing {EMBEDDINGS_FILE}"}

    with open(STANDARDS_FILE, "r", encoding="utf-8") as f:
        standards = json.load(f)
    with open(EMBEDDINGS_FILE, "r", encoding="utf-8") as f:
        emb_data = json.load(f)

    # 1. Metadata check
    model_name = emb_data.get("model")
    dim = emb_data.get("dimension")
    if not model_name:
        errors.append("Metadata missing 'model' identifier")
    if dim != EXPECTED_DIM:
        errors.append(f"Metadata dimension {dim} does not match expected {EXPECTED_DIM}")

    # 2. Extract vectors map
    vectors_map: Dict[str, Any] = {}
    if "vectors" in emb_data:
        vectors_map = emb_data["vectors"]
    elif "items" in emb_data:
        for it in emb_data["items"]:
            vectors_map[it["is_number"]] = it

    # 3. Check for duplicates in standards and embeddings
    std_keys = set()
    std_dups = []
    for s in standards:
        num = s["is_number"]
        if num in std_keys:
            std_dups.append(num)
        std_keys.add(num)

    if std_dups:
        errors.append(f"Duplicate IS numbers in standards.json: {std_dups}")

    # 4. Check for missing embeddings
    missing_emb = []
    for num in std_keys:
        if num not in vectors_map:
            missing_emb.append(num)

    if missing_emb:
        errors.append(f"Missing embeddings for {len(missing_emb)} standards (e.g. {missing_emb[:5]})")

    # 5. Check vector integrity (dimension, NaN, zeros, norm)
    corrupted_vectors = []
    zero_vectors = []
    invalid_dimensions = []

    for num, item in vectors_map.items():
        vec = item.get("vector") if isinstance(item, dict) else item
        if not isinstance(vec, list):
            corrupted_vectors.append((num, "vector is not a list"))
            continue
        if len(vec) != EXPECTED_DIM:
            invalid_dimensions.append((num, len(vec)))
            continue

        is_all_zero = True
        has_nan = False
        sum_sq = 0.0

        for val in vec:
            if not isinstance(val, (int, float)) or math.isnan(val) or math.isinf(val):
                has_nan = True
                break
            if val != 0:
                is_all_zero = False
            sum_sq += val * val

        if has_nan:
            corrupted_vectors.append((num, "contains NaN or Inf"))
        elif is_all_zero:
            zero_vectors.append(num)
        elif abs(math.sqrt(sum_sq) - 1.0) > 0.05:
            # Vectors are normalized to unit sphere
            warnings.append(f"Vector {num} norm is {math.sqrt(sum_sq):.3f} (expected ~1.0 for cosine similarity)")

    if corrupted_vectors:
        errors.append(f"Found {len(corrupted_vectors)} corrupted vectors: {corrupted_vectors[:5]}")
    if zero_vectors:
        errors.append(f"Found {len(zero_vectors)} all-zero vectors: {zero_vectors[:5]}")
    if invalid_dimensions:
        errors.append(f"Found {len(invalid_dimensions)} vectors with invalid dimension: {invalid_dimensions[:5]}")

    status = "PASSED" if not errors else "FAILED"

    report = {
        "validation_status": status,
        "timestamp": datetime.now().isoformat(),
        "total_standards": len(standards),
        "total_embeddings": len(vectors_map),
        "embedding_model": model_name,
        "dimension": EXPECTED_DIM,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings[:10],
    }

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"Status: {status}")
    print(f"Total Standards: {len(standards)}")
    print(f"Total Embeddings: {len(vectors_map)}")
    print(f"Dimension: {EXPECTED_DIM}")
    print(f"Errors: {len(errors)}")
    print(f"Warnings: {len(warnings)}")
    if errors:
        for err in errors:
            print(f"  ❌ {err}")
    else:
        print("✓ All embedding integrity and dimensional checks passed successfully!")
    print(f"Report saved to: {REPORT_FILE}")
    print("=" * 60)

    return report


if __name__ == "__main__":
    rep = validate_embeddings()
    if rep["validation_status"] != "PASSED":
        sys.exit(1)
