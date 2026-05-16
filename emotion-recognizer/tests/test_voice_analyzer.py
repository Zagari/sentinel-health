"""
Unit tests for audio.voice_analyzer — voice emotion analysis.

Tests cover:
 - Local keyword-based fallback analysis
 - LLM-based analysis (mocked)
 - Empty transcription handling
 - End-to-end analyze_voice_emotions with fallback
"""

import json
import os
import sys
import types

import pytest

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from audio.voice_analyzer import (
    analyze_voice_emotions,
    analyze_risk_locally,
    _parse_json_response,
)


# ── Schema validation helper ────────────────────────────────────────────

_REQUIRED_KEYS = {
    "source", "sentiment", "risk_level", "score",
    "summary", "keywords", "detected_signals",
    "justification", "recommended_action",
}


def _assert_valid_result(result: dict):
    """Assert the result dict has all required keys with valid types."""
    missing = _REQUIRED_KEYS - result.keys()
    assert not missing, f"Missing keys: {missing}"
    assert result["sentiment"] in ("positive", "neutral", "negative")
    assert result["risk_level"] in ("low", "moderate", "high")
    assert 0 <= result["score"] <= 10
    assert isinstance(result["keywords"], list)
    assert isinstance(result["detected_signals"], list)


# ── Local fallback tests ────────────────────────────────────────────────

class TestAnalyzeRiskLocally:
    """Tests for the keyword-based local fallback."""

    def test_neutral_text(self):
        result = analyze_risk_locally("Today was a good day at work.")
        _assert_valid_result(result)
        assert result["risk_level"] == "low"
        assert result["source"] == "local_rules"

    def test_mild_distress(self):
        result = analyze_risk_locally("I feel sad and worried about the future.")
        _assert_valid_result(result)
        assert len(result["detected_signals"]) >= 1
        assert result["score"] >= 1

    def test_moderate_distress(self):
        result = analyze_risk_locally(
            "I'm so angry and frustrated. I was crying all night."
        )
        _assert_valid_result(result)
        assert result["risk_level"] in ("moderate", "high")
        assert result["score"] >= 3

    def test_high_distress(self):
        result = analyze_risk_locally(
            "He threatened to kill me. There was violence and abuse."
        )
        _assert_valid_result(result)
        assert result["risk_level"] == "high"
        assert result["score"] >= 7

    def test_negation_cancels_signal(self):
        result_neg = analyze_risk_locally("I am not sad at all.")
        result_pos = analyze_risk_locally("I am very sad.")
        # Negated version should have lower or equal score
        assert result_neg["score"] <= result_pos["score"]

    def test_empty_text(self):
        result = analyze_risk_locally("")
        _assert_valid_result(result)
        assert result["risk_level"] == "low"
        assert result["score"] == 0


# ── JSON parsing tests ──────────────────────────────────────────────────

class TestParseJsonResponse:

    def test_clean_json(self):
        data = {"sentiment": "neutral", "score": 3}
        result = _parse_json_response(json.dumps(data))
        assert result == data

    def test_json_in_markdown(self):
        raw = '```json\n{"sentiment": "negative", "score": 7}\n```'
        result = _parse_json_response(raw)
        assert result["sentiment"] == "negative"

    def test_invalid_json(self):
        with pytest.raises(ValueError, match="not valid JSON"):
            _parse_json_response("This is not JSON at all.")


# ── End-to-end (mocked LLM) ─────────────────────────────────────────────

def test_analyze_voice_emotions_empty():
    """Empty transcription should return a 'none' source result."""
    result = analyze_voice_emotions("")
    assert result["source"] == "none"
    assert result["score"] == 0


def test_analyze_voice_emotions_mocked_llm(monkeypatch):
    """
    Full pipeline with mocked LLM — verifies the LLM path works
    and returns a properly structured result.
    """
    fake_llm_response = {
        "source": "azure_openai_llm",
        "sentiment": "negative",
        "risk_level": "moderate",
        "score": 5,
        "summary": "Speaker expresses frustration and sadness.",
        "keywords": ["frustrated", "sad", "tired"],
        "detected_signals": ["frustration", "sadness"],
        "justification": "Multiple negative emotional indicators.",
        "recommended_action": "Follow up with support.",
    }

    monkeypatch.setattr(
        "audio.voice_analyzer._analyze_with_llm",
        lambda t: fake_llm_response,
    )
    # Mock setup_openai_api to avoid needing .env
    monkeypatch.setattr(
        "audio.voice_analyzer.setup_openai_api",
        lambda: None,
    )

    result = analyze_voice_emotions("I am frustrated and tired of everything.")
    _assert_valid_result(result)
    assert result["source"] == "azure_openai_llm"
    assert result["sentiment"] == "negative"


def test_analyze_voice_emotions_llm_fallback(monkeypatch):
    """
    When LLM fails, should fall back to local analysis gracefully.
    """
    def failing_setup():
        raise ValueError("No API key")

    monkeypatch.setattr(
        "audio.voice_analyzer.setup_openai_api",
        failing_setup,
    )

    result = analyze_voice_emotions("I feel very afraid and sad.")
    _assert_valid_result(result)
    assert result["source"] == "local_rules"
    assert "llm_error" in result
    assert result["score"] >= 1
