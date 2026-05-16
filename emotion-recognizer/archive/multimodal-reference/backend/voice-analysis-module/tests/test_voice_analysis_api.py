import importlib
import sys
from types import ModuleType

from fastapi.testclient import TestClient


def _load_main_with_fake_services():
    sys.modules.pop("app.main", None)

    azure_service = ModuleType("app.services.azure_transcription_service")
    azure_service.transcribe_audio_with_azure = lambda saved_path: "transcrição fake"

    ai_service = ModuleType("app.services.ai_analysis_service")
    ai_service.analyze_transcription_with_ai = lambda transcription: {
        "source": "fake_service",
        "risk_level": "baixo",
        "score": 0,
        "justification": "Análise fake para teste.",
        "recommended_action": "Nenhuma ação automática.",
        "sentiment": "neutro",
        "summary": transcription,
        "keywords": [],
        "detected_signals": [],
        "llm_error": None,
    }

    sys.modules["app.services.azure_transcription_service"] = azure_service
    sys.modules["app.services.ai_analysis_service"] = ai_service

    return importlib.import_module("app.main")


def test_voice_analysis_rejects_unsupported_file_extension():
    main = _load_main_with_fake_services()

    client = TestClient(main.app)
    response = client.post(
        "/voice-analysis",
        files={"file": ("document.txt", b"not audio", "text/plain")},
    )

    assert response.status_code == 400
    assert "Extensão não aceita" in response.json()["detail"]


def test_voice_analysis_rejects_empty_audio_file():
    main = _load_main_with_fake_services()

    client = TestClient(main.app)
    response = client.post(
        "/voice-analysis",
        files={"file": ("empty.wav", b"", "audio/wav")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Arquivo vazio."


def test_voice_analysis_accepts_audio_upload_with_mocked_services(monkeypatch, tmp_path):
    main = _load_main_with_fake_services()
    monkeypatch.setattr(main, "UPLOAD_DIR", tmp_path)
    monkeypatch.setattr(
        main,
        "transcribe_audio_with_azure",
        lambda saved_path: "Tenho medo e preciso de ajuda.",
    )
    monkeypatch.setattr(
        main,
        "analyze_transcription_with_ai",
        lambda transcription: {
            "source": "test_double",
            "risk_level": "moderado",
            "score": 4,
            "justification": "Texto de teste com sinal de alerta.",
            "recommended_action": "Encaminhar para revisão humana.",
            "sentiment": "negativo",
            "summary": "Pedido de ajuda.",
            "keywords": ["medo"],
            "detected_signals": ["medo"],
            "llm_error": None,
        },
    )

    client = TestClient(main.app)
    response = client.post(
        "/voice-analysis",
        files={"file": ("relato.wav", b"fake audio bytes", "audio/wav")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["original_filename"] == "relato.wav"
    assert body["transcription"] == "Tenho medo e preciso de ajuda."
    assert body["analysis"]["source"] == "test_double"
    assert body["message"] == "Áudio processado com sucesso"
    assert (tmp_path / body["saved_filename"]).read_bytes() == b"fake audio bytes"


def test_voice_analysis_rejects_file_larger_than_limit(monkeypatch, tmp_path):
    main = _load_main_with_fake_services()
    monkeypatch.setattr(main, "UPLOAD_DIR", tmp_path)
    monkeypatch.setattr(main, "MAX_UPLOAD_SIZE_BYTES", 4)

    client = TestClient(main.app)
    response = client.post(
        "/voice-analysis",
        files={"file": ("relato.wav", b"this exceeds the limit", "audio/wav")},
    )

    assert response.status_code == 413
    assert "tamanho máximo" in response.json()["detail"]
    assert list(tmp_path.iterdir()) == []


def test_voice_analysis_returns_502_when_transcription_fails(monkeypatch, tmp_path):
    main = _load_main_with_fake_services()
    monkeypatch.setattr(main, "UPLOAD_DIR", tmp_path)

    def _raise_transcription_error(_saved_path):
        raise RuntimeError("azure offline")

    monkeypatch.setattr(main, "transcribe_audio_with_azure", _raise_transcription_error)

    client = TestClient(main.app)
    response = client.post(
        "/voice-analysis",
        files={"file": ("relato.wav", b"audio bytes", "audio/wav")},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "Falha ao transcrever o áudio."


def test_voice_analysis_returns_502_when_analysis_fails(monkeypatch, tmp_path):
    main = _load_main_with_fake_services()
    monkeypatch.setattr(main, "UPLOAD_DIR", tmp_path)
    monkeypatch.setattr(
        main,
        "transcribe_audio_with_azure",
        lambda saved_path: "transcrição válida",
    )

    def _raise_analysis_error(_transcription):
        raise RuntimeError("openai offline")

    monkeypatch.setattr(main, "analyze_transcription_with_ai", _raise_analysis_error)

    client = TestClient(main.app)
    response = client.post(
        "/voice-analysis",
        files={"file": ("relato.wav", b"audio bytes", "audio/wav")},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "Falha ao analisar a transcrição."
