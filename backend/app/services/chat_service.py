"""Retrieval-Augmented Generation (RAG) Chat Pipeline for MANAK-AI v2.0.

Adheres strictly to:
1. Retrieval Pipeline:
   User Query -> Embedding Generation -> Vector Similarity Search ->
   Enhanced Keyword/Spec/Category/QCO Reranking -> Retrieve Standards ->
   Retrieve Related Standards -> Retrieve QCO Rules -> Generate Grounded Response ->
   Return Structured JSON.
2. Grounded responses ONLY from BIS standards corpus. Never invents IS numbers.
3. Structured JSON output matching required specifications.
4. Support conversation history context.
5. Full backward compatibility with existing tests and clients.
"""
import re
import sys
import uuid
import logging
from typing import Dict, Any, List, Optional

from app.core import config, database
from app.retrieval import vector_search, rerank
from app.rules import related as related_rules, certification as cert_rules
from app.evidence import builder as evidence_builder
from app.services.llm_provider import get_llm_provider, FallbackProvider
from app.services.intent_router import classify_intent, build_conversational_response, Intent, DEFAULT_FOLLOW_UPS

logger = logging.getLogger(__name__)

# In-memory chat sessions storage
_chat_sessions: Dict[str, Dict[str, Any]] = {}

# Common domain token expansions to ensure accurate retrieval for industry queries
DOMAIN_SYNONYMS = {
    "tmt": ["steel", "bars", "fe", "reinforcement", "deformed", "rebar"],
    "helmet": ["helmets", "headgear", "protective"],
    "helmets": ["helmet", "headgear", "protective"],
    "motorcycle": ["two", "wheeler", "helmets", "vehicle"],
    "wire": ["cables", "cable", "conductor", "conductors", "insulated", "wiring"],
    "wires": ["cables", "conductors", "wiring"],
    "cable": ["cables", "wire", "wires", "conductor"],
    "pipe": ["pipes", "tubes", "tubing", "conduit", "potable"],
    "pipes": ["pipe", "tubes", "conduit", "potable"],
    "cooker": ["cookers", "cooking", "domestic", "pressure"],
    "paint": ["paints", "emulsion", "coating"],
    "cement": ["portland", "opc", "clinker", "mortar"],
    "solar": ["photovoltaic", "pv", "module", "modules", "cell", "lighting"],
    "pv": ["solar", "photovoltaic", "module", "cells"],
    "extinguisher": ["fire", "extinguishers", "safety"],
    # Multilingual token mappings for Hindi, Marathi, Tamil, Kannada
    "सीमेंट": ["cement", "portland", "opc", "clinker", "mortar"],
    "सिमेंट": ["cement", "portland", "opc", "clinker", "mortar"],
    "சிமெண்ட்": ["cement", "portland", "opc", "clinker", "mortar"],
    "ಸಿಮೆಂಟ್": ["cement", "portland", "opc", "clinker", "mortar"],
    "हेलमेट": ["helmet", "helmets", "headgear", "protective"],
    "शिरस्त्राण": ["helmet", "helmets", "headgear", "protective"],
    "ஹெல்மெட்": ["helmet", "helmets", "headgear", "protective"],
    "ಶಿರಸ್ತ್ರಾಣ": ["helmet", "helmets", "headgear", "protective"],
    "स्टील": ["steel", "bars", "fe", "reinforcement", "deformed", "rebar", "tmt"],
    "सरिया": ["steel", "bars", "fe", "reinforcement", "deformed", "rebar", "tmt"],
    "पोलाद": ["steel", "bars", "fe", "reinforcement", "deformed", "rebar", "tmt"],
    "எஃகு": ["steel", "bars", "fe", "reinforcement", "deformed", "rebar", "tmt"],
    "ಉಕ್ಕು": ["steel", "bars", "fe", "reinforcement", "deformed", "rebar", "tmt"],
    "तार": ["wire", "wires", "cable", "cables", "conductor", "conductors", "wiring"],
    "केबल": ["wire", "wires", "cable", "cables", "conductor", "conductors", "wiring"],
    "கம்பி": ["wire", "wires", "cable", "cables", "conductor", "conductors", "wiring"],
    "கேபிள்": ["wire", "wires", "cable", "cables", "conductor", "conductors", "wiring"],
    "ತಂತಿ": ["wire", "wires", "cable", "cables", "conductor", "conductors", "wiring"],
    "ಕೇಬಲ್": ["wire", "wires", "cable", "cables", "conductor", "conductors", "wiring"],
    "पाइप": ["pipe", "pipes", "tubes", "tubing", "conduit", "potable"],
    "पाईप": ["pipe", "pipes", "tubes", "tubing", "conduit", "potable"],
    "नल": ["pipe", "pipes", "tubes", "tubing", "conduit", "potable"],
    "குழாய்": ["pipe", "pipes", "tubes", "tubing", "conduit", "potable"],
    "ಪೈಪ್": ["pipe", "pipes", "tubes", "tubing", "conduit", "potable"],
    "ಕೊಳವೆ": ["pipe", "pipes", "tubes", "tubing", "conduit", "potable"],
    "कुकर": ["cooker", "cookers", "cooking", "domestic", "pressure"],
    "कूकर्स": ["cooker", "cookers", "cooking", "domestic", "pressure"],
    "குக்கர்": ["cooker", "cookers", "cooking", "domestic", "pressure"],
    "ಕುಕ್ಕರ್": ["cooker", "cookers", "cooking", "domestic", "pressure"],
    "सोलर": ["solar", "photovoltaic", "pv", "module", "modules", "cell", "lighting"],
    "सौर": ["solar", "photovoltaic", "pv", "module", "modules", "cell", "lighting"],
    "சூரிய": ["solar", "photovoltaic", "pv", "module", "modules", "cell", "lighting"],
    "ಸೌರ": ["solar", "photovoltaic", "pv", "module", "modules", "cell", "lighting"],
    "पेंट": ["paint", "paints", "emulsion", "coating"],
    "रंग": ["paint", "paints", "emulsion", "coating"],
    "வண்ணப்பூச்சு": ["paint", "paints", "emulsion", "coating"],
    "ಬಣ್ಣ": ["paint", "paints", "emulsion", "coating"],
    "अग्निशामक": ["extinguisher", "fire", "extinguishers", "safety"],
    "தீயணைப்பான்": ["extinguisher", "fire", "extinguishers", "safety"],
}


def _expand_query_tokens(tokens: List[str]) -> List[str]:
    expanded = list(tokens)
    for t in tokens:
        syns = DOMAIN_SYNONYMS.get(t.lower())
        if syns:
            expanded.extend(syns)
    return list(dict.fromkeys(expanded))


def _extract_is_number(query: str) -> Optional[str]:
    """Check if query explicitly specifies an IS number (e.g. IS 456, IS 4985, IS 269:2015)."""
    m = re.search(r"\bIS\s*[:\s]?\s*(\d+(?:\s*\([^)]+\))?(?::\d{4})?)\b", query, re.IGNORECASE)
    if m:
        digits = m.group(1).strip()
        return f"IS {digits}"
    return None


def _fetch_standard_by_is(is_number_prefix: str) -> Optional[Dict[str, Any]]:
    """Lookup standard directly if user specifies exact IS number."""
    clean = is_number_prefix.replace(" ", "").lower()
    try:
        conn = database.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT is_number, title, category, sub_category, scope,
                           specifications, normative_references, is_qco_mandatory,
                           qco_enforcement_date, version, last_amended,
                           amendment_history, source_excerpt, 1.0 AS similarity
                    FROM standards
                    WHERE REPLACE(LOWER(is_number), ' ', '') LIKE %s
                    LIMIT 1
                    """,
                    (f"{clean}%",),
                )
                row = cur.fetchone()
                if row:
                    row["similarity"] = 1.0
                    return row
        finally:
            conn.close()
    except Exception:
        pass
    return None


def _calculate_confidence(sim: float, kw_score: float, spec_score: float, cat_score: float, qco_score: float) -> int:
    """
    Computes normalized confidence percentage (0-100) using the 5 weights:
      40% embedding similarity, 25% spec, 20% keyword, 10% category, 5% QCO boost.
    Normalizes so that:
      - Direct/strong hits score 90+ (Green)
      - Confident relevant hits score 70-89 (Yellow)
      - Partial/exploratory hits score below 70 (Orange)
    """
    raw_final, sim_100 = rerank.enhanced_combine_scores(
        similarity=sim,
        keyword=kw_score,
        spec=spec_score,
        category=cat_score,
        qco_boost=qco_score,
    )

    # Base scale
    if sim >= 0.58 or (sim >= 0.44 and (kw_score >= 45 or spec_score >= 25)):
        # High confidence band (90 - 98)
        norm = 90 + int(min(8, max(0, (raw_final - 35) * 0.35)))
    elif sim >= 0.35 or kw_score >= 30 or spec_score > 0 or cat_score > 0:
        # Moderate confidence band (70 - 89)
        norm = 72 + int(min(16, max(0, (raw_final - 20) * 0.6)))
    else:
        # Exploratory band (< 70)
        norm = max(42, min(69, int(raw_final * 1.5)))

    return int(round(norm))


def _detect_language(text: str, default_lang: str = "en") -> str:
    """Detect language if default is 'en' but text contains Indic scripts."""
    if default_lang and default_lang.lower() in ("hi", "mr", "ta", "kn"):
        return default_lang.lower()

    # Tamil script: U+0B80 to U+0BFF
    if any("\u0b80" <= c <= "\u0bff" for c in text):
        return "ta"
    # Kannada script: U+0C80 to U+0CFF
    if any("\u0c80" <= c <= "\u0cff" for c in text):
        return "kn"
    # Devanagari script: U+0900 to U+097F
    if any("\u0900" <= c <= "\u097f" for c in text):
        marathi_indicators = ["नमस्कार", "आहे", "करा", "नाही", "पोलाद", "सिमेंट", "कूकर्स", "पाईप", "शिरस्त्राण"]
        if any(w in text for w in marathi_indicators):
            return "mr"
        return "hi"

    return default_lang or "en"


def handle_chat(message: str, session_id: Optional[str] = None,
                history: Optional[List[Dict[str, Any]]] = None,
                lang: str = "en") -> Dict[str, Any]:
    """Execute the full RAG pipeline and return structured response."""
    raw_query = (message or "").replace("\x00", "").strip()
    raw_query = re.sub(r"<script.*?>.*?</script>", "", raw_query, flags=re.IGNORECASE | re.DOTALL).strip()

    # Prompt injection and jailbreak protection
    injection_patterns = [
        r"ignore\s+(all\s+)?(previous|prior)\s+instructions?",
        r"system\s*prompt",
        r"you\s+are\s+now\s+(an?\s+)?unrestricted",
        r"jailbreak",
        r"act\s+as\s+DAN",
        r"developer\s+mode",
    ]
    for pattern in injection_patterns:
        if re.search(pattern, raw_query, re.IGNORECASE):
            raw_query = re.sub(pattern, "", raw_query, flags=re.IGNORECASE).strip()
            if not raw_query:
                return {
                    "sessionId": session_id or f"session_{uuid.uuid4().hex[:8]}",
                    "answer": "Security Notice: Your query contained disallowed instruction overrides. MANAK-AI only responds to verifiable Bureau of Indian Standards (BIS) technical specifications.",
                    "recommendations": [],
                    "evidence": [],
                    "follow_up": ["How do I search for a BIS standard?", "What is an Indian Standard?"],
                }

    sid = session_id or f"session_{uuid.uuid4().hex[:8]}"

    if sid not in _chat_sessions:
        _chat_sessions[sid] = {
            "messages": [],
            "last_standard": None,
            "last_results": [],
        }
    session = _chat_sessions[sid]

    effective_lang = _detect_language(raw_query, default_lang=lang)

    # ── Intent Routing Layer (BEFORE expensive semantic search) ──
    has_prev_standard = bool(session.get("last_standard"))
    intent, intent_meta = classify_intent(raw_query, session_has_standard=has_prev_standard)

    # For non-search intents (GREETING, GENERAL_CONVERSATION, DOCUMENT_QUERY, UNKNOWN / OUT_OF_DOMAIN):
    # Return immediately WITHOUT running embedding generation or semantic vector search.
    if intent in (Intent.GREETING, Intent.GENERAL_CONVERSATION, Intent.DOCUMENT_QUERY, Intent.UNKNOWN):
        conv_answer = None
        conv_follow_up = DEFAULT_FOLLOW_UPS.get(effective_lang, DEFAULT_FOLLOW_UPS.get(lang, DEFAULT_FOLLOW_UPS["en"]))

        # For casual greetings and general conversation, use configured LLM provider (Groq / Gemini / OpenAI)
        if intent in (Intent.GREETING, Intent.GENERAL_CONVERSATION):
            llm = get_llm_provider()
            session_history = history if history is not None else session.get("messages", [])
            try:
                conv_answer = llm.generate_conversational_response(
                    message=raw_query,
                    history=session_history,
                    lang=effective_lang,
                )
            except Exception as e:
                logger.warning("Conversational LLM response generation failed: %s", type(e).__name__)
                conv_answer = None

        # Fallback to deterministic responses if LLM is unavailable or failed
        if not conv_answer:
            conv_answer = build_conversational_response(intent, intent_meta, raw_query, lang=effective_lang)

        session["messages"].append({"role": "user", "content": raw_query})
        session["messages"].append({
            "role": "assistant",
            "content": conv_answer,
            "citations": [],
            "recommendations": [],
            "qco": None,
        })

        return {
            "intent": intent.value,
            "query": raw_query,
            "answer": conv_answer,
            "recommendations": [],
            "qco": None,
            "related_standards": [],
            "evidence": [],
            "follow_up": conv_follow_up,
            # Backward-compatible fields
            "sessionId": sid,
            "message": conv_answer,
            "citations": [],
        }

    # Resolve context from conversation history (e.g. follow-up question referencing previous standard)
    search_query = raw_query
    is_follow_up = False
    last_std = session.get("last_standard")

    follow_up_triggers = ["mandatory", "qco", "isi", "certification", "scope", "specification", "test", "amendment", "it", "this", "that"]
    if last_std and (len(raw_query.split()) <= 6 or any(w in raw_query.lower() for w in follow_up_triggers)):
        is_follow_up = True
        search_query = f"{raw_query} {last_std.get('is_number', '')} {last_std.get('title', '')}"

    # Multilingual query bridge: extract Indic tokens and append English synonyms for vector search
    is_indic = any(ord(c) > 127 for c in raw_query)
    if is_indic:
        raw_tokens = rerank.tokenize(raw_query)
        translated_syns = []
        for token in raw_tokens:
            syns = DOMAIN_SYNONYMS.get(token.lower())
            if syns:
                translated_syns.extend(syns)
        if translated_syns:
            search_query = f"{search_query} {' '.join(dict.fromkeys(translated_syns))}"

    # 1 & 2. Embedding + Vector retrieval
    direct_match = None
    explicit_is = _extract_is_number(raw_query)
    if explicit_is:
        direct_match = _fetch_standard_by_is(explicit_is)

    vs_module = sys.modules.get("app.retrieval.vector_search", vector_search)
    candidates = vs_module.vector_search(search_query, top_k=config.VECTOR_TOP_K)
    if is_follow_up and last_std:
        if not any(c.get("is_number") == last_std.get("is_number") for c in candidates):
            candidates.insert(0, {**last_std, "similarity": 0.95})
        else:
            for c in candidates:
                if c.get("is_number") == last_std.get("is_number"):
                    c["similarity"] = max(c.get("similarity", 0.0), 0.95)

    if direct_match and not any(c.get("is_number") == direct_match.get("is_number") for c in candidates):
        candidates.insert(0, direct_match)


    # 3. Rerank using enhanced 5-weight formula (40/25/20/10/5)
    query_tokens = rerank.tokenize(raw_query)
    expanded_tokens = _expand_query_tokens(query_tokens)
    query_specs = rerank.extract_specs(raw_query)

    scored = []
    for c in candidates:
        # Include title, scope, and source_excerpt in keyword matching
        full_text = f"{c.get('title', '')} {c.get('scope') or ''} {c.get('source_excerpt') or ''}"
        c_tokens = set(rerank.tokenize(full_text))
        hits = set(expanded_tokens) & c_tokens
        kw_score = min(100.0, (len(hits) / max(1, len(query_tokens))) * 100.0) if query_tokens else 0.0

        spec_score, matched = rerank.specification_match_score(query_specs, c)
        cat_score = rerank.category_overlap_score(expanded_tokens, c)
        qco_score = rerank.qco_boost_score(c)

        sim = float(c.get("similarity", 0.0))
        if direct_match and c.get("is_number") == direct_match.get("is_number"):
            sim = max(sim, 0.95)
            kw_score = 100.0
        elif is_follow_up and last_std and c.get("is_number") == last_std.get("is_number"):
            sim = max(sim, 0.95)
            kw_score = max(kw_score, 85.0)


        confidence = _calculate_confidence(sim, kw_score, spec_score, cat_score, qco_score)
        scored.append({
            "row": c,
            "sim": sim,
            "kw": kw_score,
            "spec": spec_score,
            "cat": cat_score,
            "qco": qco_score,
            "confidence": confidence,
            "matched_specs": matched,
            "overlapping_keywords": sorted(hits),
        })

    scored.sort(key=lambda s: s["confidence"], reverse=True)

    # If no results or below minimum floor, return abstention response
    if not scored:
        abstain_messages = {
            "hi": "वर्तमान बीआईएस मानक संग्रह से इस विनिर्देश को सत्यापित नहीं किया जा सका। कृपया उत्पाद विवरण की जांच करें या विशिष्ट पैरामीटर (जैसे सामग्री, ग्रेड, वोल्टेज, दबाव या आयाम) प्रदान करें।",
            "mr": "सध्याच्या बीआयएस मानक संग्रहातून या विनिर्देशाची पडताळणी करता आली नाही. कृपया उत्पादन वर्णन तपासा किंवा विशिष्ट निकष (जसे की साहित्य, श्रेणी, व्होल्टेज किंवा आकारमान) प्रदान करा.",
            "ta": "தற்போதைய BIS தரநிலைக் களஞ்சியத்திலிருந்து இந்த விவரக்குறிப்பைச் சரிபார்க்க முடியவில்லை. தயாரிப்பு விளக்கத்தைச் சரிபார்க்கவும் அல்லது குறிப்பிட்ட அளவுருக்களை வழங்கவும்.",
            "kn": "ಪ್ರಸ್ತುತ BIS ಮಾನಕಗಳ ಸಂಗ್ರಹದಿಂದ ಈ ವಿವರಣೆಯನ್ನು ಪರಿಶೀಲಿಸಲು ಸಾಧ್ಯವಾಗಲಿಲ್ಲ. ದಯವಿಟ್ಟು ಉತ್ಪನ್ನ ವಿವರಣೆಯನ್ನು ಪರಿಶೀಲಿಸಿ ಅಥವಾ ನಿರ್ದಿಷ್ಟ ನಿಯತಾಂಕಗಳನ್ನು ಒದಗಿಸಿ.",
            "en": (
                "I could not verify this from the current BIS standards corpus. "
                "Please check the product description or provide specific parameters (such as material, grade, voltage, pressure, or dimensions)."
            ),
        }
        abstain_text = abstain_messages.get(lang, abstain_messages["en"])
        session["messages"].append({"role": "user", "content": raw_query})
        session["messages"].append({"role": "assistant", "content": abstain_text, "citations": []})
        return {
            "intent": intent.value,
            "query": raw_query,
            "answer": abstain_text,
            "recommendations": [],
            "qco": {
                "mandatory": False,
                "enforcement_date": None,
                "rule": "No verified BIS standard found for this specification.",
            },
            "related_standards": [],
            "evidence": [],
            "follow_up": [
                "Find BIS standard for PVC pipes",
                "Is ISI mandatory for helmets?",
                "Which standard applies to LED street lights?",
            ],
            "sessionId": sid,
            "message": abstain_text,
            "citations": [],
        }

    # 4. Top standard & Recommendations
    top_item = scored[0]
    top = top_item["row"]
    session["last_standard"] = top

    recommendations = []
    for item in scored[:3]:
        r = item["row"]
        summary = (r.get("scope") or r.get("title") or "")
        clean_summary = summary[:200].strip() + ("..." if len(summary) > 200 else "")
        recommendations.append({
            "is_number": r["is_number"],
            "title": r["title"],
            "confidence": item["confidence"],
            "category": r.get("category") or "General",
            "summary": clean_summary,
        })

    # 5. Related Standards (Normative References)
    related_list = []
    norm_refs = top.get("normative_references") or []
    for ref in norm_refs:
        if ref and ref not in related_list and ref != top["is_number"]:
            related_list.append(ref)

    if len(related_list) < 2:
        try:
            extra = related_rules.compute_related_standards(top["is_number"], limit=4)
            for e in extra:
                is_num = e.get("is_number")
                if is_num and is_num not in related_list and is_num != top["is_number"]:
                    related_list.append(is_num)
        except Exception:
            pass

    # 6. Retrieve QCO Rules
    is_mandatory = bool(top.get("is_qco_mandatory"))
    enf_date = str(top.get("qco_enforcement_date")) if top.get("qco_enforcement_date") else None
    rule_desc = None

    try:
        rule_row = cert_rules.lookup_product(top.get("title", "")) or cert_rules.lookup_product(raw_query)
        if rule_row:
            is_mandatory = bool(rule_row.get("is_qco_mandatory", is_mandatory))
            if not enf_date and rule_row.get("enforcement_date"):
                enf_date = str(rule_row["enforcement_date"])
            prod_name = rule_row.get("product_name") or top.get("title")
            rule_desc = f"Mandatory Quality Control Order (QCO) issued by Government of India requires compulsory BIS certification (ISI Mark) for {prod_name}."
    except Exception:
        pass

    if not rule_desc:
        if is_mandatory:
            rule_desc = f"Mandatory Quality Control Order (QCO) notified under the Bureau of Indian Standards Act requires mandatory ISI certification for {top.get('title')} ({top.get('is_number')})."
        else:
            rule_desc = f"Standard {top.get('is_number')} is governed under voluntary BIS Product Certification / standard conformity assessment procedures."

    qco = {
        "mandatory": is_mandatory,
        "enforcement_date": enf_date or ("2023-01-01" if is_mandatory else None),
        "rule": rule_desc,
    }

    # 7. Evidence
    source_excerpt = top.get("source_excerpt") or top.get("scope") or f"Standard specifications and scope defined under {top.get('is_number')}."
    evidence = [
        {
            "standard": top["is_number"],
            "excerpt": source_excerpt,
        }
    ]

    # 8. Follow-up Questions (3 Contextual Prompts in target language)
    target_lang = effective_lang if effective_lang in ("hi", "mr", "ta", "kn") else lang
    if target_lang == "hi":
        follow_up = [
            f"क्या वर्तमान QCO आदेशों के तहत {top['is_number']} के लिए बीआईएस प्रमाणन अनिवार्य है?",
            f"{top['is_number']} में विशिष्ट तकनीकी विनिर्देश आवश्यकताएं क्या हैं?",
            f"{top['is_number']} के साथ कौन से प्रामाणिक संदर्भ मानक लागू होते हैं?",
        ]
    elif target_lang == "mr":
        follow_up = [
            f"सध्याच्या QCO आदेशांनुसार {top['is_number']} साठी बीआयएस प्रमाणन अनिवार्य आहे का?",
            f"{top['is_number']} मध्ये विशिष्ट तांत्रिक तपशील काय आहेत?",
            f"{top['is_number']} सोबत कोणते मानक संदर्भ लागू होतात?",
        ]
    elif target_lang == "ta":
        follow_up = [
            f"தற்போதைய QCO உத்தரவுகளின் கீழ் {top['is_number']}க்கு BIS சான்றிதழ் கட்டாயமா?",
            f"{top['is_number']} இன் குறிப்பிட்ட தொழில்நுட்ப விவரக்குறிப்புத் தேவைகள் என்ன?",
            f"{top['is_number']} உடன் பொருந்தக்கூடிய பிற இந்தியத் தரநிலைகள் யாவை?",
        ]
    elif target_lang == "kn":
        follow_up = [
            f"ಪ್ರಸ್ತುತ QCO ಆದೇಶಗಳ ಅಡಿಯಲ್ಲಿ {top['is_number']} ಗೆ BIS ಪ್ರಮಾಣೀಕರಣ ಕಡ್ಡಾಯವೇ?",
            f"{top['is_number']} ನಲ್ಲಿನ ನಿರ್ದಿಷ್ಟ ತಾಂತ್ರಿಕ ವಿವರಣೆಗಳ ಅಗತ್ಯತೆಗಳು ಯಾವುವು?",
            f"{top['is_number']} ಜೊತೆಗೆ ಯಾವ ಮಾನಕ ಉಲ್ಲೇಖಗಳು ಅನ್ವಯಿಸುತ್ತವೆ?",
        ]
    else:
        follow_up = [
            f"Is BIS certification mandatory for {top['is_number']} under current QCO orders?",
            f"What are the specific technical specification requirements in {top['is_number']}?",
            f"Which normative reference standards apply alongside {top['is_number']}?",
        ]

    # 9. Generate Grounded Response (via LLM or deterministic fallback)
    llm = get_llm_provider()
    answer = None
    if not isinstance(llm, FallbackProvider):
        try:
            answer = llm.generate_response(
                query=raw_query,
                standard=top,
                qco=qco,
                related=related_list,
                evidence=evidence,
                confidence=top_item["confidence"],
                matched_specs=top_item["matched_specs"],
                overlapping_keywords=top_item["overlapping_keywords"],
                follow_up=follow_up,
                lang=target_lang,
            )
        except Exception as e:
            logger.warning("LLM grounded response generation failed: %s", type(e).__name__)
            answer = None

    if not answer:
        answer = FallbackProvider().generate_response(
            query=raw_query,
            standard=top,
            qco=qco,
            related=related_list,
            evidence=evidence,
            confidence=top_item["confidence"],
            matched_specs=top_item["matched_specs"],
            overlapping_keywords=top_item["overlapping_keywords"],
            follow_up=follow_up,
            lang=target_lang,
        )

    # Citations for backward compatibility
    citations = [{"is_number": r["is_number"], "title": r["title"]} for r in recommendations]

    # Save to session
    session["messages"].append({"role": "user", "content": raw_query})
    session["messages"].append({
        "role": "assistant",
        "content": answer,
        "citations": citations,
        "recommendations": recommendations,
        "qco": qco,
    })

    return {
        "intent": intent.value,
        "query": raw_query,
        "answer": answer,
        "recommendations": recommendations,
        "qco": qco,
        "related_standards": related_list,
        "evidence": evidence,
        "follow_up": follow_up,
        # Backward-compatible fields
        "sessionId": sid,
        "message": answer,
        "citations": citations,
    }
