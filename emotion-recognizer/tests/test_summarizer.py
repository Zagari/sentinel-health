"""
Pytest suite for analysis.summarizer — diagnoses API-key, payload,
and end-to-end LLM summarization issues.

Testing approach:
 1. test_env_file_exists          — confirms .env is where summarizer expects it.
 2. test_api_key_loads            — verifies setup_openai_api() populates openai.api_key.
 3. test_json_payload_loads       — ensures emotion_results.json is valid input.
 4. test_summarize_mocked         — mocks the LLM call so the full pipeline runs
                                    deterministically without network access (CI-safe).
 5. test_summarize_live           — real API call with the JSON payload; marked
                                    with @pytest.mark.live so CI can skip it.
"""

import json
import os
import sys
import types

import pytest

# Make the emotion-recognizer package importable
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from analysis.summarizer import (
    setup_openai_api,
    create_chat_completion,
    extract_message_content,
    summarize_emotions,
    compact_payload,
)

# ── Fixtures ─────────────────────────────────────────────────────────────

_JSON_PATH = os.path.join(_PROJECT_ROOT, "archive", "emotion_results.json")


@pytest.fixture
def emotion_payload() -> list[dict]:
    """Load the real emotion_results.json as a Python list."""
    assert os.path.isfile(_JSON_PATH), f"Missing test fixture: {_JSON_PATH}"
    with open(_JSON_PATH, encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, list) and len(data) > 0
    return data


# ── 1. Environment / config tests ────────────────────────────────────────

def test_env_file_exists():
    """The .env file must exist in emotion-recognizer/ for load_dotenv to work."""
    env_path = os.path.join(_PROJECT_ROOT, ".env")
    assert os.path.isfile(env_path), (
        f".env not found at {env_path}. "
        "Create it with: XMerckAPIKey=<your-key>"
    )


def test_api_key_loads():
    """setup_openai_api() should load a non-empty API key from .env."""
    import openai as _openai

    setup_openai_api()

    assert _openai.api_key is not None, "openai.api_key is None after setup"
    assert len(_openai.api_key) > 0, "openai.api_key is empty after setup"
    assert _openai.azure_endpoint, "azure_endpoint not set"
    assert _openai.api_version, "api_version not set"


# ── 2. Payload validation ────────────────────────────────────────────────

def test_json_payload_loads(emotion_payload):
    """emotion_results.json must deserialize and have the expected schema."""
    required_keys = {
        "frame", "timestamp_s", "face",
        "dominant_emotion", "confidence", "all_emotions", "bbox",
    }
    for entry in emotion_payload:
        missing = required_keys - entry.keys()
        assert not missing, f"Entry missing keys: {missing}"


def test_payload_serializes_for_llm(emotion_payload):
    """The payload must be JSON-serializable (no numpy leftovers)."""
    json_str = json.dumps(emotion_payload, indent=2)
    assert len(json_str) > 100, "Serialized payload suspiciously short"


def test_compact_payload(emotion_payload):
    """compact_payload should keep only the 5 essential fields and reduce size."""
    compacted = compact_payload(emotion_payload)
    assert len(compacted) == len(emotion_payload)
    allowed_keys = {"frame", "timestamp_s", "face", "dominant_emotion", "confidence"}
    for entry in compacted:
        assert set(entry.keys()) == allowed_keys, f"Unexpected keys: {entry.keys()}"
        assert "all_emotions" not in entry
        assert "bbox" not in entry
    # Verify significant size reduction
    full_size = len(json.dumps(emotion_payload))
    compact_size = len(json.dumps(compacted))
    assert compact_size < full_size * 0.5, (
        f"Compacted payload not small enough: {compact_size} vs {full_size}"
    )


# ── 3. Mocked end-to-end (deterministic, CI-safe) ────────────────────────

def _fake_response(content: str = "The subject appears mostly neutral."):
    """Build a minimal object that looks like an OpenAI ChatCompletion."""
    msg = types.SimpleNamespace(content=content)
    choice = types.SimpleNamespace(message=msg)
    return types.SimpleNamespace(choices=[choice])


def test_summarize_mocked(emotion_payload, monkeypatch):
    """
    Full pipeline with a mocked LLM call.
    Verifies that summarizer correctly:
      - calls setup_openai_api
      - serializes the payload
      - invokes create_chat_completion
      - extracts the content string
    """
    expected_summary = "The subject displays a mix of neutral and fearful emotions."

    # Mock create_chat_completion to return a fake response
    monkeypatch.setattr(
        "analysis.summarizer.create_chat_completion",
        lambda msg: _fake_response(expected_summary),
    )

    result = summarize_emotions(emotion_payload)

    assert result is not None, "summarize_emotions returned None"
    assert result == expected_summary


def test_summarize_returns_warning_on_missing_key(monkeypatch):
    """If the API key is missing, summarize_emotions should return a warning string."""
    # Temporarily remove the key from env
    monkeypatch.delenv("XMerckAPIKey", raising=False)
    # Also force load_dotenv to not re-read cached value
    monkeypatch.setattr(
        "analysis.summarizer.load_dotenv",
        lambda **kw: None,
    )
    import openai as _openai
    monkeypatch.setattr(_openai, "api_key", None)

    result = summarize_emotions([{"dummy": True}])

    assert result is not None
    assert "LLM unavailable" in result or "API key not found" in result


def test_extract_message_content():
    """extract_message_content should pull .choices[0].message.content."""
    fake = _fake_response("hello world")
    assert extract_message_content(fake) == "hello world"


# ── 4. Live API test (opt-in) ────────────────────────────────────────────

@pytest.mark.live
def test_summarize_live(emotion_payload):
    """
    Real API call — run with:  pytest -m live
    Skipped by default in CI.

    This is the test that directly diagnoses "check api key" issues.
    If this fails, the problem is API key / network / endpoint config.
    """
    result = summarize_emotions(emotion_payload)

    assert result is not None, (
        "summarize_emotions returned None. "
        "Check terminal output for 'Error creating chat completion' details."
    )
    assert "LLM unavailable" not in result, f"API key issue: {result}"
    assert len(result) > 20, f"Summary suspiciously short: {result}"
    print(f"\n✅ Live LLM summary:\n{result}")
