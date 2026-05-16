"""
Voice emotion analysis module — analyzes transcribed speech for emotional content.

Uses the OpenAI Chat API (same configuration as summarizer.py) to analyze
the transcription, with a local keyword-based fallback if the LLM is unavailable.

Adapted from the multimodal-ai-health-monitoring project's
ai_analysis_service.py and simple_risk_analysis_service.py.
"""

import json
import logging
import re
import unicodedata

import openai
from openai import OpenAI
from analysis.summarizer import (
    setup_openai_api,
    estimate_tokens,
    compute_max_completion_tokens,
)

logger = logging.getLogger(__name__)

# ── LLM prompt for voice emotion analysis ────────────────────────────────

_VOICE_SYSTEM_PROMPT = """\
You are an expert behavioral psychologist analyzing a speech transcription \
from a video for emotional content.

Analyze the transcription below and return ONLY valid JSON with these fields:
- "sentiment": "positive", "neutral", or "negative"
- "risk_level": "low", "moderate", or "high"
- "score": integer 0-10 (0 = no emotional distress, 10 = extreme)
- "summary": short summary of the speech content and emotional tone
- "keywords": list of emotionally relevant keywords found
- "detected_signals": list of emotional signals detected (e.g., "anger", "fear", "crying", "frustration")
- "justification": brief explanation of the analysis
- "domestic violence signals": conclusion of likelyhood of evidence of emotional tone linked to potential domestic violence

Transcription:
\"\"\"<<TRANSCRIPTION>>\"\"\"\
"""


# ── LLM-based analysis ──────────────────────────────────────────────────

_JSON_OBJECT_PATTERN = re.compile(r"\{.*\}", re.DOTALL)


def _parse_json_response(content: str) -> dict:
    """Parse JSON from the LLM response, tolerant of markdown wrappers."""
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = _JSON_OBJECT_PATTERN.search(content)
        if match:
            return json.loads(match.group())
        raise ValueError(f"LLM response is not valid JSON: {content[:200]}")


def _analyze_with_llm(transcription: str) -> dict:
    """Send transcription to OpenAI for emotional analysis."""
    client = OpenAI(api_key=openai.api_key)

    prompt = _VOICE_SYSTEM_PROMPT.replace("<<TRANSCRIPTION>>", transcription)

    response = client.chat.completions.create(
        model="gpt-5.4-nano",
        messages=[{"role": "user", "content": prompt}],
        max_completion_tokens=compute_max_completion_tokens(
            _VOICE_SYSTEM_PROMPT, transcription
        ),
    )

    content = response.choices[0].message.content or ""
    result = _parse_json_response(content)
    result.setdefault("source", "openai_llm")
    return result


# ── Local fallback (keyword-based) ───────────────────────────────────────
# Adapted from simple_risk_analysis_service.py — English keyword patterns

_PATTERNS: list[tuple[str, int, str]] = [
    # Weight 3 — severe emotional distress
    (r"\bkill\b",              3, "violence"),
    (r"\bsuicid",              3, "suicidal ideation"),
    (r"\bthreat",              3, "threat"),
    (r"\bviolence\b",          3, "violence"),
    (r"\babuse\b",             3, "abuse"),
    (r"\bassault",             3, "assault"),
    (r"\bhurt me\b",           3, "physical harm"),
    (r"\bhit me\b",            3, "physical harm"),

    # Weight 2 — emotional/psychological distress
    (r"\bscream",              2, "screaming"),
    (r"\byell",                2, "yelling"),
    (r"\bcry",                 2, "crying"),
    (r"\banger\b",             2, "anger"),
    (r"\bfuriou",              2, "fury"),
    (r"\bhate\b",              2, "hatred"),
    (r"\bdesperat",            2, "desperation"),
    (r"\bpanic",               2, "panic"),
    (r"\banxious\b|\banxiety", 2, "anxiety"),
    (r"\bdepress",             2, "depression"),

    # Weight 1 — mild distress signals
    (r"\bsad\b|\bsadness\b",   1, "sadness"),
    (r"\bafraid\b|\bfear\b",   1, "fear"),
    (r"\bworr",                1, "worry"),
    (r"\bstress",              1, "stress"),
    (r"\blonely\b|\blonelin",  1, "loneliness"),
    (r"\bfrustrat",            1, "frustration"),
    (r"\bconfus",              1, "confusion"),
    (r"\btired\b|\bexhaust",   1, "exhaustion"),
    (r"\bhelp\b",              1, "plea for help"),
]

_NEGATORS = re.compile(r"\b(not|never|no|neither|nor|without|don't|doesn't|didn't|won't)\b")
_NEGATION_WINDOW = 4


def _normalize(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _is_negated(tokens: list[str], match_start: int) -> bool:
    window_start = max(0, match_start - _NEGATION_WINDOW)
    window = tokens[window_start:match_start]
    return any(_NEGATORS.fullmatch(t) for t in window)


def analyze_risk_locally(text: str) -> dict:
    """Keyword-based local fallback for voice emotion analysis."""
    normalized = _normalize(text)
    tokens = re.split(r"\W+", normalized)

    total_score = 0
    detected_signals: list[str] = []

    for pattern, weight, label in _PATTERNS:
        for m in re.finditer(pattern, normalized):
            match_token_idx = len(re.split(r"\W+", normalized[:m.start()]))
            if _is_negated(tokens, match_token_idx):
                continue
            if label not in detected_signals:
                detected_signals.append(label)
                total_score += weight
            break

    if total_score >= 7:
        risk_level = "high"
    elif total_score >= 3:
        risk_level = "moderate"
    else:
        risk_level = "low"

    sentiment = "negative" if total_score >= 3 else "neutral"

    return {
        "source": "local_rules",
        "sentiment": sentiment,
        "risk_level": risk_level,
        "score": min(total_score, 10),
        "summary": "Analysis performed using local keyword matching.",
        "keywords": detected_signals[:10],
        "detected_signals": detected_signals,
        "justification": (
            f"Detected {len(detected_signals)} emotional signal(s) "
            f"with a combined score of {total_score}."
        ),
        "recommended_action": (
            "Review flagged signals with a qualified professional."
            if risk_level != "low"
            else "No immediate action required."
        ),
    }


# ── Public API ───────────────────────────────────────────────────────────

def analyze_voice_emotions(transcription: str) -> dict:
    """
    Analyze a speech transcription for emotional content.

    Tries the OpenAI LLM first; falls back to local keyword analysis.

    Args:
        transcription: The transcribed speech text.

    Returns:
        Dict with keys: source, sentiment, risk_level, score, summary,
        keywords, detected_signals, justification, recommended_action.
        May also contain llm_error if fallback was used.
    """
    if not transcription or not transcription.strip():
        return {
            "source": "none",
            "sentiment": "neutral",
            "risk_level": "low",
            "score": 0,
            "summary": "No speech detected in the audio.",
            "keywords": [],
            "detected_signals": [],
            "justification": "Transcription was empty.",
            "recommended_action": "No action required.",
        }

    # Try LLM analysis
    try:
        setup_openai_api()
        return _analyze_with_llm(transcription)
    except Exception as e:
        logger.warning("LLM voice analysis failed, using local fallback: %s", e)
        result = analyze_risk_locally(transcription)
        result["llm_error"] = str(e)
        return result
