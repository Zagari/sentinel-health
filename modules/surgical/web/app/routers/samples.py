"""
Endpoints para galeria de clips de exemplo do GynSurg.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import boto3
import os
import json
from pathlib import Path

router = APIRouter()

# Configuração S3
S3_BUCKET = os.environ.get("S3_BUCKET", "surgical-detection-datasets-dev")
S3_PREFIX = "gynsurg_sample"
LOCAL_SAMPLES_DIR = Path("/tmp/gynsurg_samples")
LOCAL_SAMPLES_DIR.mkdir(exist_ok=True)

# Cache de metadados
_metadata_cache = None


class SampleClip(BaseModel):
    name: str
    category: str  # bleeding ou non_bleeding
    url: str
    size_mb: Optional[float] = None


class SampleMetadata(BaseModel):
    dataset: str
    description: str
    categories: Dict[str, Any]
    source: Dict[str, Any]


def get_s3_client():
    """Retorna cliente S3."""
    return boto3.client('s3')


@router.get("/metadata")
async def get_metadata() -> SampleMetadata:
    """Retorna metadados do dataset de exemplo."""
    global _metadata_cache

    if _metadata_cache is None:
        try:
            s3 = get_s3_client()
            response = s3.get_object(
                Bucket=S3_BUCKET,
                Key=f"{S3_PREFIX}/metadata.json"
            )
            _metadata_cache = json.loads(response['Body'].read().decode('utf-8'))
        except Exception as e:
            raise HTTPException(500, f"Erro ao carregar metadados: {str(e)}")

    return SampleMetadata(**_metadata_cache)


@router.get("/list")
async def list_samples(category: Optional[str] = None) -> List[SampleClip]:
    """Lista clips de exemplo disponíveis."""
    try:
        s3 = get_s3_client()
        clips = []

        categories = [category] if category else ["bleeding", "non_bleeding"]

        for cat in categories:
            prefix = f"{S3_PREFIX}/{cat}/"
            response = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=prefix)

            for obj in response.get('Contents', []):
                key = obj['Key']
                if key.endswith('.mp4'):
                    name = key.split('/')[-1]
                    clips.append(SampleClip(
                        name=name,
                        category=cat,
                        url=f"/api/samples/stream/{cat}/{name}",
                        size_mb=round(obj['Size'] / (1024 * 1024), 2)
                    ))

        return clips

    except Exception as e:
        raise HTTPException(500, f"Erro ao listar clips: {str(e)}")


@router.get("/stream/{category}/{filename}")
async def stream_sample(category: str, filename: str):
    """Faz streaming de um clip de exemplo."""
    from fastapi.responses import StreamingResponse

    if category not in ["bleeding", "non_bleeding"]:
        raise HTTPException(400, "Categoria inválida")

    s3_key = f"{S3_PREFIX}/{category}/{filename}"

    try:
        s3 = get_s3_client()
        response = s3.get_object(Bucket=S3_BUCKET, Key=s3_key)

        return StreamingResponse(
            response['Body'].iter_chunks(),
            media_type="video/mp4",
            headers={
                "Content-Disposition": f"inline; filename={filename}",
                "Content-Length": str(response['ContentLength'])
            }
        )

    except s3.exceptions.NoSuchKey:
        raise HTTPException(404, "Clip não encontrado")
    except Exception as e:
        raise HTTPException(500, f"Erro ao carregar clip: {str(e)}")


@router.post("/process/{category}/{filename}")
async def process_sample(
    category: str,
    filename: str,
    background_tasks: BackgroundTasks
):
    """Processa um clip de exemplo com o modelo."""
    from app.routers.video import jobs, process_video, UPLOAD_DIR
    import uuid

    if category not in ["bleeding", "non_bleeding"]:
        raise HTTPException(400, "Categoria inválida")

    s3_key = f"{S3_PREFIX}/{category}/{filename}"
    job_id = str(uuid.uuid4())

    # Baixar clip do S3 para local
    local_path = UPLOAD_DIR / f"{job_id}_{filename}"

    try:
        s3 = get_s3_client()
        s3.download_file(S3_BUCKET, s3_key, str(local_path))
    except Exception as e:
        raise HTTPException(500, f"Erro ao baixar clip: {str(e)}")

    # Iniciar processamento
    jobs[job_id] = {
        "status": "pending",
        "progress": 0,
        "source": {
            "type": "sample",
            "category": category,
            "filename": filename,
            "ground_truth": "bleeding" if category == "bleeding" else "non_bleeding"
        }
    }

    background_tasks.add_task(process_video, job_id, str(local_path))

    return {
        "job_id": job_id,
        "message": "Processamento iniciado",
        "ground_truth": category
    }


@router.get("/stats")
async def get_sample_stats():
    """Retorna estatísticas dos clips de exemplo."""
    try:
        s3 = get_s3_client()

        stats = {
            "bleeding": {"count": 0, "total_size_mb": 0},
            "non_bleeding": {"count": 0, "total_size_mb": 0}
        }

        for category in ["bleeding", "non_bleeding"]:
            prefix = f"{S3_PREFIX}/{category}/"
            response = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=prefix)

            for obj in response.get('Contents', []):
                if obj['Key'].endswith('.mp4'):
                    stats[category]["count"] += 1
                    stats[category]["total_size_mb"] += obj['Size'] / (1024 * 1024)

            stats[category]["total_size_mb"] = round(stats[category]["total_size_mb"], 2)

        return stats

    except Exception as e:
        raise HTTPException(500, f"Erro ao calcular estatísticas: {str(e)}")
