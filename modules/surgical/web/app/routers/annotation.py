"""
Router para interface de anotação de frames para fine-tuning.
Permite classificar frames do GynSurg como "com sangramento" ou "sem sangramento".
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import os
import json
import random
import cv2
from pathlib import Path
from datetime import datetime

router = APIRouter()

# Diretórios
GYNSURG_PATH = os.getenv("GYNSURG_PATH", "/data/GynSurg_Action_3sec")
ANNOTATIONS_PATH = os.getenv("ANNOTATIONS_PATH", "/tmp/annotations")
FRAMES_CACHE = "/tmp/frames_cache"


class AnnotationRequest(BaseModel):
    frame_id: str
    has_bleeding: bool
    confidence: Optional[str] = "high"  # high, medium, low


class AnnotationStats(BaseModel):
    total_frames: int
    annotated: int
    with_bleeding: int
    without_bleeding: int
    skipped: int


@router.get("/frame/random")
async def get_random_frame():
    """Retorna um frame aleatório não anotado para classificação."""
    bleeding_dir = Path(GYNSURG_PATH) / "GynSurg_bleeding_dataset" / "Bleeding"
    non_bleeding_dir = Path(GYNSURG_PATH) / "GynSurg_bleeding_dataset" / "Non_bleeding"

    # Verificar se diretórios existem
    if not bleeding_dir.exists() or not non_bleeding_dir.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Dataset não encontrado em {GYNSURG_PATH}. Configure GYNSURG_PATH."
        )

    # Listar todos os clips
    all_clips = list(bleeding_dir.glob("*.mp4")) + list(non_bleeding_dir.glob("*.mp4"))

    if not all_clips:
        raise HTTPException(status_code=404, detail="Nenhum clip encontrado no dataset")

    # Carregar anotações existentes
    annotations_file = Path(ANNOTATIONS_PATH) / "annotations.json"
    annotated_frames = set()
    skipped_frames = set()

    if annotations_file.exists():
        with open(annotations_file) as f:
            data = json.load(f)
            annotated_frames = set(data.get("annotated_ids", []))
            skipped_frames = set(data.get("skipped_ids", []))

    # Selecionar clip aleatório e extrair frame
    random.shuffle(all_clips)

    for clip in all_clips:
        # Extrair frame do meio do clip
        cap = cv2.VideoCapture(str(clip))
        if not cap.isOpened():
            continue

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        mid_frame = total_frames // 2

        frame_id = f"{clip.stem}_f{mid_frame}"

        # Pular se já foi anotado ou pulado
        if frame_id in annotated_frames or frame_id in skipped_frames:
            cap.release()
            continue

        cap.set(cv2.CAP_PROP_POS_FRAMES, mid_frame)
        ret, frame = cap.read()
        cap.release()

        if ret:
            # Salvar frame em cache
            os.makedirs(FRAMES_CACHE, exist_ok=True)
            frame_path = Path(FRAMES_CACHE) / f"{frame_id}.jpg"

            # Redimensionar para economizar espaço (manter aspect ratio)
            h, w = frame.shape[:2]
            max_width = 1280
            if w > max_width:
                scale = max_width / w
                frame = cv2.resize(frame, (int(w * scale), int(h * scale)))

            cv2.imwrite(str(frame_path), frame)

            # Determinar ground truth (baseado na pasta)
            ground_truth = "Bleeding" in str(clip.parent)

            return {
                "frame_id": frame_id,
                "frame_url": f"/api/annotation/frame/{frame_id}/image",
                "clip_name": clip.name,
                "ground_truth_label": "bleeding" if ground_truth else "non_bleeding",
                "total_annotated": len(annotated_frames),
                "total_skipped": len(skipped_frames)
            }

    return {
        "message": "Todos os frames foram processados!",
        "complete": True,
        "total_annotated": len(annotated_frames)
    }


@router.get("/frame/{frame_id}/image")
async def get_frame_image(frame_id: str):
    """Retorna a imagem do frame."""
    frame_path = Path(FRAMES_CACHE) / f"{frame_id}.jpg"
    if not frame_path.exists():
        raise HTTPException(status_code=404, detail="Frame não encontrado")
    return FileResponse(frame_path, media_type="image/jpeg")


@router.post("/annotate")
async def save_annotation(annotation: AnnotationRequest):
    """Salva a anotação de um frame."""
    os.makedirs(ANNOTATIONS_PATH, exist_ok=True)
    annotations_file = Path(ANNOTATIONS_PATH) / "annotations.json"

    # Carregar ou criar arquivo de anotações
    if annotations_file.exists():
        with open(annotations_file) as f:
            data = json.load(f)
    else:
        data = {
            "created_at": datetime.now().isoformat(),
            "annotations": [],
            "annotated_ids": [],
            "skipped_ids": []
        }

    # Adicionar nova anotação
    data["annotations"].append({
        "frame_id": annotation.frame_id,
        "has_bleeding": annotation.has_bleeding,
        "confidence": annotation.confidence,
        "timestamp": datetime.now().isoformat()
    })
    data["annotated_ids"].append(annotation.frame_id)
    data["updated_at"] = datetime.now().isoformat()

    with open(annotations_file, 'w') as f:
        json.dump(data, f, indent=2)

    return {
        "status": "saved",
        "frame_id": annotation.frame_id,
        "total_annotations": len(data["annotations"])
    }


@router.post("/skip/{frame_id}")
async def skip_frame(frame_id: str):
    """Marca um frame como pulado (não será mostrado novamente)."""
    os.makedirs(ANNOTATIONS_PATH, exist_ok=True)
    annotations_file = Path(ANNOTATIONS_PATH) / "annotations.json"

    if annotations_file.exists():
        with open(annotations_file) as f:
            data = json.load(f)
    else:
        data = {
            "created_at": datetime.now().isoformat(),
            "annotations": [],
            "annotated_ids": [],
            "skipped_ids": []
        }

    if frame_id not in data["skipped_ids"]:
        data["skipped_ids"].append(frame_id)
        data["updated_at"] = datetime.now().isoformat()

        with open(annotations_file, 'w') as f:
            json.dump(data, f, indent=2)

    return {"status": "skipped", "frame_id": frame_id}


@router.get("/stats")
async def get_annotation_stats():
    """Retorna estatísticas das anotações."""
    annotations_file = Path(ANNOTATIONS_PATH) / "annotations.json"

    if not annotations_file.exists():
        return AnnotationStats(
            total_frames=0,
            annotated=0,
            with_bleeding=0,
            without_bleeding=0,
            skipped=0
        )

    with open(annotations_file) as f:
        data = json.load(f)

    annotations = data.get("annotations", [])
    with_bleeding = sum(1 for a in annotations if a["has_bleeding"])
    skipped = len(data.get("skipped_ids", []))

    return AnnotationStats(
        total_frames=len(annotations) + skipped,
        annotated=len(annotations),
        with_bleeding=with_bleeding,
        without_bleeding=len(annotations) - with_bleeding,
        skipped=skipped
    )


@router.get("/export")
async def export_for_training():
    """Exporta anotações no formato YOLO para fine-tuning."""
    annotations_file = Path(ANNOTATIONS_PATH) / "annotations.json"

    if not annotations_file.exists():
        raise HTTPException(status_code=404, detail="Nenhuma anotação encontrada")

    with open(annotations_file) as f:
        data = json.load(f)

    annotations = data.get("annotations", [])
    if not annotations:
        raise HTTPException(status_code=404, detail="Nenhuma anotação encontrada")

    # Criar estrutura YOLO
    export_dir = Path(ANNOTATIONS_PATH) / "yolo_export"
    (export_dir / "images" / "train").mkdir(parents=True, exist_ok=True)
    (export_dir / "labels" / "train").mkdir(parents=True, exist_ok=True)

    exported = 0
    export_log = []

    for ann in annotations:
        frame_path = Path(FRAMES_CACHE) / f"{ann['frame_id']}.jpg"
        if frame_path.exists():
            import shutil

            # Copiar imagem
            dest_img = export_dir / "images" / "train" / f"{ann['frame_id']}.jpg"
            shutil.copy(frame_path, dest_img)

            # Criar label
            label_path = export_dir / "labels" / "train" / f"{ann['frame_id']}.txt"

            if ann["has_bleeding"]:
                # Pseudo-bbox cobrindo região central (80% da imagem)
                # Formato YOLO: class x_center y_center width height
                with open(label_path, 'w') as f:
                    f.write("1 0.5 0.5 0.8 0.8\n")  # class 1 (blood)
            else:
                # Arquivo vazio = sem detecções (negative sample)
                label_path.touch()

            exported += 1
            export_log.append({
                "frame_id": ann["frame_id"],
                "has_bleeding": ann["has_bleeding"]
            })

    # Criar data.yaml
    data_yaml = export_dir / "data.yaml"
    with open(data_yaml, 'w') as f:
        f.write(f"""path: {export_dir}
train: images/train
val: images/train
nc: 2
names:
  0: grasper
  1: blood
""")

    # Salvar log de exportação
    export_info = {
        "exported_at": datetime.now().isoformat(),
        "total_exported": exported,
        "with_bleeding": sum(1 for a in annotations if a["has_bleeding"]),
        "without_bleeding": sum(1 for a in annotations if not a["has_bleeding"]),
        "export_path": str(export_dir),
        "files": export_log
    }

    with open(export_dir / "export_info.json", 'w') as f:
        json.dump(export_info, f, indent=2)

    return {
        "status": "exported",
        "exported_frames": exported,
        "with_bleeding": export_info["with_bleeding"],
        "without_bleeding": export_info["without_bleeding"],
        "export_path": str(export_dir),
        "data_yaml": str(data_yaml)
    }


@router.delete("/reset")
async def reset_annotations():
    """Remove todas as anotações (use com cuidado!)."""
    annotations_file = Path(ANNOTATIONS_PATH) / "annotations.json"

    if annotations_file.exists():
        # Fazer backup antes de deletar
        backup_file = Path(ANNOTATIONS_PATH) / f"annotations_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        import shutil
        shutil.copy(annotations_file, backup_file)
        annotations_file.unlink()

        return {
            "status": "reset",
            "backup_created": str(backup_file)
        }

    return {"status": "nothing_to_reset"}
