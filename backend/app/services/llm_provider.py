"""LLM Provider abstraction for MANAK-AI grounded response generation and conversational interactions.

Supports:
1. Groq (Llama 3.3 70B Versatile, OpenAI-compatible ultra-fast REST API)
2. Gemini Flash (Google Generative Language REST API)
3. OpenAI (GPT-4o-mini REST API)
4. FallbackProvider (Deterministic, zero external dependency, 100% grounded in BIS database)
"""
import os
import re
import json
import logging
from typing import Dict, Any, List, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)

GROUNDED_SYSTEM_PROMPT = """You are MANAK-AI, an expert AI Procurement Copilot for Indian Standards (BIS).
Your role is to assist procurement officers and engineers by providing strictly grounded guidance on Indian Standards.

CRITICAL RULES:
1. Answer ONLY using the retrieved BIS standards context provided.
2. NEVER hallucinate or invent IS numbers or standard titles.
3. If the context does not contain sufficient information, state clearly: "I could not verify this from the current BIS standards corpus."
4. Every response MUST strictly follow these 6 structured sections:
   Section 1 — Recommendation: IS number, Title, Category, Confidence score.
   Section 2 — Why This Matches: Retrieved specifications, matched keywords, category, and scope.
   Section 3 — Certification Status: Mandatory or Optional, Enforcement date, Applicable QCO rule.
   Section 4 — Related Standards: Normative references and related IS numbers.
   Section 5 — Evidence: Quote exact source_excerpt from the standard.
   Section 6 — Suggested Follow-up Questions: 3 contextual follow-up prompts.
"""

CONVERSATIONAL_SYSTEM_PROMPT = """You are MANAK-AI, an intelligent conversational AI assistant specializing in the Bureau of Indian Standards (BIS), Quality Control Orders (QCO), Indian Standards (IS), and public procurement specifications in India.

ROLE & BEHAVIOR:
1. For casual greetings, pleasantries, or general inquiries about your capabilities, respond in a natural, polite, concise, and professional tone.
2. Introduce yourself clearly as MANAK-AI and explain that your primary domain is helping users find applicable Indian Standards, verify mandatory QCO compliance / ISI mark rules, and understand procurement specifications.
3. For general technology, software, science, or conceptual questions (e.g. explaining APIs, databases, Python, REST, machine learning, cloud computing), answer clearly, informatively, and concisely. Do NOT invent, force, or hallucinate BIS standards for general topics that have nothing to do with Indian Standards or physical procurement.
4. Do NOT repeatedly dump a long rigid bulleted list of capabilities after every simple greeting; offer a natural, welcoming reply and invite the user to share what product, standard, or procurement specification they are working on.
5. NEVER fabricate, hallucinate, or guess Indian Standard numbers (IS numbers), titles, clauses, or legal regulations.
6. If the user asks a specific procurement or standard query (e.g. asking which standard applies to a product, or details of a standard), invite them to state the specific product, material, or standard so the system can look up verified BIS records.
7. DO NOT format casual greetings or general explanations as structured procurement recommendations. Keep conversational replies friendly and clean (1-3 short paragraphs or clean bullet points).
8. Always maintain the requested conversation language.
"""

QUERY_UNDERSTANDING_SYSTEM_PROMPT = """You are the Intent Classification and Query Understanding engine for MANAK-AI, an expert AI assistant for Indian Standards (BIS), Quality Control Orders (QCO), and technical procurement specifications.

Analyze the user's latest message in the context of recent conversation history and any active Indian Standard.

Output a strict, single-line JSON object with these keys:
1. "route": "GENERAL_CONVERSATION" or "KNOWLEDGE_REQUIRED"
   - "GENERAL_CONVERSATION":
     * Greetings, polite pleasantries, capabilities inquiry, identity inquiry, thanks, goodbyes.
     * General technical, computer science, software, or programming questions (e.g. APIs, databases, REST, Python, coding, web development, machine learning, cloud, operating systems).
     * General knowledge, math, science, trivia, or questions that do NOT ask about physical procurement goods, materials, or Indian Standards (BIS/IS/QCO).
   - "KNOWLEDGE_REQUIRED":
     * Questions about physical products, materials, manufactured goods, engineering items, or equipment (e.g. steel, cement, pipes, helmets, cookers, wires, cables, valves, paints, solar modules, etc.).
     * Questions about Indian Standards (IS), Bureau of Indian Standards (BIS), ISI mark, Quality Control Orders (QCO), mandatory certification, or testing methods.
     * Questions regarding government procurement, tender specifications, GeM compliance, or procurement clauses.
     * Contextual follow-up questions referencing a previously discussed product or standard (e.g. "Is certification mandatory?", "What is its scope?", "Tell me more").
2. "intent": One of "GREETING", "GENERAL_CONVERSATION", "PROCUREMENT_RECOMMENDATION", "QCO_QUERY", "TECHNICAL_SPECIFICATION_QUERY", "DOCUMENT_QUERY", or "UNKNOWN".
3. "search_query": If "route" is "KNOWLEDGE_REQUIRED", provide a focused search query in English optimized for vector semantic search. For contextual follow-ups, synthesize the active standard/product with the user query (e.g. "Certification requirement for high strength deformed steel bars under IS 1786"). If "route" is "GENERAL_CONVERSATION", set to null.
4. "is_contextual_follow_up": boolean, true if the message relies on or asks about the previously discussed standard/product.

CRITICAL: Return ONLY a raw JSON object. No markdown fences, no explanatory text.
"""

LANGUAGE_NAMES = {
    "en": "English",
    "hi": "Hindi (हिन्दी)",
    "mr": "Marathi (मराठी)",
    "ta": "Tamil (தமிழ்)",
    "kn": "Kannada (ಕನ್ನಡ)",
}


REQUIRED_HEADINGS = {
    "en": [
        "### Section 1 — Recommendation",
        "### Section 2 — Why This Matches",
        "### Section 3 — Certification Status",
        "### Section 4 — Related Standards",
        "### Section 5 — Evidence",
        "### Section 6 — Suggested Follow-up Questions",
    ],
    "hi": [
        "### खंड 1 — अनुशंसा",
        "### खंड 2 — यह मानक क्यों मेल खाता है",
        "### खंड 3 — प्रमाणन स्थिति",
        "### खंड 4 — संबंधित मानक",
        "### खंड 5 — आधिकारिक साक्ष्य",
        "### खंड 6 — अनुवर्ती प्रश्न",
    ],
    "mr": [
        "### विभाग 1 — शिफारस",
        "### विभाग 2 — हे मानक का जुळते",
        "### विभाग 3 — प्रमाणीकरण स्थिती",
        "### विभाग 4 — संबंधित मानके",
        "### विभाग 5 — अधिकृत पुरावा",
        "### विभाग 6 — सुचवलेले फॉलो-अप प्रश्न",
    ],
    "ta": [
        "### பிரிவு 1 — பரிந்துரை",
        "### பிரிவு 2 — இந்த தரம் ஏன் பொருந்துகிறது",
        "### பிரிவு 3 — சான்றிதழ் நிலை",
        "### பிரிவு 4 — தொடர்புடைய தரநிலைகள்",
        "### பிரிவு 5 — உத்தியோகபூர்வ ஆதாரம்",
        "### பிரிவு 6 — பரிந்துரைக்கப்பட்ட பின்தொடர் கேள்விகள்",
    ],
    "kn": [
        "### ವಿಭಾಗ 1 — ಶಿಫಾರಸು",
        "### ವಿಭಾಗ 2 — ಈ ಮಾನಕ ಏಕೆ ಹೊಂದಿಕೆಯಾಗುತ್ತದೆ",
        "### ವಿಭಾಗ 3 — ಪ್ರಮಾಣೀಕರಣ ಸ್ಥಿತಿ",
        "### ವಿಭಾಗ 4 — ಸಂಬಂಧಿತ ಮಾನಕಗಳು",
        "### ವಿಭಾಗ 5 — ಅಧಿಕೃತ ಪುರಾವೆ",
        "### ವಿಭಾಗ 6 — ಸೂಚಿಸಲಾದ ಫಾಲೋ-ಅಪ್ ಪ್ರಶ್ನೆಗಳು",
    ],
}


def _build_context_prompt(query: str, standard: Dict[str, Any], qco: Dict[str, Any],
                          related: List[str], evidence: List[Dict[str, str]],
                          confidence: int, matched_specs: List[Dict[str, str]],
                          overlapping_keywords: List[str],
                          lang: str = "en") -> str:
    specs_str = json.dumps(standard.get("specifications") or {}, indent=2)
    matched_specs_str = ", ".join([f"{m.get('field')}: {m.get('value')}" for m in matched_specs]) if matched_specs else "None specific"
    kw_str = ", ".join(overlapping_keywords[:6]) if overlapping_keywords else "General semantic match"
    related_str = ", ".join(related) if related else "None referenced"
    excerpt = evidence[0]["excerpt"] if evidence else standard.get("source_excerpt", "")
    target_lang_name = LANGUAGE_NAMES.get(lang, "English")

    lang_instruction = ""
    if lang and lang != "en":
        lang_instruction = (
            f"\nLANGUAGE INSTRUCTION:\n"
            f"Generate the response strictly in {target_lang_name}.\n"
            f"IMPORTANT: NEVER translate IS numbers (e.g., IS 456, IS 1786, IS 4985), "
            f"official Indian Standard titles, or gazette/QCO identifiers. "
            f"Translate only the explanations, recommendations, and guidance text.\n"
        )

    target_headings = REQUIRED_HEADINGS.get(lang, REQUIRED_HEADINGS["en"])
    headings_block = "\n".join(target_headings)

    return f"""USER QUERY: {query}

RETRIEVED BIS STANDARD:
- IS Number: {standard.get('is_number')}
- Title: {standard.get('title')}
- Category: {standard.get('category')} / {standard.get('sub_category') or 'General'}
- Calculated Confidence: {confidence}%
- Scope: {standard.get('scope')}
- Stored Specifications: {specs_str}
- Matched Specifications in Query: {matched_specs_str}
- Matched Overlapping Keywords: {kw_str}
- QCO Certification Status: {"Mandatory" if qco.get('mandatory') else "Optional / Standard BIS conformity"}
- QCO Enforcement Date: {qco.get('enforcement_date') or "Not Specified"}
- Applicable QCO Rule: {qco.get('rule')}
- Related Standards (Normative References): {related_str}
- Official Source Excerpt: "{excerpt}"
{lang_instruction}
REQUIRED SECTION HEADINGS:
You MUST structure the response using EXACTLY these 6 markdown headings in order:
{headings_block}

Generate the grounded response adhering strictly to the 6 required sections.
"""


class FallbackProvider:
    """Deterministic grounded response generator that never calls any external API."""

    def generate_response(self, query: str, standard: Dict[str, Any], qco: Dict[str, Any],
                          related: List[str], evidence: List[Dict[str, str]],
                          confidence: int, matched_specs: List[Dict[str, str]],
                          overlapping_keywords: List[str],
                          follow_up: List[str],
                          lang: str = "en") -> str:
        is_num = standard.get("is_number", "IS Standard")
        title = standard.get("title", "")
        category = standard.get("category", "General")
        scope = standard.get("scope", "")
        excerpt = evidence[0]["excerpt"] if evidence else (standard.get("source_excerpt") or scope)
        is_mand = qco.get("mandatory", False)
        clean_excerpt = excerpt.strip().strip('"')

        # Language-specific labels and templates
        if lang == "hi":
            # Section 1
            sec1_head = "### खंड 1 — अनुशंसा"
            sec1_body = f"आपकी क्रय आवश्यकता के लिए प्राथमिक अनुशंसित भारतीय मानक **{is_num}** — *{title}* है।"
            lbl_is = "मानक संख्या"
            lbl_title = "शीर्षक"
            lbl_cat = "श्रेणी"
            lbl_conf = "विश्वास स्कोर"

            # Section 2
            sec2_head = "### खंड 2 — यह मानक क्यों मेल खाता है"
            spec_bullets = []
            if matched_specs:
                spec_items = [f"**{m.get('field', 'पैरामीटर')}**: `{m.get('value')}`" for m in matched_specs[:4]]
                spec_bullets.append(f"- **पुनर्प्राप्त विनिर्देश:** मेल खाते पैरामीटर {', '.join(spec_items)}.")
            else:
                specs = standard.get("specifications") or {}
                if specs:
                    sample_specs = [f"**{k}**: {v}" for k, v in list(specs.items())[:3]]
                    spec_bullets.append(f"- **मुख्य विनिर्देश:** शामिल {', '.join(sample_specs)}.")
            kw_text = ", ".join(overlapping_keywords[:5]) if overlapping_keywords else "उत्पाद विवरण एवं तकनीकी शब्दावली"
            spec_bullets.append(f"- **मेल खाते कीवर्ड:** `{kw_text}`.")
            spec_bullets.append(f"- **श्रेणी संगति:** `{category}` इंजीनियरिंग मानकों के अनुरूप।")
            if scope:
                clean_scope = scope[:260] + ("..." if len(scope) > 260 else "")
                spec_bullets.append(f"- **लागू दायरा:** {clean_scope}")
            why_matches_content = "\n".join(spec_bullets)

            # Section 3
            sec3_head = "### खंड 3 — प्रमाणन स्थिति"
            status_label = "अनिवार्य (गुणवत्ता नियंत्रण आदेश / ISI मार्क आवश्यक)" if is_mand else "ऐच्छिक / मानक बीआईएस उत्पाद प्रमाणन"
            enf_date = qco.get("enforcement_date") or ("लागू व प्रवृत्त" if is_mand else "लागू नहीं")
            qco_rule = qco.get("rule", "मानक बीआईएस अनुरूपता मूल्यांकन दिशानिर्देश लागू होते हैं।")
            lbl_status = "स्थिति"
            lbl_enf = "प्रवर्तन तिथि"
            lbl_rule = "लागू नियम"

            # Section 4
            sec4_head = "### खंड 4 — संबंधित मानक"
            sec4_desc = "इस विनिर्देश पर निम्नलिखित प्रामाणिक संदर्भ एवं सहवर्ती भारतीय मानक लागू होते हैं:"
            no_related = "- *मानक अनुक्रमणिका में कोई अतिरिक्त प्रामाणिक संदर्भ सूचीबद्ध नहीं है।*"

            # Section 5 & 6
            sec5_head = "### खंड 5 — आधिकारिक साक्ष्य"
            sec6_head = "### खंड 6 — अनुवर्ती प्रश्न"

        elif lang == "mr":
            # Section 1
            sec1_head = "### विभाग 1 — शिफारस"
            sec1_body = f"आपल्या खरेदी तपशिलासाठी प्राथमिक शिफारस केलेले भारतीय मानक **{is_num}** — *{title}* आहे."
            lbl_is = "मानक क्रमांक"
            lbl_title = "शीर्षक"
            lbl_cat = "श्रेणी"
            lbl_conf = "विश्वासार्हता गुण"

            # Section 2
            sec2_head = "### विभाग 2 — हे मानक का जुळते"
            spec_bullets = []
            if matched_specs:
                spec_items = [f"**{m.get('field', 'घटक')}**: `{m.get('value')}`" for m in matched_specs[:4]]
                spec_bullets.append(f"- **प्राप्त तांत्रिक तपशील:** जुळणारे घटक {', '.join(spec_items)}.")
            else:
                specs = standard.get("specifications") or {}
                if specs:
                    sample_specs = [f"**{k}**: {v}" for k, v in list(specs.items())[:3]]
                    spec_bullets.append(f"- **मुख्य तपशील:** समाविष्ट {', '.join(sample_specs)}.")
            kw_text = ", ".join(overlapping_keywords[:5]) if overlapping_keywords else "उत्पादन वर्णन आणि तांत्रिक संज्ञा"
            spec_bullets.append(f"- **जुळणारे कीवर्ड:** `{kw_text}`.")
            spec_bullets.append(f"- **श्रेणी सुसंगतता:** `{category}` अभियांत्रिकी मानकांशी सुसंगत.")
            if scope:
                clean_scope = scope[:260] + ("..." if len(scope) > 260 else "")
                spec_bullets.append(f"- **लागू व्याप्ती:** {clean_scope}")
            why_matches_content = "\n".join(spec_bullets)

            # Section 3
            sec3_head = "### विभाग 3 — प्रमाणीकरण स्थिती"
            status_label = "अनिवार्य (गुणवत्ता नियंत्रण आदेश / ISI मार्क आवश्यक)" if is_mand else "ऐच्छिक / मानक बीआयएस उत्पादन प्रमाणीकरण"
            enf_date = qco.get("enforcement_date") or ("सक्रिय आणि लागू" if is_mand else "लागू नाही")
            qco_rule = qco.get("rule", "मानक बीआयएस अनुरूपता मूल्यांकन मार्गदर्शक तत्त्वे लागू आहेत.")
            lbl_status = "स्थिती"
            lbl_enf = "अंमलबजावणी तारीख"
            lbl_rule = "लागू नियम"

            # Section 4
            sec4_head = "### विभाग 4 — संबंधित मानके"
            sec4_desc = "या तपशिलावर खालील संदर्भ आणि सहवर्ती भारतीय मानके लागू होतात:"
            no_related = "- *मानक निर्देशांकात कोणतेही अतिरिक्त संदर्भ नमूद केलेले नाहीत.*"

            # Section 5 & 6
            sec5_head = "### विभाग 5 — अधिकृत पुरावा"
            sec6_head = "### विभाग 6 — पुढील प्रश्न"

        elif lang == "ta":
            # Section 1
            sec1_head = "### பிரிவு 1 — பரிந்துரை"
            sec1_body = f"உங்கள் கொள்முதல் தேவைக்கான முதன்மை பரிந்துரைக்கப்பட்ட இந்தியத் தரம் **{is_num}** — *{title}* ஆகும்."
            lbl_is = "IS எண்"
            lbl_title = "தலைப்பு"
            lbl_cat = "வகை"
            lbl_conf = "நம்பகத்தன்மை மதிப்பெண்"

            # Section 2
            sec2_head = "### பிரிவு 2 — இது ஏன் பொருந்துகிறது"
            spec_bullets = []
            if matched_specs:
                spec_items = [f"**{m.get('field', 'அளவுரு')}**: `{m.get('value')}`" for m in matched_specs[:4]]
                spec_bullets.append(f"- **பெறப்பட்ட விவரக்குறிப்புகள்:** பொருந்திய அளவுருக்கள் {', '.join(spec_items)}.")
            else:
                specs = standard.get("specifications") or {}
                if specs:
                    sample_specs = [f"**{k}**: {v}" for k, v in list(specs.items())[:3]]
                    spec_bullets.append(f"- **முக்கிய விவரக்குறிப்புகள்:** {', '.join(sample_specs)}.")
            kw_text = ", ".join(overlapping_keywords[:5]) if overlapping_keywords else "தயாரிப்பு விளக்கம் & தொழில்நுட்ப சொற்கள்"
            spec_bullets.append(f"- **பொருந்திய முக்கிய வார்த்தைகள்:** `{kw_text}`.")
            spec_bullets.append(f"- **வகை பொருத்தம்:** `{category}` பொறியியல் தரநிலைகளுடன் ஒத்துப்போகிறது.")
            if scope:
                clean_scope = scope[:260] + ("..." if len(scope) > 260 else "")
                spec_bullets.append(f"- **பொருந்தக்கூடிய வரம்பு:** {clean_scope}")
            why_matches_content = "\n".join(spec_bullets)

            # Section 3
            sec3_head = "### பிரிவு 3 — சான்றிதழ் நிலை"
            status_label = "கட்டாயமானது (தரக் கட்டுப்பாட்டு உத்தரவு / ISI முத்திரை தேவை)" if is_mand else "விருப்பத்தேர்வு / நிலையான BIS தயாரிப்பு சான்றிதழ்"
            enf_date = qco.get("enforcement_date") or ("செயலில் உள்ளது" if is_mand else "பொருந்தாது")
            qco_rule = qco.get("rule", "நிலையான BIS இணக்க மதிப்பீட்டு வழிகாட்டுதல்கள் பொருந்தும்.")
            lbl_status = "நிலை"
            lbl_enf = "அமலாக்க தேதி"
            lbl_rule = "பொருந்தக்கூடிய விதி"

            # Section 4
            sec4_head = "### பிரிவு 4 — தொடர்புடைய தரநிலைகள்"
            sec4_desc = "இந்த விவரக்குறிப்பிற்கு பின்வரும் சான்று குறிப்புகள் மற்றும் இந்தியத் தரநிலைகள் பொருந்தும்:"
            no_related = "- *கூடுதல் குறிப்புத் தரநிலைகள் எதுவும் பட்டியலிடப்படவில்லை.*"

            # Section 5 & 6
            sec5_head = "### பிரிவு 5 — உத்தியோகபூர்வ சான்றுகள்"
            sec6_head = "### பிரிவு 6 — அடுத்தடுத்த வினாக்கள்"

        elif lang == "kn":
            # Section 1
            sec1_head = "### ವಿಭಾಗ 1 — ಶಿಫಾರಸು"
            sec1_body = f"ನಿಮ್ಮ ಖರೀದಿ ಅಗತ್ಯಕ್ಕಾಗಿ ಪ್ರಾಥಮಿಕ ಶಿಫಾರಸು ಮಾಡಲಾದ ಭಾರತೀಯ ಮಾನಕ **{is_num}** — *{title}* ಆಗಿದೆ."
            lbl_is = "IS ಸಂಖ್ಯೆ"
            lbl_title = "ಶೀರ್ಷಿಕೆ"
            lbl_cat = "ವರ್ಗ"
            lbl_conf = "ವಿಶ್ವಾಸಾರ್ಹತೆ ಸ್ಕೋರ್"

            # Section 2
            sec2_head = "### ವಿಭಾಗ 2 — ಇದು ಏಕೆ ಹೊಂದಾಣಿಕೆಯಾಗುತ್ತದೆ"
            spec_bullets = []
            if matched_specs:
                spec_items = [f"**{m.get('field', 'ನಿಯತಾಂಕ')}**: `{m.get('value')}`" for m in matched_specs[:4]]
                spec_bullets.append(f"- **ಸ್ವೀಕರಿಸಿದ ತಾಂತ್ರಿಕ ವಿವರಣೆಗಳು:** ಹೊಂದಾಣಿಕೆಯ ನಿಯತಾಂಕಗಳು {', '.join(spec_items)}.")
            else:
                specs = standard.get("specifications") or {}
                if specs:
                    sample_specs = [f"**{k}**: {v}" for k, v in list(specs.items())[:3]]
                    spec_bullets.append(f"- **ಪ್ರಮುಖ ವಿಶೇಷಣಗಳು:** {', '.join(sample_specs)} ಒಳಗೊಂಡಿದೆ.")
            kw_text = ", ".join(overlapping_keywords[:5]) if overlapping_keywords else "ಉತ್ಪನ್ನ ವಿವರಣೆ ಮತ್ತು ತಾಂತ್ರಿಕ ನಿಯಮಗಳು"
            spec_bullets.append(f"- **ಹೊಂದಾಣಿಕೆಯ ಕೀವರ್ಡ್ಗಳು:** `{kw_text}`.")
            spec_bullets.append(f"- **ವರ್ಗ ಹೊಂದಾಣಿಕೆ:** `{category}` ಎಂಜಿನಿಯರಿಂಗ್ ಮಾನಕಗಳೊಂದಿಗೆ ಹೊಂದಿಕೊಳ್ಳುತ್ತದೆ.")
            if scope:
                clean_scope = scope[:260] + ("..." if len(scope) > 260 else "")
                spec_bullets.append(f"- **ಅನ್ವಯವಾಗುವ ವ್ಯಾಪ್ತಿ:** {clean_scope}")
            why_matches_content = "\n".join(spec_bullets)

            # Section 3
            sec3_head = "### ವಿಭಾಗ 3 — ಪ್ರಮಾಣೀಕರಣ ಸ್ಥಿತಿ"
            status_label = "ಕಡ್ಡಾಯ (ಗುಣಮಟ್ಟ ನಿಯಂತ್ರಣ ಆದೇಶ / ISI ಮಾರ್ಕ್ ಅಗತ್ಯವಿದೆ)" if is_mand else "ಐಚ್ಛಿಕ / ಸಾಮಾನ್ಯ BIS ಉತ್ಪನ್ನ ಪ್ರಮಾಣೀಕರಣ"
            enf_date = qco.get("enforcement_date") or ("ಸಕ್ರಿಯ ಮತ್ತು ಜಾರಿಯಲ್ಲಿದೆ" if is_mand else "ಅನ್ವಯಿಸುವುದಿಲ್ಲ")
            qco_rule = qco.get("rule", "ಸಾಮಾನ್ಯ BIS ಅನುಸರಣೆ ಮೌಲ್ಯಮಾಪನ ಮಾರ್ಗಸೂಚಿಗಳು ಅನ್ವಯಿಸುತ್ತವೆ.")
            lbl_status = "ಸ್ಥಿತಿ"
            lbl_enf = "ಜಾರಿ ದಿನಾಂಕ"
            lbl_rule = "ಅನ್ವಯಿಸುವ ನಿಯಮ"

            # Section 4
            sec4_head = "### ವಿಭಾಗ 4 — ಸಂಬಂಧಿತ ಮಾನಕಗಳು"
            sec4_desc = "ಈ ವಿವರಣೆಗೆ ಕೆಳಗಿನ ಉಲ್ಲೇಖಗಳು ಮತ್ತು ಸಹಾಯಕ ಭಾರತೀಯ ಮಾನಕಗಳು ಅನ್ವಯಿಸುತ್ತವೆ:"
            no_related = "- *ಯಾವುದೇ ಹೆಚ್ಚುವರಿ ಪ್ರಮಾಣಿತ ಉಲ್ಲೇಖಗಳನ್ನು ಪಟ್ಟಿ ಮಾಡಲಾಗಿಲ್ಲ.*"

            # Section 5 & 6
            sec5_head = "### ವಿಭಾಗ 5 — ಅಧಿಕೃತ ಪುರಾವೆ"
            sec6_head = "### ವಿಭಾಗ 6 — ಮುಂದಿನ ಪ್ರಶ್ನೆಗಳು"

        else:
            # Default English
            sec1_head = "### Section 1 — Recommendation"
            sec1_body = f"The primary recommended Indian Standard for your procurement requirement is **{is_num}** — *{title}*."
            lbl_is = "IS Number"
            lbl_title = "Title"
            lbl_cat = "Category"
            lbl_conf = "Confidence Score"

            sec2_head = "### Section 2 — Why This Matches"
            spec_bullets = []
            if matched_specs:
                spec_items = [f"**{m.get('field', 'Parameter')}**: `{m.get('value')}`" for m in matched_specs[:4]]
                spec_bullets.append(f"- **Retrieved Specifications:** Matched parameters {', '.join(spec_items)}.")
            else:
                specs = standard.get("specifications") or {}
                if specs:
                    sample_specs = [f"**{k}**: {v}" for k, v in list(specs.items())[:3]]
                    spec_bullets.append(f"- **Key Specifications:** Includes {', '.join(sample_specs)}.")
            kw_text = ", ".join(overlapping_keywords[:5]) if overlapping_keywords else "Product description & technical terminology"
            spec_bullets.append(f"- **Matched Keywords:** `{kw_text}`.")
            spec_bullets.append(f"- **Category Overlap:** Aligns with `{category}` engineering standards.")
            if scope:
                clean_scope = scope[:260] + ("..." if len(scope) > 260 else "")
                spec_bullets.append(f"- **Applicable Scope:** {clean_scope}")
            why_matches_content = "\n".join(spec_bullets)

            sec3_head = "### Section 3 — Certification Status"
            status_label = "Mandatory (Quality Control Order / ISI Mark Required)" if is_mand else "Optional / Standard BIS Product Certification"
            enf_date = qco.get("enforcement_date") or ("Active & Enforced" if is_mand else "N/A")
            qco_rule = qco.get("rule", "Standard BIS conformity assessment guidelines apply.")
            lbl_status = "Status"
            lbl_enf = "Enforcement Date"
            lbl_rule = "Applicable Rule"

            sec4_head = "### Section 4 — Related Standards"
            sec4_desc = "The following normative references and companion Indian Standards apply to this specification:"
            no_related = "- *No additional normative references listed in the standard index.*"

            sec5_head = "### Section 5 — Evidence"
            sec6_head = "### Section 6 — Suggested Follow-up Questions"

        # Related standards list
        if related:
            related_items = "\n".join([f"- **{ref}**" for ref in related[:5]])
        else:
            related_items = no_related

        follow_up_lines = "\n".join([f"{i+1}. {q}" for i, q in enumerate(follow_up)])

        return f"""{sec1_head}
{sec1_body}
- **{lbl_is}:** `{is_num}`
- **{lbl_title}:** {title}
- **{lbl_cat}:** {category}
- **{lbl_conf}:** {confidence}%

{sec2_head}
{why_matches_content}

{sec3_head}
- **{lbl_status}:** **{status_label}**
- **{lbl_enf}:** {enf_date}
- **{lbl_rule}:** {qco_rule}

{sec4_head}
{sec4_desc}
{related_items}

{sec5_head}
> "{clean_excerpt}"

{sec6_head}
{follow_up_lines}"""

    def generate_conversational_response(self, message: str,
                                         history: Optional[List[Dict[str, Any]]] = None,
                                         lang: str = "en",
                                         system_context: Optional[str] = None,
                                         intent: Optional[str] = None,
                                         intent_meta: Optional[Dict[str, Any]] = None) -> str:
        """Deterministic conversational response requiring zero external API."""
        from app.services.intent_router import classify_intent, build_conversational_response, Intent
        if intent is not None:
            try:
                int_obj = Intent(intent)
            except Exception:
                int_obj = Intent.GREETING
            meta = intent_meta or {}
        else:
            int_obj, meta = classify_intent(message)
        return build_conversational_response(int_obj, meta, message, lang=lang)

    def understand_query(self, message: str,
                         history: Optional[List[Dict[str, Any]]] = None,
                         last_standard: Optional[Dict[str, Any]] = None,
                         lang: str = "en") -> Dict[str, Any]:
        """Deterministic rule-based query understanding for fallback."""
        from app.services.intent_router import classify_intent, Intent
        has_std = bool(last_standard)
        intent, meta = classify_intent(message, session_has_standard=has_std)

        is_conv = intent in (Intent.GREETING, Intent.GENERAL_CONVERSATION, Intent.DOCUMENT_QUERY, Intent.UNKNOWN)
        route = "GENERAL_CONVERSATION" if is_conv else "KNOWLEDGE_REQUIRED"

        is_follow_up = False
        follow_up_triggers = ["mandatory", "qco", "isi", "certification", "scope", "specification", "test", "amendment", "it", "this", "that", "more", "tell me", "detail", "details", "about"]
        if last_standard:
            if len(message.split()) <= 8 or any(w in message.lower() for w in follow_up_triggers):
                is_follow_up = True
                search_query = f"{message} {last_standard.get('is_number', '')} {last_standard.get('title', '')}"
                is_conv = False
                route = "KNOWLEDGE_REQUIRED"
                intent = Intent.PROCUREMENT_RECOMMENDATION

        return {
            "route": route,
            "intent": intent.value,
            "search_query": search_query if route == "KNOWLEDGE_REQUIRED" else None,
            "is_contextual_follow_up": is_follow_up
        }


class GroqProvider:
    """Groq Cloud API integration using OpenAI-compatible REST API.
    
    Provides high-speed inference on Groq LPUs.
    Safe: zero secrets logged, graceful fallback on error, rate limit, or timeout.
    """

    DEFAULT_MODEL = "llama-3.3-70b-versatile"
    FALLBACK_MODEL = "openai/gpt-oss-120b"

    def __init__(self, api_key: str, model: Optional[str] = None):
        self.api_key = api_key.strip().strip('"').strip("'")
        env_model = os.environ.get("GROQ_MODEL")
        self.model = model or env_model or self.DEFAULT_MODEL
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"

    def _post_with_fallback(self, payload: dict, timeout: int = 6) -> Optional[dict]:
        """Execute request to Groq with automatic model fallback if model is 404/inaccessible."""
        import requests
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        candidate_models = [self.model]
        if self.DEFAULT_MODEL not in candidate_models:
            candidate_models.append(self.DEFAULT_MODEL)
        if self.FALLBACK_MODEL not in candidate_models:
            candidate_models.append(self.FALLBACK_MODEL)

        for attempt_model in candidate_models:
            payload["model"] = attempt_model
            try:
                res = requests.post(self.api_url, headers=headers, json=payload, timeout=timeout)
                if res.status_code == 200:
                    self.model = attempt_model  # Remember working model
                    return res.json()
                elif res.status_code == 404 and "model" in res.text:
                    logger.warning("Groq model '%s' not found (404), attempting fallback model...", attempt_model)
                    continue
                else:
                    logger.warning("Groq API error (status %d): %s", res.status_code, res.text[:150])
                    return None
            except requests.Timeout:
                logger.warning("Groq API timed out after %ds", timeout)
                return None
            except Exception as e:
                logger.warning("Groq API request failed: %s", type(e).__name__)
                return None
        return None

    def generate_response(self, query: str, standard: Dict[str, Any], qco: Dict[str, Any],
                          related: List[str], evidence: List[Dict[str, str]],
                          confidence: int, matched_specs: List[Dict[str, str]],
                          overlapping_keywords: List[str],
                          follow_up: List[str],
                          lang: str = "en") -> Optional[str]:
        """Generate polished grounded response using retrieved BIS/QCO context."""
        prompt = _build_context_prompt(
            query, standard, qco, related, evidence, confidence, matched_specs, overlapping_keywords, lang=lang
        )
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": GROUNDED_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 1024
        }
        data = self._post_with_fallback(payload, timeout=8)
        if data:
            choices = data.get("choices", [])
            if choices:
                content = choices[0].get("message", {}).get("content")
                if content and content.strip():
                    return content.strip()
        return None

    def generate_conversational_response(self, message: str,
                                         history: Optional[List[Dict[str, Any]]] = None,
                                         lang: str = "en",
                                         system_context: Optional[str] = None) -> Optional[str]:
        """Generate conversational response for greetings and general inquiries."""
        target_lang = LANGUAGE_NAMES.get(lang, "English")
        sys_prompt = system_context or CONVERSATIONAL_SYSTEM_PROMPT
        if lang and lang != "en":
            sys_prompt += (
                f"\n\nLANGUAGE INSTRUCTION:\n"
                f"You MUST respond strictly in {target_lang}. "
                f"Keep your tone polite, natural, and helpful in {target_lang}."
            )

        messages = [{"role": "system", "content": sys_prompt}]

        if history:
            for item in history[-6:]:
                role = item.get("role")
                content = item.get("content")
                if role in ("user", "assistant") and content and isinstance(content, str):
                    clean_content = content[:500] if len(content) > 500 else content
                    messages.append({"role": role, "content": clean_content})

        messages.append({"role": "user", "content": message})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.5,
            "max_tokens": 512
        }
        data = self._post_with_fallback(payload, timeout=6)
        if data:
            choices = data.get("choices", [])
            if choices:
                content = choices[0].get("message", {}).get("content")
                if content and content.strip():
                    return content.strip()
        return None

    def understand_query(self, message: str,
                         history: Optional[List[Dict[str, Any]]] = None,
                         last_standard: Optional[Dict[str, Any]] = None,
                         lang: str = "en") -> Optional[Dict[str, Any]]:
        """Classify user intent and formulate search query using Groq LLM."""
        context_parts = []
        if last_standard:
            is_num = last_standard.get("is_number", "")
            title = last_standard.get("title", "")
            context_parts.append(f"Active Discussed Standard: {is_num} — {title}")

        if history:
            recent_turns = []
            for item in history[-4:]:
                r = item.get("role", "")
                c = item.get("content", "")
                if r in ("user", "assistant") and c:
                    clean_c = c[:200].replace("\n", " ").strip()
                    recent_turns.append(f"{r.capitalize()}: {clean_c}")
            if recent_turns:
                context_parts.append("Recent Conversation:\n" + "\n".join(recent_turns))

        context_str = "\n\n".join(context_parts) if context_parts else "No previous conversation context."
        user_prompt = f"{context_str}\n\nLatest User Message: {message}\n\nJSON Classification:"

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": QUERY_UNDERSTANDING_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.0,
            "max_tokens": 350
        }
        data = self._post_with_fallback(payload, timeout=5)
        if data:
            choices = data.get("choices", [])
            if choices:
                content = choices[0].get("message", {}).get("content", "").strip()
                content = re.sub(r"^```(?:json)?\s*", "", content)
                content = re.sub(r"\s*```$", "", content).strip()
                try:
                    parsed = json.loads(content)
                    if isinstance(parsed, dict) and "route" in parsed:
                        return parsed
                except json.JSONDecodeError:
                    logger.warning("Failed to decode JSON from Groq understand_query: %s", content[:100])
        return None


class GeminiFlashProvider:
    """Gemini 1.5/2.0 Flash integration using Google Generative Language REST API."""

    def __init__(self, api_key: str):
        self.api_key = api_key.strip().strip('"').strip("'")

    def generate_response(self, query: str, standard: Dict[str, Any], qco: Dict[str, Any],
                          related: List[str], evidence: List[Dict[str, str]],
                          confidence: int, matched_specs: List[Dict[str, str]],
                          overlapping_keywords: List[str],
                          follow_up: List[str],
                          lang: str = "en") -> Optional[str]:
        import requests
        prompt = _build_context_prompt(
            query, standard, qco, related, evidence, confidence, matched_specs, overlapping_keywords, lang=lang
        )
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
        payload = {
            "system_instruction": {"parts": [{"text": GROUNDED_SYSTEM_PROMPT}]},
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 1024}
        }
        try:
            res = requests.post(url, json=payload, timeout=8)
            if res.status_code == 200:
                data = res.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts and parts[0].get("text"):
                        return parts[0]["text"]
        except Exception as e:
            logger.warning("Gemini Flash API call failed, falling back to deterministic: %s", e)
        return None

    def generate_conversational_response(self, message: str,
                                         history: Optional[List[Dict[str, Any]]] = None,
                                         lang: str = "en",
                                         system_context: Optional[str] = None) -> Optional[str]:
        import requests
        target_lang = LANGUAGE_NAMES.get(lang, "English")
        sys_prompt = system_context or CONVERSATIONAL_SYSTEM_PROMPT
        if lang and lang != "en":
            sys_prompt += f"\n\nLANGUAGE INSTRUCTION:\nGenerate response strictly in {target_lang}."

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
        contents = []
        if history:
            for item in history[-6:]:
                role = item.get("role")
                content = item.get("content")
                if content and isinstance(content, str):
                    gemini_role = "user" if role == "user" else "model"
                    contents.append({"role": gemini_role, "parts": [{"text": content[:500]}]})
        contents.append({"role": "user", "parts": [{"text": message}]})

        payload = {
            "system_instruction": {"parts": [{"text": sys_prompt}]},
            "contents": contents,
            "generationConfig": {"temperature": 0.5, "maxOutputTokens": 512}
        }
        try:
            res = requests.post(url, json=payload, timeout=8)
            if res.status_code == 200:
                data = res.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts and parts[0].get("text"):
                        return parts[0]["text"].strip()
        except Exception as e:
            logger.warning("Gemini Flash conversational call failed: %s", type(e).__name__)
        return None

    def understand_query(self, message: str,
                         history: Optional[List[Dict[str, Any]]] = None,
                         last_standard: Optional[Dict[str, Any]] = None,
                         lang: str = "en") -> Optional[Dict[str, Any]]:
        import requests

        context_parts = []
        if last_standard:
            context_parts.append(f"Active Discussed Standard: {last_standard.get('is_number')} — {last_standard.get('title')}")
        if history:
            for item in history[-4:]:
                r = item.get("role", "")
                c = item.get("content", "")
                if r in ("user", "assistant") and c:
                    context_parts.append(f"{r.capitalize()}: {c[:200].strip()}")
        context_str = "\n".join(context_parts) if context_parts else "No previous context."
        user_prompt = f"{context_str}\n\nLatest User Message: {message}\n\nJSON Classification:"

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
        payload = {
            "system_instruction": {"parts": [{"text": QUERY_UNDERSTANDING_SYSTEM_PROMPT}]},
            "contents": [{"parts": [{"text": user_prompt}]}],
            "generationConfig": {"temperature": 0.0, "maxOutputTokens": 200}
        }
        try:
            res = requests.post(url, json=payload, timeout=4)
            if res.status_code == 200:
                data = res.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts and parts[0].get("text"):
                        content = parts[0]["text"].strip()
                        content = re.sub(r"^```(?:json)?\s*", "", content)
                        content = re.sub(r"\s*```$", "", content).strip()
                        parsed = json.loads(content)
                        if isinstance(parsed, dict) and "route" in parsed:
                            return parsed
        except Exception as e:
            logger.warning("Gemini Flash understand_query call failed: %s", type(e).__name__)
        return None


class OpenAIProvider:
    """OpenAI GPT-4o-mini integration."""

    def __init__(self, api_key: str):
        self.api_key = api_key.strip().strip('"').strip("'")

    def generate_response(self, query: str, standard: Dict[str, Any], qco: Dict[str, Any],
                          related: List[str], evidence: List[Dict[str, str]],
                          confidence: int, matched_specs: List[Dict[str, str]],
                          overlapping_keywords: List[str],
                          follow_up: List[str],
                          lang: str = "en") -> Optional[str]:
        import requests
        prompt = _build_context_prompt(
            query, standard, qco, related, evidence, confidence, matched_specs, overlapping_keywords, lang=lang
        )
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": GROUNDED_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 1024
        }
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=8)
            if res.status_code == 200:
                data = res.json()
                choices = data.get("choices", [])
                if choices and choices[0].get("message", {}).get("content"):
                    return choices[0]["message"]["content"]
        except Exception as e:
            logger.warning("OpenAI API call failed, falling back to deterministic: %s", e)
        return None

    def generate_conversational_response(self, message: str,
                                         history: Optional[List[Dict[str, Any]]] = None,
                                         lang: str = "en",
                                         system_context: Optional[str] = None) -> Optional[str]:
        import requests
        target_lang = LANGUAGE_NAMES.get(lang, "English")
        sys_prompt = system_context or CONVERSATIONAL_SYSTEM_PROMPT
        if lang and lang != "en":
            sys_prompt += f"\n\nLANGUAGE INSTRUCTION:\nGenerate response strictly in {target_lang}."

        messages = [{"role": "system", "content": sys_prompt}]
        if history:
            for item in history[-6:]:
                role = item.get("role")
                content = item.get("content")
                if role in ("user", "assistant") and content and isinstance(content, str):
                    messages.append({"role": role, "content": content[:500]})
        messages.append({"role": "user", "content": message})

        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": "gpt-4o-mini",
            "messages": messages,
            "temperature": 0.5,
            "max_tokens": 512
        }
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=8)
            if res.status_code == 200:
                data = res.json()
                choices = data.get("choices", [])
                if choices and choices[0].get("message", {}).get("content"):
                    return choices[0]["message"]["content"].strip()
        except Exception as e:
            logger.warning("OpenAI conversational API call failed: %s", type(e).__name__)
        return None

    def understand_query(self, message: str,
                         history: Optional[List[Dict[str, Any]]] = None,
                         last_standard: Optional[Dict[str, Any]] = None,
                         lang: str = "en") -> Optional[Dict[str, Any]]:
        import requests

        context_parts = []
        if last_standard:
            context_parts.append(f"Active Discussed Standard: {last_standard.get('is_number')} — {last_standard.get('title')}")
        if history:
            for item in history[-4:]:
                r = item.get("role", "")
                c = item.get("content", "")
                if r in ("user", "assistant") and c:
                    context_parts.append(f"{r.capitalize()}: {c[:200].strip()}")
        context_str = "\n".join(context_parts) if context_parts else "No previous context."
        user_prompt = f"{context_str}\n\nLatest User Message: {message}\n\nJSON Classification:"

        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": QUERY_UNDERSTANDING_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.0,
            "max_tokens": 200
        }
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=4)
            if res.status_code == 200:
                data = res.json()
                choices = data.get("choices", [])
                if choices:
                    content = choices[0].get("message", {}).get("content", "").strip()
                    content = re.sub(r"^```(?:json)?\s*", "", content)
                    content = re.sub(r"\s*```$", "", content).strip()
                    parsed = json.loads(content)
                    if isinstance(parsed, dict) and "route" in parsed:
                        return parsed
        except Exception as e:
            logger.warning("OpenAI understand_query call failed: %s", type(e).__name__)
        return None


def get_llm_provider():
    """Factory function returning configured LLM provider with safe fallback.
    
    Priority:
    1. Explicit LLM_PROVIDER ('groq', 'gemini', 'openai')
    2. Implicit detection based on GROQ_API_KEY, GEMINI_API_KEY, OPENAI_API_KEY
    3. FallbackProvider (deterministic, zero external dependency)
    """
    provider_name = (os.environ.get("LLM_PROVIDER") or "").strip().lower()

    if provider_name == "groq":
        groq_key = os.environ.get("GROQ_API_KEY", "").strip()
        if groq_key:
            model = os.environ.get("GROQ_MODEL") or "llama-3.3-70b-versatile"
            return GroqProvider(groq_key, model=model)
        logger.warning("LLM_PROVIDER='groq' but GROQ_API_KEY is not configured. Falling back to FallbackProvider.")
        return FallbackProvider()

    if provider_name == "gemini":
        gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if gemini_key:
            return GeminiFlashProvider(gemini_key)
        logger.warning("LLM_PROVIDER='gemini' but GEMINI_API_KEY is not configured. Falling back to FallbackProvider.")
        return FallbackProvider()

    if provider_name == "openai":
        openai_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if openai_key:
            return OpenAIProvider(openai_key)
        logger.warning("LLM_PROVIDER='openai' but OPENAI_API_KEY is not configured. Falling back to FallbackProvider.")
        return FallbackProvider()

    if provider_name in ("fallback", "none", "off", "disabled"):
        return FallbackProvider()

    # Implicit detection only if LLM_PROVIDER is not explicitly specified
    if not provider_name:
        groq_key = os.environ.get("GROQ_API_KEY", "").strip()
        if groq_key:
            model = os.environ.get("GROQ_MODEL") or "llama-3.3-70b-versatile"
            return GroqProvider(groq_key, model=model)

        gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if gemini_key:
            return GeminiFlashProvider(gemini_key)

        openai_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if openai_key:
            return OpenAIProvider(openai_key)

    return FallbackProvider()

