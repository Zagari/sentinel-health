"""
Audio transcription module — converts speech to text using OpenAI Whisper.

Uses the OpenAI Python SDK directly with the OPENAI_API_KEY environment variable.
"""

import os
import logging
from openai import OpenAI
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# ── Config ───────────────────────────────────────────────────────────────

_MODEL = "whisper-1"


def _load_api_key() -> str:
    """Load the OPENAI_API_KEY from the .env file."""
    env_path = os.path.join(os.path.dirname(__file__), os.pardir, ".env")
    load_dotenv(dotenv_path=os.path.abspath(env_path))

    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise ValueError(
            "API key not found. Set OPENAI_API_KEY in your .env file. "
            "Get a key from https://platform.openai.com/api-keys"
        )
    return api_key


# ── Public API ───────────────────────────────────────────────────────────

def transcribe_audio(audio_path: str, language: str = "en") -> str:
    """
    Transcribe an audio file using the Whisper model via the OpenAI API.

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
    client = OpenAI(api_key=api_key)

    logger.info("Transcribing audio: %s", audio_path)

    try:
        with open(audio_path, "rb") as f:
            response = client.audio.transcriptions.create(
                model=_MODEL,
                file=f,
                response_format="verbose_json",
                language=language,
            )
    except Exception as e:
        raise RuntimeError(f"Whisper API request failed: {e}") from e

    text = (getattr(response, "text", "") or "").strip()
    detected_lang = getattr(response, "language", language)
    logger.info(
        "Transcription complete: %d chars, language=%s",
        len(text), detected_lang,
    )

    return text
