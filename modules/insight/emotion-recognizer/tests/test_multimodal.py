"""
Unit tests for the multimodal integration — verifies that visualizer
and summarizer correctly handle the combined video + voice data.
"""

import json
import os
import sys
import types

import pytest

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from analysis.summarizer import (
    compact_payload,
    summarize_emotions,
)


# ── Fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def video_results() -> list[dict]:
    """Minimal video analysis results."""
    return [
        {
            "frame": 0, "timestamp_s": 0.0, "face": 0,
            "dominant_emotion": "neutral", "confidence": 75.0,
            "all_emotions": {"neutral": 75.0, "happy": 10.0, "sad": 15.0},
            "bbox": {"x": 100, "y": 50, "w": 120, "h": 120},
        },
        {
            "frame": 10, "timestamp_s": 0.33, "face": 0,
            "dominant_emotion": "sad", "confidence": 60.0,
            "all_emotions": {"neutral": 20.0, "happy": 5.0, "sad": 60.0},
            "bbox": {"x": 105, "y": 52, "w": 118, "h": 118},
        },
    ]


@pytest.fixture
def voice_result() -> dict:
    """Minimal voice analysis result."""
    return {
        "source": "openai_llm",
        "sentiment": "negative",
        "risk_level": "moderate",
        "score": 5,
        "summary": "Speaker expresses frustration.",
        "keywords": ["frustrated", "tired"],
        "detected_signals": ["frustration", "exhaustion"],
        "justification": "Negative emotional indicators detected.",
        "recommended_action": "Follow up recommended.",
        "transcription": "I'm frustrated and tired of everything.",
    }


def _fake_response(content: str):
    msg = types.SimpleNamespace(content=content)
    choice = types.SimpleNamespace(message=msg, finish_reason="stop")
    return types.SimpleNamespace(choices=[choice])


# ── Summarizer multimodal tests ──────────────────────────────────────────

def test_summarize_video_only(video_results, monkeypatch):
    """summarize_emotions should work with video data only (no voice)."""
    expected = "The subject appears neutral with hints of sadness."

    monkeypatch.setattr(
        "analysis.summarizer.create_chat_completion",
        lambda msg: _fake_response(expected),
    )
    monkeypatch.setattr(
        "analysis.summarizer.setup_openai_api", lambda: None,
    )

    result = summarize_emotions(video_results, voice_result=None)
    assert result == expected


def test_summarize_multimodal(video_results, voice_result, monkeypatch):
    """summarize_emotions should include both video and voice data."""
    expected = "Both facial and voice analysis indicate negative emotions."

    call_payloads = []

    def mock_completion(msg):
        call_payloads.append(msg)
        return _fake_response(expected)

    monkeypatch.setattr(
        "analysis.summarizer.create_chat_completion", mock_completion,
    )
    monkeypatch.setattr(
        "analysis.summarizer.setup_openai_api", lambda: None,
    )

    result = summarize_emotions(video_results, voice_result=voice_result)
    assert result == expected

    # Verify the payload sent to the LLM contains both sections
    payload = json.loads(call_payloads[0])
    assert "video_emotions" in payload
    assert "voice_analysis" in payload
    assert payload["voice_analysis"]["sentiment"] == "negative"
    assert len(payload["video_emotions"]) == 2


def test_summarize_multimodal_empty_voice(video_results, monkeypatch):
    """When voice source is 'none', voice_analysis should be excluded."""
    expected = "Only video emotions detected."

    call_payloads = []

    def mock_completion(msg):
        call_payloads.append(msg)
        return _fake_response(expected)

    monkeypatch.setattr(
        "analysis.summarizer.create_chat_completion", mock_completion,
    )
    monkeypatch.setattr(
        "analysis.summarizer.setup_openai_api", lambda: None,
    )

    empty_voice = {"source": "none", "sentiment": "neutral"}
    result = summarize_emotions(video_results, voice_result=empty_voice)

    payload = json.loads(call_payloads[0])
    assert "video_emotions" in payload
    assert "voice_analysis" not in payload


# ── Compact payload still works ──────────────────────────────────────────

def test_compact_payload_keys(video_results):
    compacted = compact_payload(video_results)
    allowed = {"frame", "timestamp_s", "face", "dominant_emotion", "confidence"}
    for entry in compacted:
        assert set(entry.keys()) == allowed
