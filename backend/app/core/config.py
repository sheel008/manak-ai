"""Application configuration via environment variables."""
import os


# DATABASE_URL is overridden in docker-compose or production environment;
# local default points to the pgvector container on localhost.
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://manak:manak@localhost:5432/manak_ai",
)
# Hosted providers like Render, Heroku, Supabase may supply postgres://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

_cand_data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
if not os.path.exists(_cand_data_dir):
    _cand_data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

DATA_DIR = os.environ.get("DATA_DIR", _cand_data_dir)

STANDARDS_FILE = os.path.join(DATA_DIR, "standards.json")
CERTIFICATION_RULES_FILE = os.path.join(DATA_DIR, "certification_rules.json")
DEPARTMENTS_FILE = os.path.join(DATA_DIR, "departments.json")
EMBEDDINGS_FILE = os.path.join(DATA_DIR, "embeddings.json")
QCO_MAPPING_FILE = os.path.join(DATA_DIR, "qco_mapping.json")
SYNONYMS_FILE = os.path.join(DATA_DIR, "synonyms.json")
RELATED_STANDARDS_FILE = os.path.join(DATA_DIR, "related_standards.json")
METADATA_FILE = os.path.join(DATA_DIR, "metadata.json")

EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# Relevance threshold (0-100) below which we abstain.
ABSTAIN_THRESHOLD = float(os.environ.get("ABSTAIN_THRESHOLD", "40"))

# Number of candidates pulled from the vector search (Top-20 candidate pool), then trimmed to final Top-5.
VECTOR_TOP_K = int(os.environ.get("VECTOR_TOP_K", "20"))
FINAL_TOP_K = int(os.environ.get("FINAL_TOP_K", "5"))

EMBEDDING_DIM = int(os.environ.get("EMBEDDING_DIM", "384"))

# Document analysis chunking configuration
DOC_MAX_CHUNKS = int(os.environ.get("DOC_MAX_CHUNKS", "24"))
DOC_CHUNK_SIZE = int(os.environ.get("DOC_CHUNK_SIZE", "1500"))
DOC_CHUNK_OVERLAP = int(os.environ.get("DOC_CHUNK_OVERLAP", "250"))

# CORS origins: comma-separated list of origins or "*"
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*")


