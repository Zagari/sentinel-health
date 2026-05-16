"""
Unit tests for audio.transcriber - Whisper API transcription via OpenAI SDK.

All tests mock the OpenAI client to avoid requiring real credentials.
"""

import os
import sys
from unittest.mock import MagicMock

import pytest

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from audio.transcriber import _load_api_key, transcribe_audio


# -- Helpers -----------------------------------------------------------------

def _patch_openai(monkeypatch, *, text: str = "Hello world", language: str = "en", raise_exc: Exception | None = None):
    """
    Replace `audio.transcriber.OpenAI` with a factory that returns a MagicMock
    whose `audio.transcriptions.create(...)` returns a fake response (or raises).
    """
    fake_response = MagicMock()
    fake_response.text = text
    fake_response.language = language

    mock_client = MagicMock()
    if raise_exc is not None:
        mock_client.audio.transcriptions.create.side_effect = raise_exc
    else:
        mock_client.audio.transcriptions.create.return_value = fake_response

    monkeypatch.setattr("audio.transcriber.OpenAI", lambda api_key=None: mock_client)
    return mock_client


# -- Credentials tests -------------------------------------------------------

def test_api_key_missing(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("audio.transcriber.load_dotenv", lambda **kw: None)
    with pytest.raises(ValueError, match="API key not found"):
        _load_api_key()


def test_api_key_loaded(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")
    monkeypatch.setattr("audio.transcriber.load_dotenv", lambda **kw: None)
    assert _load_api_key() == "test-key-123"


# -- Transcription tests (mocked SDK) ----------------------------------------

def test_transcribe_success(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "mock-key")
    monkeypatch.setattr("audio.transcriber.load_dotenv", lambda **kw: None)
    wav = tmp_path / "test.wav"
    wav.write_bytes(b"\x00" * 100)

    _patch_openai(monkeypatch, text="Hello world", language="en")

    assert transcribe_audio(str(wav)) == "Hello world"


def test_transcribe_api_error(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "mock-key")
    monkeypatch.setattr("audio.transcriber.load_dotenv", lambda **kw: None)
    wav = tmp_path / "test.wav"
    wav.write_bytes(b"\x00" * 100)

    _patch_openai(monkeypatch, raise_exc=Exception("Bad request"))

    with pytest.raises(RuntimeError, match="Whisper API request failed"):
        transcribe_audio(str(wav))


def test_transcribe_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "mock-key")
    monkeypatch.setattr("audio.transcriber.load_dotenv", lambda **kw: None)
    wav = tmp_path / "test.wav"
    wav.write_bytes(b"\x00" * 100)

    _patch_openai(monkeypatch, text="", language="en")

    assert transcribe_audio(str(wav)) == ""


def test_transcribe_missing_key(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("audio.transcriber.load_dotenv", lambda **kw: None)
    wav = tmp_path / "test.wav"
    wav.write_bytes(b"\x00" * 100)
    with pytest.raises(ValueError, match="API key not found"):
        transcribe_audio(str(wav))
