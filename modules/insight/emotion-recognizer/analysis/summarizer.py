"""
LLM-based emotion summarizer.
Takes the JSON payload from analyzer.py and generates a natural-language
summary of the emotions detected, using the OpenAI API.

Requirements:
- OpenAI Python library (v1.0.0 or higher)
- python-dotenv library for loading .env files
- Valid OpenAI API key stored in the OPENAI_API_KEY environment variable.
  Get a key from: https://platform.openai.com/api-keys
"""

import json
import os
import openai
from openai import OpenAI
from dotenv import load_dotenv


# Model used for chat completions (OpenAI public catalog)
_CHAT_MODEL = "gpt-5.4-nano"


def setup_openai_api():
    """Load the OPENAI_API_KEY from the .env file and configure the openai library."""
    # Load .env from the emotion-recognizer directory (where it actually lives)
    env_path = os.path.join(os.path.dirname(__file__), os.pardir, ".env")
    load_dotenv(dotenv_path=os.path.abspath(env_path))

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "API key not found. Please set OPENAI_API_KEY in your .env file. "
            "Get a key from https://platform.openai.com/api-keys"
        )
    openai.api_key = api_key

    # Check OpenAI library version
    if openai.__version__.split(".")[0] == "0":
        raise Exception(
            "Please update OpenAI library to version >=1.0.0 "
            "(pip install openai --upgrade)"
        )


_SYSTEM_PROMPT = """\
You are an expert behavioral psychologist analyzing multimodal emotion-detection data.

You will receive a JSON object with one or two sections:

1. "video_emotions" — a JSON array of per-frame face detections with fields:
   - "frame": frame number
   - "timestamp_s": time in seconds
   - "face": face index (0-based)
   - "dominant_emotion": the strongest emotion detected
   - "confidence": confidence score (0-100)

2. "voice_analysis" (optional) — a JSON object with speech analysis:
   - "sentiment": positive/neutral/negative
   - "risk_level": low/moderate/high
   - "score": 0-10 distress score
   - "summary": brief speech summary
   - "detected_signals": list of emotional signals
   - "transcription": the spoken words

Your task:
1. Identify the overall emotional tone combining video and voice data.
2. Note any significant emotional shifts or patterns over time.
3. If voice data is present, correlate speech emotions with facial expressions.
4. Note agreements or contradictions between face and voice emotions.
5. Keep the summary concise (3-6 sentences), readable, and insightful.

Respond ONLY with the natural-language summary — no JSON, no bullet points, \
no headings.\
"""


def compact_payload(export_data: list[dict]) -> list[dict]:
    """
    Reduce the full analyzer output to only the fields the LLM needs.
    Keeps: frame, timestamp_s, face, dominant_emotion, confidence.
    Drops: all_emotions, bbox (saves ~70% of token usage).
    """
    return [
        {
            "frame": r["frame"],
            "timestamp_s": r["timestamp_s"],
            "face": r["face"],
            "dominant_emotion": r["dominant_emotion"],
            "confidence": round(float(r["confidence"]), 1),
        }
        for r in export_data
    ]


# ── Token estimation ─────────────────────────────────────────────────────

_MODEL_MAX_TOKENS = 8192          # gpt-5.4-nano context window
_RESPONSE_TOKENS_RESERVE = 600    # enough for a 3-6 sentence summary


def estimate_tokens(text: str) -> int:
    """
    Estimate the number of tokens in a string using a simple heuristic.

    Rule of thumb for English + JSON:
      ~1 token ≈ 4 characters  (OpenAI's own guideline).
    We use 3.5 chars/token to be slightly conservative (overestimate).

    For exact counts, install `tiktoken` and use:
        tiktoken.encoding_for_model("gpt-4o").encode(text)
    """
    return int(len(text) / 3.5)


def compute_max_completion_tokens(system_prompt: str, user_message: str,
                                   model_limit: int = _MODEL_MAX_TOKENS,
                                   reserve: int = _RESPONSE_TOKENS_RESERVE) -> int:
    """
    Calculate the max_completion_tokens value so the request fits within
    the model's context window.

    Returns:
        max_completion_tokens — at least `reserve`, capped so
        prompt_tokens + max_completion_tokens ≤ model_limit.
    """
    prompt_tokens = estimate_tokens(system_prompt) + estimate_tokens(user_message)
    # Add ~20 tokens for message formatting overhead
    prompt_tokens += 20
    available = model_limit - prompt_tokens
    # Ensure at least `reserve` tokens for the response
    return max(available, reserve)


def create_chat_completion(user_message: str):
    """
    Create a chat completion using the configured OpenAI chat model.

    Args:
        user_message: The JSON payload string to summarize.

    Returns:
        The API response object, or None on failure.
    """
    try:
        client = OpenAI(api_key=openai.api_key)

        response = client.chat.completions.create(
            model=_CHAT_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            max_completion_tokens=compute_max_completion_tokens(
                _SYSTEM_PROMPT, user_message
            ),
        )
        # Debug: print the raw response for diagnostics
        prompt_est = estimate_tokens(_SYSTEM_PROMPT) + estimate_tokens(user_message)
        print(f"[summarizer] est_prompt_tokens={prompt_est}")
        print(f"[summarizer] max_completion_tokens="
              f"{compute_max_completion_tokens(_SYSTEM_PROMPT, user_message)}")
        print(f"[summarizer] finish_reason={response.choices[0].finish_reason}")
        print(f"[summarizer] content={response.choices[0].message.content!r}")
        return response
    except Exception as e:
        print(f"Error creating chat completion: {e}")
        return None


def extract_message_content(response) -> str:
    """
    Extract the message content from the API response.

    Args:
        response: The API response object.

    Returns:
        The extracted message content string.
    """
    content = response.choices[0].message.content
    # Some API versions return None instead of "" for empty/filtered responses
    return content if content else ""


def summarize_emotions(export_data: list[dict] | None = None,
                       voice_result: dict | None = None) -> str | None:
    """
    High-level entry point: takes the serializable video results list
    and optional voice analysis result, and returns a unified
    natural-language summary string, or None on failure.
    """
    try:
        setup_openai_api()
    except (ValueError, Exception) as e:
        return f"⚠️ LLM unavailable: {e}"

    # Build multimodal payload
    payload: dict = {}
    if export_data:
        payload["video_emotions"] = compact_payload(export_data)
    if voice_result and voice_result.get("source") != "none":
        payload["voice_analysis"] = {
            k: voice_result[k]
            for k in (
                "sentiment", "risk_level", "score", "summary",
                "detected_signals", "keywords", "transcription",
            )
            if k in voice_result
        }

    if not payload:
        return "No data to summarise."

    json_payload = json.dumps(payload, default=str)
    response = create_chat_completion(json_payload)

    if response is None:
        return None

    return extract_message_content(response)
