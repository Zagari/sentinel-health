"""
Endpoints de informações sobre o modelo e dataset.
"""
from fastapi import APIRouter
from typing import Dict, Any, List
from pydantic import BaseModel

router = APIRouter()


class ClassInfo(BaseModel):
    id: int
    name: str
    description: str


MODEL_INFO = {
    "name": "YOLOv8m - Surgical Detection",
    "version": "3.0 (v3_finetuned)",
    "architecture": "YOLOv8m (Ultralytics)",
    "input_size": 640,
    "confidence_threshold": 0.30,
    "training_dataset": "CholecSeg8k + GynSurg (fine-tuning)",
    "validation_dataset": "GynSurg Action Recognition",
    "classes": [
        {"id": 0, "name": "grasper", "description": "Pinça de apreensão cirúrgica"},
        {"id": 1, "name": "blood", "description": "Sangramento detectado"},
    ],
    "performance": {
        "detection_rate": "91.72%",
        "false_positive_rate": "13.44%",
        "validation_frames": 1806
    }
}

DATASET_INFO = {
    "training": {
        "name": "CholecSeg8k",
        "description": "Dataset de colecistectomia laparoscópica com máscaras de segmentação",
        "total_images": 8080,
        "train_images": 6464,
        "val_images": 1616,
        "classes": {
            "grasper": {"instances": 13680, "description": "Pinça de apreensão"},
            "blood": {"instances": 2545, "description": "Áreas de sangramento"}
        },
        "resolution": "Variable",
        "source": "Kaggle - CholecSeg8k",
        "purpose": "Treinamento do modelo de detecção"
    },
    "validation": {
        "name": "GynSurg Action Recognition",
        "description": "Clips de cirurgias ginecológicas laparoscópicas",
        "bleeding_clips": 977,
        "non_bleeding_clips": 1064,
        "sample_clips": {
            "bleeding": 50,
            "non_bleeding": 54
        },
        "resolution": "3840x2160 (4K)",
        "fps": 30,
        "clip_duration_seconds": 3,
        "source": "Medical University of Vienna / Toronto",
        "purpose": "Validação cross-dataset e demonstração",
        "license": "CC BY-NC-ND 4.0"
    }
}

TRAINING_METRICS = {
    "model": "YOLOv8m",
    "current_version": "v3_finetuned",
    "training_phases": [
        {
            "version": "v1_baseline",
            "description": "Treino inicial em CholecSeg8k",
            "epochs": 100,
            "detection_rate": "5.41%",
            "false_positive_rate": "76.11%"
        },
        {
            "version": "v2_classweight",
            "description": "Treino com class weights (cls=3.0)",
            "epochs": 100,
            "detection_rate": "12.14%",
            "false_positive_rate": "46.89%"
        },
        {
            "version": "v3_finetuned",
            "description": "Fine-tuning com 1020 frames anotados do GynSurg",
            "epochs": 30,
            "base_model": "v2_classweight",
            "finetuning_data": "475 frames bleeding + 545 frames non-bleeding",
            "detection_rate": "91.72%",
            "false_positive_rate": "13.44%"
        }
    ],
    "image_size": 640,
    "optimizer": "AdamW",
    "training_time": "~3-4 hours (treino inicial) + ~1 hora (fine-tuning)"
}

PROJECT_INFO = {
    "name": "Surgical Video AI",
    "description": "Sistema de análise de vídeos cirúrgicos para detecção de sangramento e instrumentos",
    "challenge": "FIAP Tech Challenge - Fase 4: Análise de Dados",
    "objective": "Monitoramento de saúde da mulher através de análise de vídeos de cirurgias ginecológicas",
    "features": [
        "Detecção de sangramento anômalo em tempo real",
        "Identificação de instrumentos cirúrgicos",
        "Processamento de vídeos via upload ou URL",
        "Galeria de clips de exemplo para demonstração",
        "Relatórios automáticos de detecção"
    ],
    "tech_stack": {
        "ml": "YOLOv8 (Ultralytics), PyTorch",
        "backend": "FastAPI, Python 3.10+",
        "frontend": "HTML, CSS, JavaScript",
        "infrastructure": "Docker, AWS S3, Terraform"
    },
    "repository": "https://github.com/Zagari/surgical-video-ai"
}


@router.get("/model")
async def get_model_info() -> Dict[str, Any]:
    """Informações sobre o modelo."""
    return MODEL_INFO


@router.get("/dataset")
async def get_dataset_info() -> Dict[str, Any]:
    """Informações sobre os datasets usados."""
    return DATASET_INFO


@router.get("/metrics")
async def get_training_metrics() -> Dict[str, Any]:
    """Métricas de treinamento."""
    return TRAINING_METRICS


@router.get("/classes")
async def get_classes() -> List[ClassInfo]:
    """Lista de classes detectadas."""
    return [ClassInfo(**c) for c in MODEL_INFO["classes"]]


@router.get("/project")
async def get_project_info() -> Dict[str, Any]:
    """Informações sobre o projeto."""
    return PROJECT_INFO


@router.get("/strategy")
async def get_strategy() -> Dict[str, Any]:
    """Explica a estratégia cross-dataset e fine-tuning utilizada."""
    return {
        "title": "Estratégia Cross-Dataset + Fine-tuning",
        "description": "Treino em CholecSeg8k, fine-tuning e validação em GynSurg",
        "approach": {
            "phase1_training": {
                "dataset": "CholecSeg8k",
                "type": "Colecistectomia laparoscópica",
                "images": 8080,
                "annotations": "Máscaras de segmentação pixel-level",
                "rationale": "Anotações precisas para treinar detecção de objetos",
                "result": "v1_baseline (5.41% det / 76.11% FP)"
            },
            "phase2_class_weights": {
                "technique": "Class weights (cls=3.0)",
                "rationale": "Compensar desbalanceamento de classes (5.4:1 grasper vs blood)",
                "result": "v2_classweight (12.14% det / 46.89% FP)"
            },
            "phase3_finetuning": {
                "dataset": "GynSurg",
                "type": "Cirurgias ginecológicas laparoscópicas",
                "annotations": "1020 frames anotados manualmente (475 bleeding + 545 non-bleeding)",
                "technique": "Fine-tuning do v2 com pseudo-bounding boxes",
                "parameters": "30 epochs, lr=0.001, freeze=10 camadas",
                "result": "v3_finetuned (91.72% det / 13.44% FP)"
            },
            "validation": {
                "dataset": "GynSurg (validation set fixo)",
                "clips": "10 bleeding + 10 non-bleeding",
                "frames": "~1800 frames totais",
                "rationale": "Validar generalização em procedimentos ginecológicos reais"
            }
        },
        "benefits": [
            "Treino inicial aprende padrões universais de sangramento",
            "Class weights compensam desbalanceamento de classes",
            "Fine-tuning adapta o modelo para cirurgias ginecológicas",
            "Validação cross-dataset comprova capacidade de generalização"
        ],
        "final_metrics": {
            "detection_rate": "91.72%",
            "false_positive_rate": "13.44%",
            "confidence_threshold": 0.30
        }
    }
