"""LLM Provider abstraction for MANAK-AI grounded response generation.

Supports:
1. Gemini Flash (if GEMINI_API_KEY is configured)
2. OpenAI (if OPENAI_API_KEY is configured)
3. FallbackProvider (Deterministic, zero external dependency, 100% grounded in BIS database)
"""
import os
import re
import json
import logging
from typing import Dict, Any, List, Optional

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


LANGUAGE_NAMES = {
    "en": "English",
    "hi": "Hindi (हिन्दी)",
    "mr": "Marathi (मराठी)",
    "ta": "Tamil (தமிழ்)",
    "kn": "Kannada (ಕನ್ನಡ)",
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
            f"Translate only the explanations, recommendations, section titles, and guidance text.\n"
        )

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


class GeminiFlashProvider:
    """Gemini 1.5/2.0 Flash integration using Google Generative Language REST API."""

    def __init__(self, api_key: str):
        self.api_key = api_key

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


class OpenAIProvider:
    """OpenAI GPT-4o-mini integration."""

    def __init__(self, api_key: str):
        self.api_key = api_key

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


def get_llm_provider():
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key:
        return GeminiFlashProvider(gemini_key)
    openai_key = os.environ.get("OPENAI_API_KEY")
    if openai_key:
        return OpenAIProvider(openai_key)
    return FallbackProvider()

