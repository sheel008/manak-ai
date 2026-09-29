"""Database connection and schema helpers."""
import psycopg2
from psycopg2.extras import RealDictCursor, Json
from app.core import config

CREATE_SCHEMA_SQL = """
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS standards (
    id SERIAL PRIMARY KEY,
    is_number TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    sub_category TEXT,
    scope TEXT,
    specifications JSONB,
    normative_references TEXT[],
    is_qco_mandatory BOOLEAN DEFAULT FALSE,
    qco_enforcement_date DATE,
    version TEXT,
    last_amended DATE,
    amendment_history JSONB,
    source_excerpt TEXT,
    department TEXT,
    sector TEXT,
    qco_required BOOLEAN DEFAULT FALSE,
    search_weight_boost FLOAT DEFAULT 1.0,
    keywords TEXT[] DEFAULT '{}',
    description TEXT,
    status TEXT DEFAULT 'Active',
    source TEXT,
    provenance TEXT,
    related_standards TEXT[] DEFAULT '{}',
    revision_year TEXT,
    international_equivalent TEXT,
    title_hindi TEXT,
    embedding vector(%(dim)s)
    
);

CREATE TABLE IF NOT EXISTS certification_rules (
    id SERIAL PRIMARY KEY,
    product_name TEXT NOT NULL,
    aliases TEXT[] DEFAULT '{}',
    is_qco_mandatory BOOLEAN DEFAULT FALSE,
    applicable_is_number TEXT,
    enforcement_date DATE,
    UNIQUE(product_name, applicable_is_number)
);

CREATE TABLE IF NOT EXISTS reviews (
    id SERIAL PRIMARY KEY,
    request_id TEXT NOT NULL,
    is_number TEXT NOT NULL,
    decision TEXT NOT NULL,
    reviewed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS search_logs (
    id SERIAL PRIMARY KEY,
    query TEXT NOT NULL,
    top_result_is_number TEXT,
    department TEXT,
    result_count INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS saved_items (
    id SERIAL PRIMARY KEY,
    is_number TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    category TEXT,
    is_qco_mandatory BOOLEAN DEFAULT FALSE,
    saved_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS departments (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    officer_name TEXT,
    designation TEXT
);
"""

MIGRATION_SQL = """
ALTER TABLE standards ADD COLUMN IF NOT EXISTS department TEXT;
ALTER TABLE standards ADD COLUMN IF NOT EXISTS sector TEXT;
ALTER TABLE standards ADD COLUMN IF NOT EXISTS qco_required BOOLEAN DEFAULT FALSE;
ALTER TABLE standards ADD COLUMN IF NOT EXISTS search_weight_boost FLOAT DEFAULT 1.0;
ALTER TABLE standards ADD COLUMN IF NOT EXISTS keywords TEXT[] DEFAULT '{}';
ALTER TABLE standards ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE standards ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'Active';
ALTER TABLE standards ADD COLUMN IF NOT EXISTS source TEXT;
ALTER TABLE standards ADD COLUMN IF NOT EXISTS provenance TEXT;
ALTER TABLE standards ADD COLUMN IF NOT EXISTS related_standards TEXT[] DEFAULT '{}';
ALTER TABLE standards ADD COLUMN IF NOT EXISTS revision_year TEXT;
ALTER TABLE standards ADD COLUMN IF NOT EXISTS international_equivalent TEXT;
ALTER TABLE standards ADD COLUMN IF NOT EXISTS title_hindi TEXT;

CREATE INDEX IF NOT EXISTS idx_standards_department ON standards(department);
CREATE INDEX IF NOT EXISTS idx_standards_sector ON standards(sector);
CREATE INDEX IF NOT EXISTS idx_standards_qco_required ON standards(qco_required);
CREATE INDEX IF NOT EXISTS idx_standards_status ON standards(status);
CREATE UNIQUE INDEX IF NOT EXISTS idx_certification_rules_product_is
ON certification_rules(product_name, applicable_is_number);
"""


def get_connection():
    return psycopg2.connect(config.DATABASE_URL, cursor_factory=RealDictCursor)


def init_schema():
    """Create tables, ensure vector extension, and run non-destructive schema migrations."""
    conn = get_connection()
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(CREATE_SCHEMA_SQL, {"dim": config.EMBEDDING_DIM})
            cur.execute(MIGRATION_SQL)
        print("✓ Schema verified (vector extension + tables + migrations present)")
    finally:
        conn.close()

