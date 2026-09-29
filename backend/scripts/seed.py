import json
import os
from psycopg2.extras import Json

from app.core import config, database
from app.services import embedding


# ------------------------------------------------------------
# Utility Functions
# ------------------------------------------------------------

def count_rows(table):
    """Return total number of rows in a table."""
    conn = database.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) AS c FROM {table}")
            return cur.fetchone()["c"]
    finally:
        conn.close()


# ------------------------------------------------------------
# Seed Departments
# ------------------------------------------------------------

# ------------------------------------------------------------
# Seed Departments
# ------------------------------------------------------------

def seed_departments():
    """Insert BIS departments up to full canonical list (14 departments)."""
    if not os.path.exists(config.DEPARTMENTS_FILE):
        print("⚠ departments.json not found.")
        return

    with open(config.DEPARTMENTS_FILE, "r", encoding="utf-8") as f:
        departments = json.load(f)

    dept_count = count_rows("departments")
    if dept_count == len(departments):
        print(f"✓ Departments already present and up to date ({dept_count})")
        return

    conn = database.get_connection()
    conn.autocommit = True

    try:
        with conn.cursor() as cur:
            for dept in departments:
                cur.execute(
                    """
                    INSERT INTO departments
                    (id, name, officer_name, designation)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (id)
                    DO UPDATE SET
                        name = EXCLUDED.name,
                        officer_name = EXCLUDED.officer_name,
                        designation = EXCLUDED.designation;
                    """,
                    (
                        dept["id"],
                        dept["name"],
                        dept.get("officer_name"),
                        dept.get("designation"),
                    ),
                )

        print(f"✓ Seeded {len(departments)} BIS departments")

    finally:
        conn.close()


def count_aligned_standards():
    """Count standards that have the aligned schema fields populated."""
    conn = database.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) AS c FROM standards WHERE department IS NOT NULL AND sector IS NOT NULL"
            )
            row = cur.fetchone()
            return row["c"] if row else 0
    except Exception:
        return 0
    finally:
        conn.close()


# ------------------------------------------------------------
# Main Seed Function
# ------------------------------------------------------------

def seed():
    from app.rules import certification as cert_rules

    print("\n========== MANAK-AI DATABASE SEED ==========\n")

    database.init_schema()
    seed_departments()

    std_count = count_rows("standards")
    rule_count = count_rows("certification_rules")
    dept_count = count_rows("departments")
    aligned_count = count_aligned_standards()

    print(
        f"Current Database → Standards: {std_count} (Aligned: {aligned_count}) | Rules: {rule_count} | Departments: {dept_count}"
    )

    # Skip ONLY when latest fully-aligned dataset already exists.
    if std_count == 528 and rule_count == 260 and dept_count == 14 and aligned_count == 528:
        print("✓ Latest BIS knowledge base already loaded and aligned. Skipping migration.\n")
        return

    print("🚀 Database is outdated or unaligned. Starting migration...\n")

    # --------------------------------------------------------
    # Load datasets
    # --------------------------------------------------------

    with open(config.STANDARDS_FILE, "r", encoding="utf-8") as f:
        standards = json.load(f)

    with open(config.CERTIFICATION_RULES_FILE, "r", encoding="utf-8") as f:
        rules = json.load(f)

    print(f"Loaded {len(standards)} standards from JSON.")
    print(f"Loaded {len(rules)} certification rules from JSON.\n")

    # Clean date fields
    for standard in standards:
        standard["qco_enforcement_date"] = (
            standard.get("qco_enforcement_date") or None
        )
        standard["last_amended"] = standard.get("last_amended") or None

    # --------------------------------------------------------
    # Load Embeddings (Reuse precomputed embeddings.json)
    # --------------------------------------------------------

    precomputed_vectors = {}
    if os.path.exists(config.EMBEDDINGS_FILE):
        with open(config.EMBEDDINGS_FILE, "r", encoding="utf-8") as f:
            emb_payload = json.load(f)
        vec_dict = emb_payload.get("vectors") or {}
        if not vec_dict and "items" in emb_payload:
            for item in emb_payload["items"]:
                vec_dict[item["is_number"]] = item
        for is_num, entry in vec_dict.items():
            vec = entry.get("vector") if isinstance(entry, dict) else entry
            if vec and len(vec) == config.EMBEDDING_DIM:
                precomputed_vectors[is_num] = vec

    print(f"✓ Reusing {len(precomputed_vectors)} precomputed 384-dim embeddings from embeddings.json")

    # Fallback to model embedding only for any missing standard
    missing_stds = [s for s in standards if s["is_number"] not in precomputed_vectors]
    if missing_stds:
        print(f"Generating embeddings for {len(missing_stds)} missing standards...")
        missing_texts = [f"{s['title']}. {s['scope']}" for s in missing_stds]
        missing_vecs = embedding.embed_texts(missing_texts)
        for s, vec in zip(missing_stds, missing_vecs):
            precomputed_vectors[s["is_number"]] = vec

    vectors = [precomputed_vectors[s["is_number"]] for s in standards]
    print(f"✓ Ready with {len(vectors)} embeddings (384 dimensions).\n")

    # --------------------------------------------------------
    # Database Migration
    # --------------------------------------------------------

    conn = database.get_connection()
    conn.autocommit = True

    inserted_std = 0
    updated_std = 0

    inserted_rules = 0
    updated_rules = 0

    try:

        with conn.cursor() as cur:

            # ==================================================
            # Standards UPSERT
            # ==================================================

            print("Migrating Standards (all 26 canonical fields + embedding)...\n")

            for standard, vector in zip(standards, vectors):
                # Synchronize canonical QCO applicability
                is_qco = cert_rules.is_qco_applicable(standard=standard)
                qco_det = cert_rules.get_qco_details(standard.get("is_number"))
                qco_enf = standard.get("qco_enforcement_date") or (
                    qco_det.get("enforcement_date") if qco_det else None
                )
                is_qco_mandatory = is_qco or bool(standard.get("is_qco_mandatory"))
                qco_required = is_qco or bool(standard.get("qco_required"))

                cur.execute(
                    """
                    INSERT INTO standards
                    (
                        is_number,
                        title,
                        category,
                        sub_category,
                        scope,
                        specifications,
                        normative_references,
                        is_qco_mandatory,
                        qco_enforcement_date,
                        version,
                        last_amended,
                        amendment_history,
                        source_excerpt,
                        department,
                        sector,
                        qco_required,
                        search_weight_boost,
                        keywords,
                        description,
                        status,
                        source,
                        provenance,
                        related_standards,
                        revision_year,
                        international_equivalent,
                        title_hindi,
                        embedding
                    )
                    VALUES
                    (
                        %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
                    )
                    ON CONFLICT (is_number)
                    DO UPDATE SET
                        title = EXCLUDED.title,
                        category = EXCLUDED.category,
                        sub_category = EXCLUDED.sub_category,
                        scope = EXCLUDED.scope,
                        specifications = EXCLUDED.specifications,
                        normative_references = EXCLUDED.normative_references,
                        is_qco_mandatory = EXCLUDED.is_qco_mandatory,
                        qco_enforcement_date = EXCLUDED.qco_enforcement_date,
                        version = EXCLUDED.version,
                        last_amended = EXCLUDED.last_amended,
                        amendment_history = EXCLUDED.amendment_history,
                        source_excerpt = EXCLUDED.source_excerpt,
                        department = EXCLUDED.department,
                        sector = EXCLUDED.sector,
                        qco_required = EXCLUDED.qco_required,
                        search_weight_boost = EXCLUDED.search_weight_boost,
                        keywords = EXCLUDED.keywords,
                        description = EXCLUDED.description,
                        status = EXCLUDED.status,
                        source = EXCLUDED.source,
                        provenance = EXCLUDED.provenance,
                        related_standards = EXCLUDED.related_standards,
                        revision_year = EXCLUDED.revision_year,
                        international_equivalent = EXCLUDED.international_equivalent,
                        title_hindi = EXCLUDED.title_hindi,
                        embedding = EXCLUDED.embedding;
                    """,
                    (
                        standard["is_number"],
                        standard["title"],
                        standard["category"],
                        standard.get("sub_category"),
                        standard.get("scope") or "",
                        Json(standard.get("specifications", {})),
                        standard.get("normative_references", []),
                        is_qco_mandatory,
                        qco_enf,
                        standard.get("version"),
                        standard.get("last_amended"),
                        Json(standard.get("amendment_history", [])),
                        standard.get("source_excerpt"),
                        standard.get("department"),
                        standard.get("sector"),
                        qco_required,
                        float(standard.get("search_weight_boost") or 1.0),
                        standard.get("keywords", []),
                        standard.get("description") or standard.get("scope") or "",
                        standard.get("status", "Active"),
                        standard.get("source", "Bureau of Indian Standards"),
                        standard.get("provenance", "BIS Official Standard Publication"),
                        standard.get("related_standards", []),
                        standard.get("revision_year"),
                        standard.get("international_equivalent"),
                        standard.get("title_hindi"),
                        vector,
                    ),
                )

            # Count after migration
            new_std_count = count_rows("standards")

            inserted_std = max(new_std_count - std_count, 0)
            updated_std = min(std_count, len(standards))

            # ==================================================
            # Certification Rules UPSERT
            # ==================================================

            print("Migrating Certification Rules...\n")

            for rule in rules:

                cur.execute(
                    """
                    INSERT INTO certification_rules
                    (
                        product_name,
                        aliases,
                        is_qco_mandatory,
                        applicable_is_number,
                        enforcement_date
                    )
                    VALUES (%s,%s,%s,%s,%s)
                    ON CONFLICT (product_name, applicable_is_number)
                    DO UPDATE SET
                        aliases = EXCLUDED.aliases,
                        is_qco_mandatory = EXCLUDED.is_qco_mandatory,
                        enforcement_date = EXCLUDED.enforcement_date;
                    """,
                    (
                        rule["product_name"],
                        rule.get("aliases", []),
                        rule.get("is_qco_mandatory", False),
                        rule.get("applicable_is_number"),
                        rule.get("enforcement_date") or None,
                    ),
                )

            new_rule_count = count_rows("certification_rules")

            inserted_rules = max(new_rule_count - rule_count, 0)
            updated_rules = min(rule_count, len(rules))

    finally:
        conn.close()

    # --------------------------------------------------------
    # Final Summary
    # --------------------------------------------------------

    print("\n========== MIGRATION COMPLETE ==========\n")

    print(f"Standards JSON             : {len(standards)}")
    print(f"Certification Rules JSON   : {len(rules)}")
    print()

    print(f"Standards Inserted         : {inserted_std}")
    print(f"Standards Updated          : {updated_std}")
    print(f"Current Standards in DB    : {count_rows('standards')}")
    print()

    print(f"Rules Inserted             : {inserted_rules}")
    print(f"Rules Updated              : {updated_rules}")
    print(f"Current Rules in DB        : {count_rows('certification_rules')}")
    print()

    print("✅ MANAK-AI knowledge base successfully migrated.")
    print("=========================================\n")


if __name__ == "__main__":
    seed()