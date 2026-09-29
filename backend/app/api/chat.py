"""Chat endpoint for MANAK-AI AI Procurement Copilot."""
from fastapi import APIRouter, HTTPException
from app.schemas import ChatRequest
from app.services.chat_service import handle_chat

router = APIRouter()


@router.post("/chat")
def chat(req: ChatRequest):
    """
    RAG-powered conversational assistant for BIS standards and procurement specs.
    Returns grounded structured JSON with recommendations, QCO rules, related standards, and evidence.
    """
    message = (req.message or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message is required")

    history = getattr(req, "history", None) or []
    lang = getattr(req, "lang", None) or "en"
    return handle_chat(message, req.sessionId, history, lang=lang)
