import pytest
from openai import OpenAIError

from app.services import ai_analysis_service
from app.services.ai_analysis_service import (
    _parse_json_response,
    analyze_transcription_with_ai,
)


def test_parse_json_response_handles_clean_json():
    result = _parse_json_response('{"sentiment": "neutro", "risk_level": "baixo"}')

    assert result == {"sentiment": "neutro", "risk_level": "baixo"}


def test_parse_json_response_extracts_json_embedded_in_text():
    raw_content = (
        "Aqui está a análise solicitada:\n"
        '{"risk_level": "moderado", "score": 4}\n'
        "Espero ter ajudado."
    )

    result = _parse_json_response(raw_content)

    assert result == {"risk_level": "moderado", "score": 4}


def test_parse_json_response_raises_value_error_when_no_json_present():
    with pytest.raises(ValueError, match="JSON válido"):
        _parse_json_response("Resposta livre, sem JSON.")


class _FakeSettings:
    openai_api_key: str | None = None
    openai_model: str = "fake-model"


def test_get_openai_client_raises_when_api_key_missing(monkeypatch):
    monkeypatch.setattr(ai_analysis_service, "_client", None)
    monkeypatch.setattr(ai_analysis_service, "settings", _FakeSettings())

    with pytest.raises(OpenAIError, match="OPENAI_API_KEY"):
        ai_analysis_service._get_openai_client()


def test_analyze_transcription_falls_back_to_local_rules_when_llm_fails(monkeypatch):
    def _raise_openai_error(_transcription):
        raise OpenAIError("api offline")

    monkeypatch.setattr(ai_analysis_service, "_analyze_with_openai", _raise_openai_error)

    result = analyze_transcription_with_ai("Sinto medo e recebi ameaça.")

    assert result["source"] == "local_fallback"
    assert result["sentiment"] == "indefinido"
    assert result["llm_error"] == "api offline"
    assert "medo" in result["detected_signals"]
    assert "ameaça" in result["detected_signals"]
    assert result["keywords"] == []


def test_analyze_transcription_returns_openai_result_when_call_succeeds(monkeypatch):
    monkeypatch.setattr(
        ai_analysis_service,
        "_analyze_with_openai",
        lambda _: {
            "risk_level": "baixo",
            "score": 1,
            "justification": "Texto neutro.",
            "recommended_action": "Nenhuma ação automática.",
        },
    )

    result = analyze_transcription_with_ai("Hoje foi um dia tranquilo.")

    assert result["source"] == "openai_llm"
    assert result["risk_level"] == "baixo"
