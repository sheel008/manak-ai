"""Pydantic response schemas for the MANAK-AI API."""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from pydantic import ConfigDict


class SearchRequest(BaseModel):
    query: str
    department: Optional[str] = None
    category: Optional[str] = None
    sector: Optional[str] = None
    qco_required: Optional[bool] = None
    top_k: Optional[int] = None
    min_confidence: Optional[float] = None
    reopen: Optional[bool] = False


class CompareRequest(BaseModel):
    is_numbers: List[str]


class SavedItemCreate(BaseModel):
    is_number: str


class CertificationCheckRequest(BaseModel):
    product_name: str


class ChatRequest(BaseModel):
    message: str
    sessionId: Optional[str] = None
    lang: Optional[str] = "en"
    history: Optional[List[Dict[str, Any]]] = None


class ReviewCreate(BaseModel):
    request_id: str
    is_number: str
    decision: str  # accept, reject, flag


class NormativeReference(BaseModel):
    is_number: str
    title: Optional[str] = None
    category: Optional[str] = None


class RelatedStandard(BaseModel):
    is_number: str
    title: Optional[str] = None
    category: Optional[str] = None


class Evidence(BaseModel):
    source_excerpt: str
    matched_specifications: List[Dict[str, str]]
    overlapping_keywords: List[str]


class Amendment(BaseModel):
    amendment_number: str
    date: str
    description: str


class VersionInfo(BaseModel):
    version: Optional[str] = None
    last_amended: Optional[str] = None
    amendment_history: List[Amendment] = []


class StandardResult(BaseModel):
    rank: int
    is_number: str
    title: str
    category: str
    sub_category: Optional[str] = None
    scope: str
    department: Optional[str] = None
    sector: Optional[str] = None
    relevance_score: float
    confidence: Optional[float] = None
    similarity_score: float
    keyword_score: float
    specification_score: float
    department_score: Optional[float] = None
    is_qco_mandatory: bool
    qco_required: Optional[bool] = None
    qco_enforcement_date: Optional[str] = None
    why_recommended: Optional[str] = None
    qco_info: Optional[Dict[str, Any]] = None
    evidence: Evidence
    explanation: str
    normative_references: List[NormativeReference]
    related_standards: List[RelatedStandard]
    version_info: VersionInfo
    certification: Dict[str, Any]



class SearchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    request_id: str
    query: str
    abstained: bool
    abstention_reason: Optional[str] = None
    results: List[StandardResult] = []
    threshold: Optional[float] = None
