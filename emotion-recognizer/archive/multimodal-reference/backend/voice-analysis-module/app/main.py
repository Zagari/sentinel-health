import logging
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile

from app.core.config import settings
from app.core.logging import configure_logging
from app.schemas.voice_analysis_schema import AnalysisResult, VoiceAnalysisResponse
from app.services.ai_analysis_service import analyze_transcription_with_ai
from app.services.azure_transcription_service import transcribe_audio_with_azure

configure_logging()
logger = logging.getLogger(__name__)

ALLOWED_AUDIO_EXTENSIONS = frozenset({".wav", ".mp3", ".m4a", ".ogg", ".flac", ".webm"})
UPLOAD_DIR = Path("uploads")
UPLOAD_CHUNK_SIZE_BYTES = 1024 * 1024
MAX_UPLOAD_SIZE_BYTES = settings.max_upload_size_mb * 1024 * 1024

app = FastAPI(title="SafeHer Voice Analysis")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def _validate_filename_and_extension(file: UploadFile) -> str:
    name = (file.filename or "").strip()

    if not name:
        raise HTTPException(status_code=400, detail="Nome do arquivo ausente ou inválido.")

    suffix = Path(name).suffix.lower()

    if suffix not in ALLOWED_AUDIO_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_AUDIO_EXTENSIONS))
        raise HTTPException(
            status_code=400,
            detail=f"Extensão não aceita. Permitidas: {allowed}",
        )

    return name


async def _persist_upload_with_size_limit(file: UploadFile, destination: Path) -> int:
    bytes_written = 0

    with destination.open("wb") as buffer:
        while chunk := await file.read(UPLOAD_CHUNK_SIZE_BYTES):
            bytes_written += len(chunk)
            if bytes_written > MAX_UPLOAD_SIZE_BYTES:
                buffer.close()
                destination.unlink(missing_ok=True)
                size_mb = MAX_UPLOAD_SIZE_BYTES / (1024 * 1024)
                raise HTTPException(
                    status_code=413,
                    detail=f"Arquivo excede o tamanho máximo de {size_mb:.0f} MB.",
                )
            buffer.write(chunk)

    if bytes_written == 0:
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Arquivo vazio.")

    return bytes_written


@app.post("/voice-analysis", response_model=VoiceAnalysisResponse)
async def voice_analysis(file: UploadFile = File(...)) -> VoiceAnalysisResponse:
    """Recebe um áudio, transcreve com Azure Speech e retorna análise de risco."""
    filename = _validate_filename_and_extension(file)

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    suffix = Path(filename).suffix.lower()
    saved_filename = f"{uuid4()}{suffix}"
    saved_path = UPLOAD_DIR / saved_filename

    await _persist_upload_with_size_limit(file, saved_path)

    try:
        transcription = transcribe_audio_with_azure(str(saved_path))
    except Exception as error:
        logger.exception(
            "Voice analysis pipeline failed at transcription step",
            extra={
                "event": "voice_analysis_failed",
                "stage": "transcription",
                "saved_path": str(saved_path),
            },
        )
        raise HTTPException(
            status_code=502,
            detail="Falha ao transcrever o áudio.",
        ) from error

    try:
        analysis = analyze_transcription_with_ai(transcription)
    except Exception as error:
        logger.exception(
            "Voice analysis pipeline failed at analysis step",
            extra={
                "event": "voice_analysis_failed",
                "stage": "analysis",
                "saved_path": str(saved_path),
            },
        )
        raise HTTPException(
            status_code=502,
            detail="Falha ao analisar a transcrição.",
        ) from error

    return VoiceAnalysisResponse(
        original_filename=filename,
        saved_filename=saved_filename,
        saved_path=str(saved_path),
        transcription=transcription,
        analysis=AnalysisResult(**analysis),
        message="Áudio processado com sucesso",
    )
