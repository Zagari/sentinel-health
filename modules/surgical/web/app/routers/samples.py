"""
Endpoints para galeria de clips de exemplo do GynSurg.

Estratégia de dados:
- **Primário**: bucket S3 (`S3_BUCKET/S3_PREFIX/...`). Mais conveniente quando
  o host tem AWS CLI configurado e/ou roda em EC2 com IAM Role.
- **Fallback**: diretório local montado em `LOCAL_SAMPLES_PATH`, com estrutura:
      LOCAL_SAMPLES_PATH/bleeding/*.mp4
      LOCAL_SAMPLES_PATH/non_bleeding/*.mp4
      LOCAL_SAMPLES_PATH/metadata.json   (opcional)

Toda chamada tenta S3 primeiro. Se levantar qualquer exceção (NoCredentials,
AccessDenied, conexão recusada, etc.), usa o filesystem local se disponível.
Senão, falha com 503 detalhando o erro — o frontend distingue 503 (galeria
indisponível, mensagem amigável) de 500 (falha real).

Isso permite que o mesmo container funcione tanto numa máquina com creds AWS
sem clips locais quanto num servidor com os clips no disco e sem AWS CLI.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import boto3
import os
import shutil
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Configuração ────────────────────────────────────────────────────────────

S3_BUCKET = os.environ.get("S3_BUCKET", "surgical-detection-datasets-dev")
S3_PREFIX = "gynsurg_sample"

# Pasta local com os mesmos clips (fallback quando S3 falha).
# Estrutura esperada: bleeding/ e non_bleeding/ subdirs com .mp4 dentro.
LOCAL_SAMPLES_PATH = Path(os.environ.get("LOCAL_SAMPLES_PATH", "/data/gynsurg_sample"))

CATEGORIES = ("bleeding", "non_bleeding")

# Cache de metadados (apenas para resposta S3 — local sempre lê do disco)
_metadata_cache: Optional[Dict[str, Any]] = None


# ── Models ─────────────────────────────────────────────────────────────────

class SampleClip(BaseModel):
    name: str
    category: str
    url: str
    size_mb: Optional[float] = None
    source: Optional[str] = None  # "s3" ou "local" — útil pro frontend opcional


class SampleMetadata(BaseModel):
    dataset: str
    description: str
    categories: Dict[str, Any]
    source: Dict[str, Any]


# ── Helpers — modo local ────────────────────────────────────────────────────

def _local_available() -> bool:
    """True se LOCAL_SAMPLES_PATH existe e contém pelo menos uma das categorias."""
    return LOCAL_SAMPLES_PATH.is_dir() and any(
        (LOCAL_SAMPLES_PATH / cat).is_dir() for cat in CATEGORIES
    )


def _list_local(category: Optional[str]) -> List[SampleClip]:
    cats = [category] if category else list(CATEGORIES)
    clips: List[SampleClip] = []
    for cat in cats:
        cat_dir = LOCAL_SAMPLES_PATH / cat
        if not cat_dir.is_dir():
            continue
        for f in sorted(cat_dir.glob("*.mp4")):
            try:
                size_mb = round(f.stat().st_size / (1024 * 1024), 2)
            except OSError:
                size_mb = None
            clips.append(SampleClip(
                name=f.name,
                category=cat,
                url=f"/api/samples/stream/{cat}/{f.name}",
                size_mb=size_mb,
                source="local",
            ))
    return clips


def _local_clip_path(category: str, filename: str) -> Optional[Path]:
    """Retorna o Path local ou None se não existir / fora do prefixo permitido."""
    candidate = (LOCAL_SAMPLES_PATH / category / filename).resolve()
    base = LOCAL_SAMPLES_PATH.resolve()
    try:
        candidate.relative_to(base)
    except ValueError:
        # Path traversal attempt — recusar
        return None
    if not candidate.is_file() or candidate.suffix.lower() != ".mp4":
        return None
    return candidate


def _local_metadata() -> Dict[str, Any]:
    """Carrega metadata.json local; se ausente, sintetiza um a partir das categorias."""
    meta_file = LOCAL_SAMPLES_PATH / "metadata.json"
    if meta_file.is_file():
        return json.loads(meta_file.read_text(encoding="utf-8"))
    # Sintetizar metadata mínima a partir do que existe no disco
    cats: Dict[str, Any] = {}
    for cat in CATEGORIES:
        cat_dir = LOCAL_SAMPLES_PATH / cat
        if cat_dir.is_dir():
            cats[cat] = {
                "count": len(list(cat_dir.glob("*.mp4"))),
                "description": (
                    "Clips com sangramento" if cat == "bleeding"
                    else "Clips sem sangramento"
                ),
            }
    return {
        "dataset": "GynSurg Action Recognition (local)",
        "description": "Clips de cirurgias ginecológicas (carregados do filesystem local).",
        "categories": cats,
        "source": {"type": "local", "path": str(LOCAL_SAMPLES_PATH)},
    }


def _local_stats() -> Dict[str, Dict[str, float]]:
    stats: Dict[str, Dict[str, float]] = {
        cat: {"count": 0, "total_size_mb": 0} for cat in CATEGORIES
    }
    for cat in CATEGORIES:
        cat_dir = LOCAL_SAMPLES_PATH / cat
        if not cat_dir.is_dir():
            continue
        for f in cat_dir.glob("*.mp4"):
            try:
                stats[cat]["count"] += 1
                stats[cat]["total_size_mb"] += f.stat().st_size / (1024 * 1024)
            except OSError:
                continue
        stats[cat]["total_size_mb"] = round(stats[cat]["total_size_mb"], 2)
    return stats


# ── Helpers — modo S3 ───────────────────────────────────────────────────────

def get_s3_client():
    """Retorna cliente S3."""
    return boto3.client('s3')


def _list_s3(category: Optional[str]) -> List[SampleClip]:
    s3 = get_s3_client()
    cats = [category] if category else list(CATEGORIES)
    clips: List[SampleClip] = []
    for cat in cats:
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
                    size_mb=round(obj['Size'] / (1024 * 1024), 2),
                    source="s3",
                ))
    return clips


def _s3_metadata() -> Dict[str, Any]:
    s3 = get_s3_client()
    response = s3.get_object(Bucket=S3_BUCKET, Key=f"{S3_PREFIX}/metadata.json")
    return json.loads(response['Body'].read().decode('utf-8'))


def _s3_stats() -> Dict[str, Dict[str, float]]:
    s3 = get_s3_client()
    stats: Dict[str, Dict[str, float]] = {
        cat: {"count": 0, "total_size_mb": 0} for cat in CATEGORIES
    }
    for cat in CATEGORIES:
        prefix = f"{S3_PREFIX}/{cat}/"
        response = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=prefix)
        for obj in response.get('Contents', []):
            if obj['Key'].endswith('.mp4'):
                stats[cat]["count"] += 1
                stats[cat]["total_size_mb"] += obj['Size'] / (1024 * 1024)
        stats[cat]["total_size_mb"] = round(stats[cat]["total_size_mb"], 2)
    return stats


# ── Endpoints ───────────────────────────────────────────────────────────────

@router.get("/metadata")
async def get_metadata() -> SampleMetadata:
    """Retorna metadados do dataset de exemplo (S3 → local fallback)."""
    global _metadata_cache
    if _metadata_cache is not None:
        return SampleMetadata(**_metadata_cache)
    try:
        _metadata_cache = _s3_metadata()
        return SampleMetadata(**_metadata_cache)
    except Exception as s3_err:
        if _local_available():
            logger.warning("S3 metadata indisponível (%s) — usando local fallback.", s3_err)
            _metadata_cache = _local_metadata()
            return SampleMetadata(**_metadata_cache)
        raise HTTPException(
            503,
            f"S3 inacessível ({s3_err}) e sem fallback local em {LOCAL_SAMPLES_PATH}.",
        )


@router.get("/list")
async def list_samples(category: Optional[str] = None) -> List[SampleClip]:
    """Lista clips de exemplo (S3 → local fallback)."""
    try:
        return _list_s3(category)
    except Exception as s3_err:
        if _local_available():
            logger.warning("S3 list indisponível (%s) — usando local fallback.", s3_err)
            return _list_local(category)
        raise HTTPException(
            503,
            f"S3 inacessível ({s3_err}) e sem fallback local em {LOCAL_SAMPLES_PATH}.",
        )


@router.get("/stream/{category}/{filename}")
async def stream_sample(category: str, filename: str):
    """Faz streaming de um clip (S3 → local fallback)."""
    if category not in CATEGORIES:
        raise HTTPException(400, "Categoria inválida")

    # Tenta S3 primeiro
    s3_key = f"{S3_PREFIX}/{category}/{filename}"
    try:
        s3 = get_s3_client()
        response = s3.get_object(Bucket=S3_BUCKET, Key=s3_key)
        return StreamingResponse(
            response['Body'].iter_chunks(),
            media_type="video/mp4",
            headers={
                "Content-Disposition": f"inline; filename={filename}",
                "Content-Length": str(response['ContentLength']),
            },
        )
    except Exception as s3_err:
        # Fallback local
        local_path = _local_clip_path(category, filename)
        if local_path is not None:
            logger.warning("S3 stream indisponível (%s) — servindo do disco: %s", s3_err, local_path)
            return FileResponse(
                str(local_path),
                media_type="video/mp4",
                filename=filename,
            )
        # Diferenciar 404 (não existe) vs 500 (outro erro)
        if "NoSuchKey" in str(type(s3_err).__name__):
            raise HTTPException(404, "Clip não encontrado")
        raise HTTPException(
            503,
            f"S3 inacessível ({s3_err}) e sem fallback local para {category}/{filename}.",
        )


@router.post("/process/{category}/{filename}")
async def process_sample(
    category: str,
    filename: str,
    background_tasks: BackgroundTasks,
):
    """Processa um clip de exemplo com o modelo (S3 → local fallback)."""
    from app.routers.video import jobs, process_video, UPLOAD_DIR
    import uuid

    if category not in CATEGORIES:
        raise HTTPException(400, "Categoria inválida")

    job_id = str(uuid.uuid4())
    local_dest = UPLOAD_DIR / f"{job_id}_{filename}"

    # Tenta baixar do S3
    s3_key = f"{S3_PREFIX}/{category}/{filename}"
    used_source = "s3"
    try:
        s3 = get_s3_client()
        s3.download_file(S3_BUCKET, s3_key, str(local_dest))
    except Exception as s3_err:
        # Fallback: copiar do filesystem local
        src = _local_clip_path(category, filename)
        if src is None:
            raise HTTPException(
                503,
                f"S3 inacessível ({s3_err}) e clip não encontrado localmente em "
                f"{LOCAL_SAMPLES_PATH}/{category}/{filename}.",
            )
        logger.warning("S3 download indisponível (%s) — copiando do disco: %s", s3_err, src)
        shutil.copy2(src, local_dest)
        used_source = "local"

    jobs[job_id] = {
        "status": "pending",
        "progress": 0,
        "source": {
            "type": "sample",
            "category": category,
            "filename": filename,
            "ground_truth": category,
            "fetched_from": used_source,
        },
    }

    background_tasks.add_task(process_video, job_id, str(local_dest))

    return {
        "job_id": job_id,
        "message": "Processamento iniciado",
        "ground_truth": category,
        "fetched_from": used_source,
    }


@router.get("/stats")
async def get_sample_stats():
    """Estatísticas dos clips (S3 → local fallback)."""
    try:
        return _s3_stats()
    except Exception as s3_err:
        if _local_available():
            logger.warning("S3 stats indisponível (%s) — usando local fallback.", s3_err)
            return _local_stats()
        raise HTTPException(
            503,
            f"S3 inacessível ({s3_err}) e sem fallback local em {LOCAL_SAMPLES_PATH}.",
        )
