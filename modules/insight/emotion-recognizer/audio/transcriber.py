"""
Audio transcription module — converts speech to text using apiGPTeal Whisper.

Uses the same apiGPTeal endpoint and XMerckAPIKey as the summarizer,
so no additional Azure Speech credentials are needed.

Based on audio_whisper.py.
"""

import os
import logging
import requests
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# ── Config ───────────────────────────────────────────────────────────────

_API_ROOT = "https://iapi-test.merck.com/gpt/v2"
_MODEL = "whisper-1"
_API_VERSION = "2024-10-21"


def _load_api_key() -> str:
    """Load the apiGPTeal key from .env (same key used by summarizer)."""
    env_path = os.path.join(os.path.dirname(__file__), os.pardir, ".env")
    load_dotenv(dotenv_path=os.path.abspath(env_path))

    api_key = os.getenv("XMerckAPIKey", "")
    if not api_key:
        raise ValueError(
            "API key not found. Set XMerckAPIKey in your .env file. "
            "Visit https://share.merck.com/spaces/EG/pages/1759994187/apiGPTeal+Onboarding"
        )
    return api_key


# ── Public API ───────────────────────────────────────────────────────────

def transcribe_audio(audio_path: str, language: str = "en") -> str:
    """
    Transcribe an audio file using the Whisper model via apiGPTeal.

    Supported formats: mp3, mp4, mpeg, mpga, m4a, wav, webm (max 25 MB).

    Args:
        audio_path: Path to the audio file (WAV from extractor, or any
                    Whisper-supported format).
        language:   ISO-639-1 language code (default: "en").

    Returns:
        Transcribed text string. Empty string if no speech detected.

    Raises:
        ValueError: If the API key is not configured.
        RuntimeError: If the Whisper API call fails.
    """
    api_key = _load_api_key()

    url = f"{_API_ROOT}/{_MODEL}/audio/transcriptions"
    headers = {"X-Merck-APIKey": api_key}
    params = {"api-version": _API_VERSION}
    data = {
        "response_format": "verbose_json",
        "language": language,
    }

    logger.info("Transcribing audio: %s", audio_path)

    try:
        with open(audio_path, "rb") as f:
            files = {"file": f}
            response = requests.post(
                url,
                params=params,
                headers=headers,
                files=files,
                data=data,
                timeout=120,
            )
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        detail = ""
        try:
            detail = response.json().get("error", {}).get("message", "")
        except Exception:
            detail = response.text[:200] if response.text else ""
        raise RuntimeError(
            f"Whisper API error ({response.status_code}): {detail}"
        ) from e
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Whisper API request failed: {e}") from e

    result = response.json()
    text = result.get("text", "").strip()

    detected_lang = result.get("language", language)
    logger.info(
        "Transcription complete: %d chars, language=%s",
        len(text), detected_lang,
    )

    return text
