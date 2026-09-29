"""MANAK-AI FastAPI Production Application.

Serves semantic vector search over Indian Standards (IS), document-based procurement
clause matching, QCO regulatory compliance checks, interactive chatbot, and reviews.
"""
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from scripts.seed import seed
from app.api.routes import router
from app.core import config


@asynccontextmanager
async def lifespan(app: FastAPI):
    # On startup: create schema, enable vector extension, and seed from JSON (skips if populated).
    seed()
    yield


app = FastAPI(
    title="MANAK-AI Backend",
    description="Evidence-backed recommendation engine for Indian Standards in procurement.",
    version="1.0.0",
    lifespan=lifespan,
)

# Parse CORS origins from config
cors_raw = getattr(config, "CORS_ORIGINS", "*")
if cors_raw == "*" or not cors_raw:
    origins = ["*"]
else:
    origins = [o.strip() for o in cors_raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.onrender\.com" if "*" not in origins else None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.get("/health")
@app.get("/api/health")
def health():
    return {"status": "ok"}

