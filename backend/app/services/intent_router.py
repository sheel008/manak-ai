"""Deterministic, lightweight intent classification and routing layer for Ask MANAK-AI.

Runs BEFORE the domain-specific recommendation / semantic search pipeline.
Requires ZERO external paid LLM/API dependencies.

Distinguishes at minimum:
1. GREETING
2. GENERAL_CONVERSATION
3. BIS_STANDARD_QUERY
4. PROCUREMENT_RECOMMENDATION
5. QCO_QUERY
6. TECHNICAL_SPECIFICATION_QUERY
7. DOCUMENT_QUERY
8. UNKNOWN (Out-of-Domain / Ambiguous)
"""
import re
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple


class Intent(str, Enum):
    GREETING = "GREETING"
    GENERAL_CONVERSATION = "GENERAL_CONVERSATION"
    BIS_STANDARD_QUERY = "BIS_STANDARD_QUERY"
    PROCUREMENT_RECOMMENDATION = "PROCUREMENT_RECOMMENDATION"
    QCO_QUERY = "QCO_QUERY"
    TECHNICAL_SPECIFICATION_QUERY = "TECHNICAL_SPECIFICATION_QUERY"
    DOCUMENT_QUERY = "DOCUMENT_QUERY"
    UNKNOWN = "UNKNOWN"


# Multilingual greetings and responses
GREETING_PATTERNS = [
    r"^(?:hi|hey|hello|hiya|howdy|heya|hola)\b",
    r"^(?:good\s+(?:morning|afternoon|evening|day))\b",
    r"^(?:greetings)\b",
    # Indic greetings (use whitespace, punctuation, or end of string rather than ASCII \b)
    r"^(?:नमस्ते|नमस्कार|सुप्रभात|प्रणाम)(?:[\s,!?।–—]|$)",
    r"^(?:வணக்கம்|காலை\s+வணக்கம்)(?:[\s,!?।–—]|$)",
    r"^(?:ನಮಸ್ಕಾರ|ಶುಭೋದಯ)(?:[\s,!?।–—]|$)",
]

# Greetings that address the assistant
BOT_NAMES = [r"manak", r"manak[- ]ai", r"copilot", r"assistant", r"there", r"bot"]

OUT_OF_DOMAIN_PATTERNS = [
    r"\b(?:write|code|generate|create)\s+(?:a\s+)?(?:python|java|javascript|c\+\+|c#|ruby|go|rust|php|sql|html|css)\b",
    r"\b(?:python|java|c\+\+|javascript)\s+(?:program|script|code|function|class)\b",
    r"\b(?:factorial|fibonacci|palindrome|quicksort|bubble\s*sort|binary\s*search)\b",
    r"\b(?:write|compose)\s+(?:a\s+)?(?:poem|essay|story|song|joke)\b",
    r"\b(?:who\s+won|who\s+is\s+the\s+president|prime\s+minister\s+of|capital\s+of)\b",
    r"\b(?:recipe\s+for|how\s+to\s+cook|how\s+to\s+bake)\b",
    r"\b(?:weather\s+in|weather\s+today)\b",
    r"\b(?:tell\s+me\s+a\s+joke)\b",
]

DOCUMENT_PATTERNS = [
    r"\b(?:analyze|analyse|check|upload|parse)\s+(?:this\s+)?(?:document|tender|rfp|bid|contract|file|pdf|docx)\b",
    r"\b(?:document|tender|rfp)\s+(?:analysis|clause\s+matching|verification)\b",
]

QCO_KEYWORDS = [
    r"\b(?:qco|quality\s+control\s+order)\b",
    r"\b(?:mandatory|compulsory|obligation|enforced)\b",
    r"\b(?:certification|isi\s+mark|isi\s+certified|isi\s+mandatory)\b",
    r"\b(?:enforcement\s+date|compliance\s+deadline)\b",
    # Multilingual
    r"(?:अनिवार्य|कंपलसरी|सक्तीचे|கட்டாய|ಕಡ್ಡಾಯ)",
    r"(?:गुणवत्ता\s+नियंत्रण|प्रमाणन|प्रमाणीकरण|சான்றிதழ்|ಪ್ರಮಾಣೀಕರಣ)",
]

SPEC_KEYWORDS = [
    r"\b(?:technical\s+specifications?|technical\s+requirements?|specification\s+requirements?)\b",
    r"\b(?:specifications?|specs|parameters?|tolerances?|properties|dimensions?)\b",
    r"\b(?:test\s+methods?|tensile\s+strength|chemical\s+composition|sampling\s+guidelines?)\b",
    # Multilingual
    r"(?:तकनीकी\s+विनिर्देश|विनिर्देश|तांत्रिक\s+तपशील|தொழில்நுட்ப\s+விவரக்குறிப்பு|ತಾಂತ್ರಿಕ\s+ವಿವರಣೆ)",
]

GENERAL_CONVERSATION_PATTERNS = [
    (r"\b(?:who\s+are\s+you|what\s+are\s+you|what\s+is\s+your\s+name|tell\s+me\s+about\s+yourself)\b", "identity"),
    (r"\b(?:what\s+can\s+you\s+do|how\s+can\s+you\s+help|what\s+do\s+you\s+do|help\s+me|how\s+does\s+(?:this|manak(?:-ai)?)\s+work)\b", "capabilities"),
    (r"\b(?:thank\s+you|thanks(?:\s+a\s+lot|\s+so\s+much)?|thx|cheers)\b", "thanks"),
    (r"\b(?:bye|goodbye|see\s+you|cya|farewell)\b", "bye"),
]

GENERAL_TECH_CONVERSATION_PATTERNS = [
    r"\bwhat\s+is\s+the\s+difference\s+between\b",
    r"\bwhat\s+is\s+(?:an?\s+)?(?:api|rest\s*api|database|db|python|machine\s*learning|deep\s*learning|git|docker|sql|cloud)\b",
    r"\bhow\s+does\s+(?:an?\s+)?(?:api|rest|database|machine\s*learning|neural\s*network)\s+work\b",
    r"\bexplain\s+(?:machine\s*learning|deep\s*learning|neural\s*network|rest\s*api|database|api|python)\b",
]

DOMAIN_COMMODITY_KEYWORDS = [
    r"\b(?:steel|tmt|rebar|cement|concrete|pipe|pipes|tube|tubes|helmet|helmets|cooker|cookers|wire|wires|cable|cables)\b",
    r"\b(?:paint|paints|varnish|enamel|glass|glazing|solar|pv|panel|plywood|timber|wood|board)\b",
    r"\b(?:valve|valves|extinguisher|extinguishers|cylinder|cylinders|transformer|transformers|battery|batteries|led|lighting|luminaire)\b",
    r"\b(?:switch|socket|fuse|mcb|circuit\s+breaker|insulator|insulation|aggregate|mortar|brick|bricks|tile|tiles)\b",
    r"\b(?:sanitary|geyser|heater|pump|pumps|motor|motors|generator|compressor|fan|iron|appliance|appliances)\b",
    r"\b(?:footwear|shoe|shoes|boot|boots|textile|textiles|fabric|yarn|thread|tarpaulin|mask|ppe|gloves)\b",
    r"\b(?:fertilizer|pesticide|polymer|plastic|plastics|rubber|tyre|tyres|tire|tires|furniture|chair|chairs|desk)\b",
]

# Procurement indicator words
PROCUREMENT_INDICATORS = [
    r"\b(?:which|what)\s+(?:bis\s+)?standard\b",
    r"\b(?:standard\s+applies\s+to|standards?\s+for|standard\s+should\s+i\s+use)\b",
    r"\b(?:procurement|tender|gem\s+portal|specification\s+for|clause)\b",
    r"\b(?:bis|isi|indian\s+standard)\b",
]

DEFAULT_FOLLOW_UPS: Dict[str, List[str]] = {
    "en": [
        "Which BIS standard applies to LED street lights?",
        "Is BIS certification mandatory for helmets?",
        "Find BIS standard for PVC pipes",
    ],
    "hi": [
        "LED स्ट्रीट लाइट पर कौन सा मानक लागू होता है?",
        "क्या हेलमेट के लिए ISI अनिवार्य है?",
        "PVC पाइप के लिए BIS मानक खोजें।",
    ],
    "mr": [
        "LED स्ट्रीट लाइटवर कोणते मानक लागू होते?",
        "हेल्मेटसाठी ISI सक्तीचे आहे का?",
        "PVC पाईपसाठी BIS मानक शोधा.",
    ],
    "ta": [
        "LED தெரு விளக்குகளுக்கு எந்தத் தரம் பொருந்தும்?",
        "ஹெல்மெட்டுகளுக்கு ISI கட்டாயமா?",
        "PVC குழாய்களுக்கான BIS தரநிலையைக் கண்டறியவும்.",
    ],
    "kn": [
        "LED ಬೀದಿ ದೀಪಗಳಿಗೆ ಯಾವ ಗುಣಮಟ್ಟ ಅನ್ವಯಿಸುತ್ತದೆ?",
        "ಹೆಲ್ಮೆಟ್‌ಗಳಿಗೆ ISI ಕಡ್ಡಾಯವೇ?",
        "PVC ಪೈಪ್‌ಗಳಿಗಾಗಿ BIS ಗುಣಮಟ್ಟವನ್ನು ಹುಡುಕಿ.",
    ],
}


def extract_is_number(query: str) -> Optional[str]:
    """Extract standard IS number if explicitly present (e.g., IS 16503:2017, IS 456, IS:4985)."""
    m = re.search(r"\bIS\s*[:\s]?\s*(\d+(?:\s*\([^)]+\))?(?::\d{4})?)\b", query, re.IGNORECASE)
    if m:
        return f"IS {m.group(1).strip()}"
    return None


def _strip_greeting_prefix(text: str) -> str:
    """Strip leading greeting phrases and bot names to see if substantive query remains."""
    cleaned = text.strip()
    for pattern in GREETING_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()

    # Also strip common addressing tokens like "manak", "there", commas, colons
    cleaned = re.sub(r"^[\s,:\-–—]+", "", cleaned).strip()
    for name in BOT_NAMES:
        cleaned = re.sub(rf"^{name}\b", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"^[\s,:\-–—]+", "", cleaned).strip()
    return cleaned


def classify_intent(message: str, session_has_standard: bool = False) -> Tuple[Intent, Dict[str, Any]]:
    """
    Classifies user message intent using deterministic rules.
    Returns (Intent, metadata).
    
    Guarantees:
    - Normal procurement queries (even starting with 'Hi, ...') will NOT be treated as greetings.
    - Pure greetings (e.g. 'hi', 'hello', 'hey', 'good morning') will NOT trigger semantic search.
    - Out-of-domain queries (e.g. 'write a python program for factorial') will NOT trigger semantic search.
    """
    raw = (message or "").strip()
    lower = raw.lower()
    meta: Dict[str, Any] = {"original_query": raw}

    # 1. Check for Out-of-domain programming / trivia queries
    is_bis_related = bool(
        re.search(r"\b(?:bis|isi|indian\s+standard|qco|standard|is\s*\d+)\b", lower, re.IGNORECASE)
    )
    if not is_bis_related:
        for pat in OUT_OF_DOMAIN_PATTERNS:
            if re.search(pat, lower, re.IGNORECASE):
                return Intent.UNKNOWN, meta

    # 2. Check for explicit IS Number
    is_num = extract_is_number(raw)
    if is_num:
        meta["is_number"] = is_num
        # Check if QCO query on this IS standard
        if any(re.search(pat, lower, re.IGNORECASE) for pat in QCO_KEYWORDS):
            return Intent.QCO_QUERY, meta
        # Check if technical specification query on this IS standard
        if any(re.search(pat, lower, re.IGNORECASE) for pat in SPEC_KEYWORDS):
            return Intent.TECHNICAL_SPECIFICATION_QUERY, meta
        # Otherwise general standard retrieval
        return Intent.BIS_STANDARD_QUERY, meta

    # 3. Check for pure greetings vs greeting + procurement query
    # Check if the query starts with a greeting
    has_greeting_start = any(re.search(pat, lower, re.IGNORECASE) for pat in GREETING_PATTERNS)
    if has_greeting_start:
        substantive = _strip_greeting_prefix(raw)
        # If substantive query remains, route the substantive query
        if substantive:
            sub_words = [w for w in re.split(r"\W+", substantive) if len(w) > 1]
            if len(sub_words) >= 2 or any(re.search(pat, substantive, re.IGNORECASE) for pat in PROCUREMENT_INDICATORS):
                # Classify the remaining query
                return _classify_domain_query(substantive, session_has_standard, meta)

        # No substantive query remaining -> Pure greeting
        meta["greeting_type"] = _detect_greeting_type(lower)
        return Intent.GREETING, meta

    # 4. Check for General Conversation (identity, capabilities, thanks, bye)
    for pat, conv_type in GENERAL_CONVERSATION_PATTERNS:
        if re.search(pat, lower, re.IGNORECASE):
            substantive = re.sub(pat, "", lower).strip()
            sub_words = [w for w in re.split(r"\W+", substantive) if len(w) > 1]
            if len(sub_words) < 2 and not any(re.search(p, substantive) for p in PROCUREMENT_INDICATORS):
                meta["conv_type"] = conv_type
                return Intent.GENERAL_CONVERSATION, meta

    # 5. Check for General Tech / Conceptual questions (e.g. API vs database, Python, machine learning)
    if not is_bis_related:
        for pat in GENERAL_TECH_CONVERSATION_PATTERNS:
            if re.search(pat, lower, re.IGNORECASE):
                meta["conv_type"] = "general_tech"
                return Intent.GENERAL_CONVERSATION, meta

    # 6. Check for Document Query
    for pat in DOCUMENT_PATTERNS:
        if re.search(pat, lower, re.IGNORECASE):
            return Intent.DOCUMENT_QUERY, meta

    # 7. Check for Domain Queries (QCO, Technical Spec, Procurement Recommendation)
    return _classify_domain_query(raw, session_has_standard, meta)


def _detect_greeting_type(text: str) -> str:
    if "good morning" in text or "सुप्रभात" in text or "காலை வணக்கம்" in text or "ಶುಭೋದಯ" in text:
        return "morning"
    if "good evening" in text:
        return "evening"
    if "good afternoon" in text:
        return "afternoon"
    if "hey" in text:
        return "hey"
    if "hello" in text:
        return "hello"
    return "hi"


def _classify_domain_query(text: str, session_has_standard: bool, meta: Dict[str, Any]) -> Tuple[Intent, Dict[str, Any]]:
    lower = text.lower()

    # QCO Query without IS number (e.g., "Is BIS certification mandatory for helmets?", "Does this product require QCO compliance?")
    if any(re.search(pat, lower, re.IGNORECASE) for pat in QCO_KEYWORDS):
        return Intent.QCO_QUERY, meta

    # Technical Spec Query without IS number (e.g. "What are the technical specifications for cement?")
    if any(re.search(pat, lower, re.IGNORECASE) for pat in SPEC_KEYWORDS):
        return Intent.TECHNICAL_SPECIFICATION_QUERY, meta

    # Follow-up query in ongoing conversation
    follow_up_triggers = ["it", "this", "that", "more", "tell me", "explain", "detail", "details", "scope", "about", "mandatory", "qco", "isi"]
    if session_has_standard and (len(text.split()) <= 8 or any(w in lower for w in follow_up_triggers)):
        return Intent.PROCUREMENT_RECOMMENDATION, meta

    # Check for explicit procurement indicators or recognized domain commodities
    has_procurement_ind = any(re.search(pat, lower, re.IGNORECASE) for pat in PROCUREMENT_INDICATORS)
    has_commodity = any(re.search(pat, lower, re.IGNORECASE) for pat in DOMAIN_COMMODITY_KEYWORDS)

    if has_procurement_ind or has_commodity:
        return Intent.PROCUREMENT_RECOMMENDATION, meta

    # Do not assume every unknown question is a BIS procurement query.
    # Questions without domain keywords route safely to GENERAL_CONVERSATION
    return Intent.GENERAL_CONVERSATION, meta


def build_conversational_response(intent: Intent, meta: Dict[str, Any], query: str, lang: str = "en") -> str:
    """Generate friendly, concise responses for non-search intents."""
    lang = (lang or "en").lower()

    if intent == Intent.GREETING:
        gtype = meta.get("greeting_type", "hi")
        if lang == "hi":
            if gtype == "morning":
                return "🌅 सुप्रभात! मैं मानक-एआई (MANAK-AI) हूँ। आज मैं भारतीय मानकों (BIS) या क्रय विनिर्देशों में आपकी क्या सहायता कर सकता हूँ?"
            if gtype == "evening":
                return "🌆 शुभ संध्या! मैं मानक-एआई (MANAK-AI) हूँ। आज मैं भारतीय मानकों (BIS) या क्रय आवश्यकताओं में आपकी क्या सहायता कर सकता हूँ?"
            return (
                "👋 नमस्ते! मैं मानक-एआई (MANAK-AI) हूँ, आपका बीआईएस एवं क्रय सह-पायलट।\n\n"
                "मैं आपकी निम्नलिखित में सहायता कर सकता हूँ:\n"
                "• लागू बीआईएस मानक खोजना\n"
                "• QCO / बीआईएस प्रमाणन आवश्यकताओं की जाँच करना\n"
                "• तकनीकी विनिर्देशों को समझना\n"
                "• क्रय आवश्यकताओं का विश्लेषण करना\n\n"
                "आप क्या देखना चाहेंगे?"
            )
        elif lang == "mr":
            return (
                "👋 नमस्कार! मी मानक-एआय (MANAK-AI) आहे, आपला बीआयएस आणि खरेदी सह-पायलट.\n\n"
                "मी खालील बाबींमध्ये मदत करू शकतो:\n"
                "• लागू बीआयएस मानके शोधणे\n"
                "• QCO / बीआयएस प्रमाणीकरण आवश्यकता तपासणे\n"
                "• तांत्रिक तपशील समजून घेणे\n"
                "• खरेदी आवश्यकतांचे विश्लेषण करणे\n\n"
                "आपण काय तपासू इच्छिता?"
            )
        elif lang == "ta":
            return (
                "👋 வணக்கம்! நான் MANAK-AI, உங்கள் BIS மற்றும் கொள்முதல் வழிகாட்டி.\n\n"
                "நான் உங்களுக்கு இதில் உதவ முடியும்:\n"
                "• பொருந்தக்கூடிய BIS தரநிலைகளைக் கண்டறிதல்\n"
                "• QCO / BIS சான்றிதழ் தேவைகளைச் சரிபார்த்தல்\n"
                "• தொழில்நுட்ப விவரக்குறிப்புகளைப் புரிந்துகொள்ளுதல்\n"
                "• கொள்முதல் தேவைகளை ஆய்வு செய்தல்\n\n"
                "நீங்கள் எதைச் சரிபார்க்க விரும்புகிறீர்கள்?"
            )
        elif lang == "kn":
            return (
                "👋 ನಮಸ್ಕಾರ! ನಾನು MANAK-AI, ನಿಮ್ಮ BIS ಮತ್ತು ಖರೀದಿ ಸಹಾಯಕ.\n\n"
                "ನಾನು ನಿಮಗೆ ಈ ಕೆಳಗಿನವುಗಳಲ್ಲಿ ಸಹಾಯ ಮಾಡಬಲ್ಲೆ:\n"
                "• ಅನ್ವಯವಾಗುವ BIS ಮಾನಕಗಳನ್ನು ಹುಡುಕುವುದು\n"
                "• QCO / BIS ಪ್ರಮಾಣೀಕರಣ ಅಗತ್ಯತೆಗಳನ್ನು ಪರಿಶೀಲಿಸುವುದು\n"
                "• ತಾಂತ್ರಿಕ ವಿವರಣೆಗಳನ್ನು ಅರ್ಥಮಾಡಿಕೊಳ್ಳುವುದು\n"
                "• ಖರೀದಿ ಅಗತ್ಯಗಳನ್ನು ವಿಶ್ಲೇಷಿಸುವುದು\n\n"
                "ನೀವು ಏನನ್ನು ಪರಿಶೀಲಿಸಲು ಬಯಸುತ್ತೀರಿ?"
            )
        else:
            if gtype == "morning":
                return "🌅 Good morning! How can I assist you with Indian Standards (BIS) or procurement specifications today?"
            if gtype == "evening":
                return "🌆 Good evening! How can I assist you with Indian Standards (BIS) or procurement requirements today?"
            if gtype == "afternoon":
                return "☀️ Good afternoon! How can I assist you with Indian Standards (BIS) or procurement requirements today?"
            if gtype == "hey":
                return "👋 Hey there! How can I help you with BIS standards or procurement today?"
            if gtype == "hello":
                return "👋 Hello! How can I assist you with Indian Standards (BIS), QCO regulations, or procurement specifications today?"
            return (
                "👋 Hello! I'm MANAK-AI, your procurement copilot.\n\n"
                "I can help you with:\n"
                "• Finding applicable BIS Standards\n"
                "• Checking QCO / BIS certification requirements\n"
                "• Understanding technical specifications\n"
                "• Analyzing procurement requirements\n\n"
                "What would you like to check?"
            )

    elif intent == Intent.GENERAL_CONVERSATION:
        ctype = meta.get("conv_type", "identity")
        if ctype == "thanks":
            if lang == "hi":
                return "आपका स्वागत है! जब भी आपको बीआईएस मानकों, QCO अनुपालन या क्रय विनिर्देशों की पुष्टि करने की आवश्यकता हो, बेझिझक पूछें।"
            return "You're welcome! Feel free to ask whenever you need help verifying BIS standards, QCO compliance, or procurement specifications."
        if ctype == "bye":
            if lang == "hi":
                return "अलविदा! भविष्य में भारतीय मानकों या क्रय से संबंधित किसी भी आवश्यकता के लिए मुझसे बेझिझक संपर्क करें।"
            return "Goodbye! Feel free to reach out whenever you need assistance with Indian Standards or procurement in the future."
        # Identity / Capabilities
        if lang == "hi":
            return (
                "मैं मानक-एआई (MANAK-AI) हूँ, भारत में सार्वजनिक खरीद के लिए भारतीय मानक ब्यूरो (BIS) और विनियामक अनुपालन में विशेषज्ञता रखने वाला आपका AI-संचालित क्रय सह-पायलट।\n\n"
                "मैं आपके लिए क्या कर सकता हूँ:\n"
                "• **बीआईएस मानक खोजें**: अपने उत्पाद या निविदा आवश्यकताओं के लिए लागू सटीक भारतीय मानकों की पहचान करें।\n"
                "• **QCO स्थिति सत्यापित करें**: जाँचें कि भारत सरकार की अधिसूचनाओं के तहत अनिवार्य ISI मार्क लागू है या नहीं।\n"
                "• **तकनीकी विनिर्देश**: मुख्य तकनीकी पैरामीटर और प्रामाणिक संदर्भ प्राप्त करें।\n"
                "• **क्रय मार्गदर्शन**: GeM पोर्टल और सरकारी निविदाओं के लिए विनिर्देशों को समझें।\n\n"
                "आप किस उत्पाद या मानक के बारे में जानना चाहते हैं?"
            )
        return (
            "I am MANAK-AI, your AI-powered procurement copilot specialized in Bureau of Indian Standards (BIS) and regulatory compliance for public procurement in India.\n\n"
            "Here is what I can do for you:\n"
            "• **Find BIS Standards**: Identify the exact Indian Standards applicable to your product or tender requirements.\n"
            "• **Verify QCO Status**: Check whether mandatory Quality Control Orders (QCO) and ISI marking apply under Government of India notifications.\n"
            "• **Technical Specifications**: Retrieve key technical parameters, test requirements, and normative reference standards.\n"
            "• **Procurement Guidance**: Explain standard clauses and compliance requirements for GeM and public tenders.\n\n"
            "What product or standard would you like to explore?"
        )

    elif intent == Intent.DOCUMENT_QUERY:
        if lang == "hi":
            return (
                "मानक-एआई में एक समर्पित **दस्तावेज़ विश्लेषण (Document Analysis)** सुविधा शामिल है। आप साइडबार में दस्तावेज़ विश्लेषण टैब के माध्यम से निविदा या अनुबंध दस्तावेज़ (.pdf, .docx, .txt) अपलोड कर सकते हैं ताकि अनिवार्य बीआईएस मानकों और QCO अनुपालन की स्वचालित जाँच की जा सके।\n\n"
                "यदि आपके पास कोई विशिष्ट क्लॉज या विनिर्देश है, तो आप उसे सीधे यहाँ चैट में भी पेस्ट कर सकते हैं।"
            )
        return (
            "MANAK-AI includes a dedicated Document Analysis feature. You can upload RFP, tender, or procurement clause documents (.pdf, .docx, .txt) via the **Document Analysis** tab in the sidebar to automatically match clauses against mandatory BIS standards and verify QCO compliance.\n\n"
            "If you have a specific excerpt or specification clause, you can also paste it directly here in the chat for analysis."
        )

    elif intent == Intent.UNKNOWN:
        if lang == "hi":
            return (
                "मैं मानक-एआई (MANAK-AI) हूँ, जो विशेष रूप से भारतीय मानक ब्यूरो (BIS) तकनीकी विनिर्देशों, गुणवत्ता नियंत्रण आदेशों (QCOs) और सार्वजनिक खरीद अनुपालन के लिए प्रशिक्षित है। मैं सामान्य प्रोग्रामिंग या असंबंधित कार्यों में सहायता नहीं कर सकता।\n\n"
                "कृपया भारतीय मानकों, उत्पाद विनिर्देशों या बीआईएस प्रमाणन आवश्यकताओं से संबंधित प्रश्न पूछें।"
            )
        return (
            "I am MANAK-AI, specialized in Bureau of Indian Standards (BIS) technical specifications, Quality Control Orders (QCOs), and public procurement compliance. I cannot assist with general programming or unrelated tasks.\n\n"
            "Please ask a question related to Indian Standards, product specifications, or BIS certification requirements."
        )

    return ""
