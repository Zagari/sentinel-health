"""
Endpoints para processamento de vídeo.
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl
from typing import Optional, Dict, Any
import uuid
import subprocess
from pathlib import Path
import os

from app.services.detector import VideoDetector

router = APIRouter()

# Inicializar detector (carrega modelo)
detector = None

UPLOAD_DIR = Path("/tmp/surgical-uploads")
RESULTS_DIR = Path("/tmp/surgical-results")
UPLOAD_DIR.mkdir(exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)


def get_detector():
    """Lazy loading do detector."""
    global detector
    if detector is None:
        model_path = os.environ.get("MODEL_PATH", "models/best.pt")
        detector = VideoDetector(model_path=model_path)
    return detector


class URLRequest(BaseModel):
    url: HttpUrl


class ProcessingStatus(BaseModel):
    job_id: str
    status: str  # pending, processing, completed, failed
    progress: Optional[float] = None
    result_url: Optional[str] = None
    report_url: Optional[str] = None
    detections: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# Armazenamento de jobs (em produção, usar Redis ou DB)
jobs: Dict[str, Dict] = {}


@router.post("/upload")
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """Upload de vídeo para processamento."""
    valid_extensions = ('.mp4', '.avi', '.mov', '.mkv', '.webm')
    if not file.filename.lower().endswith(valid_extensions):
        raise HTTPException(400, f"Formato não suportado. Use: {', '.join(valid_extensions)}")

    job_id = str(uuid.uuid4())
    file_path = UPLOAD_DIR / f"{job_id}_{file.filename}"

    # Salvar arquivo
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Iniciar processamento em background
    jobs[job_id] = {"status": "pending", "progress": 0}
    background_tasks.add_task(process_video, job_id, str(file_path))

    return {"job_id": job_id, "message": "Processamento iniciado"}


@router.post("/url")
async def process_url(
    background_tasks: BackgroundTasks,
    request: URLRequest
):
    """Processar vídeo a partir de URL."""
    job_id = str(uuid.uuid4())
    file_path = UPLOAD_DIR / f"{job_id}_video.mp4"

    jobs[job_id] = {"status": "downloading", "progress": 0}

    try:
        # Usar yt-dlp para baixar (funciona com YouTube e outras fontes)
        result = subprocess.run([
            "yt-dlp", "-f", "best[height<=720]",
            "-o", str(file_path),
            str(request.url)
        ], capture_output=True, text=True, timeout=300)

        if result.returncode != 0:
            raise HTTPException(400, f"Erro ao baixar vídeo: {result.stderr[:200]}")

    except subprocess.TimeoutExpired:
        jobs[job_id] = {"status": "failed", "error": "Timeout ao baixar vídeo"}
        raise HTTPException(408, "Timeout ao baixar vídeo")
    except FileNotFoundError:
        jobs[job_id] = {"status": "failed", "error": "yt-dlp não instalado"}
        raise HTTPException(500, "yt-dlp não está instalado no servidor")

    jobs[job_id] = {"status": "pending", "progress": 0}
    background_tasks.add_task(process_video, job_id, str(file_path))

    return {"job_id": job_id, "message": "Download concluído, processamento iniciado"}


@router.get("/status/{job_id}")
async def get_status(job_id: str):
    """Verificar status do processamento."""
    if job_id not in jobs:
        raise HTTPException(404, "Job não encontrado")

    return ProcessingStatus(job_id=job_id, **jobs[job_id])


@router.get("/result/{job_id}/video")
async def get_result_video(job_id: str):
    """Baixar vídeo processado com anotações."""
    result_path = RESULTS_DIR / f"{job_id}_annotated.mp4"
    if not result_path.exists():
        raise HTTPException(404, "Vídeo processado não encontrado")

    return FileResponse(
        str(result_path),
        media_type="video/mp4",
        filename=f"surgical_detection_{job_id}.mp4"
    )


@router.get("/result/{job_id}/report")
async def get_result_report(job_id: str):
    """Baixar relatório JSON."""
    report_path = RESULTS_DIR / f"{job_id}_detections.json"
    if not report_path.exists():
        raise HTTPException(404, "Relatório não encontrado")

    return FileResponse(
        str(report_path),
        media_type="application/json",
        filename=f"surgical_report_{job_id}.json"
    )


async def process_video(job_id: str, video_path: str):
    """Processa vídeo em background."""
    try:
        jobs[job_id]["status"] = "processing"

        det = get_detector()
        result = det.process_video(
            video_path=video_path,
            output_dir=str(RESULTS_DIR),
            job_id=job_id,
            progress_callback=lambda p: jobs[job_id].update({"progress": p})
        )

        jobs[job_id].update({
            "status": "completed",
            "progress": 100,
            "result_url": f"/api/video/result/{job_id}/video",
            "report_url": f"/api/video/result/{job_id}/report",
            "detections": result["summary"]
        })

    except Exception as e:
        jobs[job_id].update({
            "status": "failed",
            "error": str(e)
        })
