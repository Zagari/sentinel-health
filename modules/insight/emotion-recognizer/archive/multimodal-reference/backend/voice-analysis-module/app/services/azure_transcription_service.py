import logging
from pathlib import Path
from threading import Event

from app.core.config import settings
from app.utils.audio_converter import (
    prepare_audio_path_for_azure_speech,
    read_pcm_s16le_16k_mono_bytes,
)

TRANSCRIPTION_TIMEOUT_SECONDS = 25
logger = logging.getLogger(__name__)


def _import_speech_sdk():
    """Importa o SDK do Azure Speech sob demanda para reduzir custo de import."""
    import azure.cognitiveservices.speech as speechsdk

    return speechsdk


def _ensure_credentials_configured(file_path: str) -> tuple[str, str]:
    speech_key = settings.azure_speech_key
    speech_region = settings.azure_speech_region

    if not speech_key or not speech_region:
        logger.error(
            "Credenciais do Azure Speech ausentes",
            extra={
                "event": "transcription_failed",
                "service": "azure_speech",
                "stage": "configuration",
                "reason": "missing_credentials",
                "file_path": file_path,
            },
        )
        raise ValueError("AZURE_SPEECH_KEY ou AZURE_SPEECH_REGION não configurados.")

    return speech_key, speech_region


def _read_pcm_bytes(file_path: str) -> bytes:
    """Prepara o áudio em PCM e cuida da limpeza do WAV temporário."""
    temp_wav: Path | None = None
    try:
        wav_path, temp_wav = prepare_audio_path_for_azure_speech(file_path)
        return read_pcm_s16le_16k_mono_bytes(wav_path)
    except Exception:
        logger.exception(
            "Falha ao preparar áudio para o Azure Speech",
            extra={
                "event": "transcription_failed",
                "service": "azure_speech",
                "stage": "audio_preparation",
                "file_path": file_path,
            },
        )
        raise
    finally:
        # Apagar o WAV temporário antes do SDK abrir ficheiros: no Windows o Azure
        # mantém o handle aberto após recognize_once e unlink no fim causava WinError 32.
        if temp_wav is not None:
            try:
                temp_wav.unlink(missing_ok=True)
            except PermissionError:
                logger.warning(
                    "Não foi possível remover WAV temporário antes da transcrição",
                    extra={
                        "event": "temporary_audio_cleanup_failed",
                        "service": "azure_speech",
                        "stage": "audio_preparation",
                        "file_path": file_path,
                        "temporary_file_path": str(temp_wav),
                    },
                )


def _build_recognizer(speechsdk, speech_key: str, speech_region: str, pcm_bytes: bytes):
    speech_config = speechsdk.SpeechConfig(
        subscription=speech_key,
        region=speech_region,
    )
    speech_config.speech_recognition_language = "pt-BR"

    stream_format = speechsdk.audio.AudioStreamFormat(
        samples_per_second=16000,
        bits_per_sample=16,
        channels=1,
    )
    push_stream = speechsdk.audio.PushAudioInputStream(stream_format=stream_format)
    push_stream.write(pcm_bytes)
    push_stream.close()

    audio_config = speechsdk.audio.AudioConfig(stream=push_stream)
    return speechsdk.SpeechRecognizer(
        speech_config=speech_config,
        audio_config=audio_config,
    )


def _run_recognition(speechsdk, recognizer, file_path: str) -> str:
    recognized_texts: list[str] = []
    cancellation_error: str | None = None
    done = Event()

    def on_recognized(evt):
        if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech and evt.result.text:
            recognized_texts.append(evt.result.text)

    def on_stopped(_evt):
        done.set()

    def on_canceled(evt):
        nonlocal cancellation_error
        details = evt.result.cancellation_details
        if details.error_details:
            cancellation_error = f"Erro Azure Speech: {details.reason} - {details.error_details}"
        done.set()

    recognizer.recognized.connect(on_recognized)
    recognizer.session_stopped.connect(on_stopped)
    recognizer.canceled.connect(on_canceled)

    try:
        recognizer.start_continuous_recognition_async().get()
        finished_in_time = done.wait(timeout=TRANSCRIPTION_TIMEOUT_SECONDS)
        recognizer.stop_continuous_recognition_async().get()
    except Exception:
        logger.exception(
            "Falha ao executar a transcrição com Azure Speech",
            extra={
                "event": "transcription_failed",
                "service": "azure_speech",
                "stage": "recognition",
                "file_path": file_path,
            },
        )
        raise

    if not finished_in_time:
        logger.warning(
            "Sinal session_stopped não recebido antes do tempo limite; usando resultado parcial",
            extra={
                "event": "transcription_timeout_warning",
                "service": "azure_speech",
                "stage": "recognition",
                "reason": "timeout",
                "timeout_seconds": TRANSCRIPTION_TIMEOUT_SECONDS,
                "file_path": file_path,
                "recognized_segments": len(recognized_texts),
            },
        )

    if cancellation_error:
        logger.error(
            "Transcrição com Azure Speech foi cancelada",
            extra={
                "event": "transcription_failed",
                "service": "azure_speech",
                "stage": "recognition",
                "reason": "canceled",
                "file_path": file_path,
                "error": cancellation_error,
            },
        )
        raise RuntimeError(cancellation_error)

    return " ".join(recognized_texts).strip()


def transcribe_audio_with_azure(file_path: str) -> str:
    """Transcreve o áudio em pt-BR usando Azure Cognitive Services Speech."""
    speech_key, speech_region = _ensure_credentials_configured(file_path)
    pcm_bytes = _read_pcm_bytes(file_path)

    speechsdk = _import_speech_sdk()
    recognizer = _build_recognizer(speechsdk, speech_key, speech_region, pcm_bytes)
    return _run_recognition(speechsdk, recognizer, file_path)
