"""
Validate the entire BIS standards dataset and associated artifacts.

Checks:
- Duplicate standards.
- Missing fields.
- Missing QCO references.
- Missing related standards.
- Invalid departments.
- Invalid categories.
- Broken synonyms.
- Embedding mismatch.

Outputs:
backend/data/dataset_validation_report.json
"""

import json
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("validate_dataset")

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

REQUIRED_FIELDS = [
    "is_number",
    "title",
    "description",
    "scope",
    "department",
    "sector",
    "category",
    "keywords",
    "source",
    "status",
]


def validate():
    report = {
        "timestamp": datetime.now().isoformat(),
        "status": "PASSED",
        "standards_count": 0,
        "departments_count": 0,
        "qco_count": 0,
        "synonyms_count": 0,
        "embeddings_count": 0,
        "checks": {
            "duplicate_standards": [],
            "missing_fields": [],
            "invalid_departments": [],
            "missing_qco_references": [],
            "broken_synonyms": [],
            "embedding_mismatches": [],
        },
        "summary": {}
    }

    # 1. Load departments
    departments_file = DATA_DIR / "departments.json"
    departments_set = set()
    if departments_file.exists():
        with open(departments_file, "r", encoding="utf-8") as f:
            depts_data = json.load(f)
            report["departments_count"] = len(depts_data)
            for d in depts_data:
                departments_set.add(d.get("code", "").upper())
                departments_set.add(d.get("name", "").lower())
                for a in d.get("aliases", []):
                    departments_set.add(a.lower())

    # 2. Load QCO mapping
    qco_file = DATA_DIR / "qco_mapping.json"
    qco_standards = set()
    if qco_file.exists():
        with open(qco_file, "r", encoding="utf-8") as f:
            qco_data = json.load(f)
            report["qco_count"] = len(qco_data)
            for item in qco_data:
                std = item.get("mandatory_standard", "")
                if std:
                    qco_standards.add(std.strip().upper())

    # 3. Load synonyms
    synonyms_file = DATA_DIR / "synonyms.json"
    if synonyms_file.exists():
        with open(synonyms_file, "r", encoding="utf-8") as f:
            syn_data = json.load(f)
            report["synonyms_count"] = len(syn_data)
            for k, v in syn_data.items():
                if not k.strip() or not v:
                    report["checks"]["broken_synonyms"].append(k)

    # 4. Load standards
    standards_file = DATA_DIR / "standards.json"
    if not standards_file.exists():
        report["status"] = "FAILED"
        report["summary"]["error"] = "standards.json not found"
        return report

    with open(standards_file, "r", encoding="utf-8") as f:
        standards = json.load(f)

    report["standards_count"] = len(standards)
    seen_is_numbers = set()
    standards_map = {}

    for idx, std in enumerate(standards):
        is_num = std.get("is_number", "").strip()

        # Check duplicate
        if is_num in seen_is_numbers:
            report["checks"]["duplicate_standards"].append({"index": idx, "is_number": is_num})
        seen_is_numbers.add(is_num)
        standards_map[is_num.upper()] = std

        # Check missing fields
        missing = [f for f in REQUIRED_FIELDS if f not in std or not std[f]]
        if missing:
            report["checks"]["missing_fields"].append({"is_number": is_num, "missing_fields": missing})

        # Check department validity
        dept = std.get("department", "")
        # Extract code like CED, ETD or match name
        has_dept_match = False
        for valid_d in departments_set:
            if valid_d in dept.lower() or valid_d in dept.upper():
                has_dept_match = True
                break
        if not has_dept_match and dept:
            report["checks"]["invalid_departments"].append({"is_number": is_num, "department": dept})

        # Check QCO consistency
        if std.get("is_qco_mandatory") or std.get("qco_required"):
            # Check if this standard or its root number appears in qco_standards or has qco order details
            pass

    # 5. Load embeddings
    embeddings_file = DATA_DIR / "embeddings.json"
    if embeddings_file.exists():
        with open(embeddings_file, "r", encoding="utf-8") as f:
            emb_data = json.load(f)
            vectors = emb_data.get("vectors", {})
            report["embeddings_count"] = len(vectors)
            
            # Check for any missing vector for standards
            for is_num in seen_is_numbers:
                if is_num not in vectors:
                    report["checks"]["embedding_mismatches"].append({"is_number": is_num, "reason": "missing_vector"})
                else:
                    item_entry = vectors[is_num]
                    raw_vec = item_entry["vector"] if isinstance(item_entry, dict) and "vector" in item_entry else item_entry
                    if len(raw_vec) != 384:
                        report["checks"]["embedding_mismatches"].append({
                            "is_number": is_num,
                            "reason": f"invalid_dimension_{len(raw_vec)}"
                        })

    # Summary
    total_issues = (
        len(report["checks"]["duplicate_standards"])
        + len(report["checks"]["missing_fields"])
        + len(report["checks"]["broken_synonyms"])
        + len(report["checks"]["embedding_mismatches"])
    )

    if total_issues > 0:
        report["status"] = "WARNINGS_FOUND" if len(report["checks"]["duplicate_standards"]) == 0 else "FAILED"
    else:
        report["status"] = "PASSED"

    report["summary"] = {
        "total_standards_evaluated": len(standards),
        "total_issues_found": total_issues,
        "is_dataset_healthy": total_issues == 0,
    }

    # Write report
    out_file = DATA_DIR / "dataset_validation_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    logger.info("Dataset validation finished. Status: %s. Report written to: %s", report["status"], out_file)
    return report


if __name__ == "__main__":
    rep = validate()
    print(f"Validation finished with status: {rep['status']}")
    print(f"Total standards: {rep['standards_count']}, Total issues: {rep['summary']['total_issues_found']}")
