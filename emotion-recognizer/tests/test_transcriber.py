"""
Unit tests for audio.transcriber - Whisper API transcription.

All tests mock the HTTP calls to avoid requiring real credentials.
"""

import os
import sys

import pytest

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from audio.transcriber import _load_api_key, transcribe_audio


# -- Credentials tests -------------------------------------------------------

def test_api_key_missing(monkeypatch):
    monkeypatch.delenv("XMerckAPIKey", raising=False)
    monkeypatch.setattr("audio.transcriber.load_dotenv", lambda **kw: None)
    with pytest.raises(ValueError, match="API key not found"):
        _load_api_key()


def test_api_key_loaded(monkeypatch):
    monkeypatch.setenv("XMerckAPIKey", "test-key-123")
    monkeypatch.setattr("audio.transcriber.load_dotenv", lambda **kw: None)
    assert _load_api_key() == "test-key-123"


# -- Transcription tests (mocked HTTP) ---------------------------------------

def test_transcribe_success(tmp_path, monkeypatch):
    monkeypatch.setenv("XMerckAPIKey", "mock-key")
    monkeypatch.setattr("audio.transcriber.load_dotenv", lambda **kw: None)
    wav = tmp_path / "test.wav"
    wav.write_bytes(b"\x00" * 100)

    class FakeResp:
        status_code = 200
        def raise_for_status(self): pass
        def json(self): return {"text": "Hello world", "language": "en"}

    monkeypatch.setattr("audio.transcriber.requests.post", lambda *a, **kw: FakeResp())
    assert transcribe_audio(str(wav)) == "Hello world"


def test_transcribe_http_error(tmp_path, monkeypatch):
    monkeypatch.setenv("XMerckAPIKey", "mock-key")
    monkeypatch.setattr("audio.transcriber.load_dotenv", lambda **kw: None)
    wav = tmp_path / "test.wav"
    wav.write_bytes(b"\x00" * 100)

    import requests as req

    class FakeResp:
        status_code = 400
        text = '{"error":{"message":"Bad request"}}'
        def raise_for_status(self):
            raise req.exceptions.HTTPError(response=self)
        def json(self): return {"error": {"message": "Bad request"}}

    monkeypatch.setattr("audio.transcriber.requests.post", lambda *a, **kw: FakeResp())
    with pytest.raises(RuntimeError, match="Whisper API error"):
        transcribe_audio(str(wav))


def test_transcribe_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("XMerckAPIKey", "mock-key")
    monkeypatch.setattr("audio.transcriber.load_dotenv", lambda **kw: None)
    wav = tmp_path / "test.wav"
    wav.write_bytes(b"\x00" * 100)

    class FakeResp:
        status_code = 200
        def raise_for_status(self): pass
        def json(self): return {"text": "", "language": "en"}

    monkeypatch.setattr("audio.transcriber.requests.post", lambda *a, **kw: FakeResp())
    assert transcribe_audio(str(wav)) == ""


def test_transcribe_missing_key(tmp_path, monkeypatch):
    monkeypatch.delenv("XMerckAPIKey", raising=False)
    monkeypatch.setattr("audio.transcriber.load_dotenv", lambda **kw: None)
    wav = tmp_path / "test.wav"
    wav.write_bytes(b"\x00" * 100)
    with pytest.raises(ValueError, match="API key not found"):
        transcribe_audio(str(wav))
