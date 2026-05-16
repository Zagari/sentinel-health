#!/bin/bash
# =============================================================================
# Script de inferência YOLOv8 no servidor
# Processa vídeo e gera relatório
# =============================================================================

set -e

# Configurações
S3_MODELS_BUCKET="surgical-detection-models-dev"
S3_RESULTS_BUCKET="surgical-detection-results-dev"
WORK_DIR="$HOME/surgical-training"
VENV_DIR="$HOME/surgical-venv"
MODEL_PATH="$WORK_DIR/models/best.pt"

# Verificar argumentos
if [ -z "$1" ]; then
    echo "Uso: $0 <video.mp4> [--upload]"
    echo ""
    echo "Opções:"
    echo "  --upload    Faz upload dos resultados para S3"
    echo ""
    echo "Exemplo:"
    echo "  $0 cirurgia.mp4"
    echo "  $0 cirurgia.mp4 --upload"
    exit 1
fi

VIDEO_PATH="$1"
UPLOAD_TO_S3=false
if [ "$2" == "--upload" ]; then
    UPLOAD_TO_S3=true
fi

# Verificar se vídeo existe
if [ ! -f "$VIDEO_PATH" ]; then
    echo "❌ Vídeo não encontrado: $VIDEO_PATH"
    exit 1
fi

VIDEO_NAME=$(basename "$VIDEO_PATH" | sed 's/\.[^.]*$//')
OUTPUT_DIR="$WORK_DIR/inference/$VIDEO_NAME"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "========================================"
echo "  INFERÊNCIA YOLOV8 - SURGICAL VIDEO AI"
echo "========================================"
echo ""
echo "Vídeo: $VIDEO_PATH"
echo "Saída: $OUTPUT_DIR"

# Criar diretórios
mkdir -p "$OUTPUT_DIR"
mkdir -p "$WORK_DIR/models"

# Baixar modelo do S3 se necessário
echo ""
echo "[1/4] Verificando modelo..."
if [ ! -f "$MODEL_PATH" ]; then
    echo "   Baixando modelo do S3..."
    aws s3 cp "s3://$S3_MODELS_BUCKET/trained/best.pt" "$MODEL_PATH"
fi

if [ ! -f "$MODEL_PATH" ]; then
    echo "❌ Modelo não encontrado. Execute o treinamento primeiro."
    exit 1
fi
echo "✅ Modelo: $MODEL_PATH"

# Ativar ambiente virtual
source "$VENV_DIR/bin/activate"

# Executar inferência
echo ""
echo "[2/4] Processando vídeo..."

yolo detect predict \
    model="$MODEL_PATH" \
    source="$VIDEO_PATH" \
    project="$OUTPUT_DIR" \
    name="detections" \
    exist_ok=True \
    save=True \
    save_txt=True \
    save_conf=True \
    conf=0.5

# Gerar relatório JSON
echo ""
echo "[3/4] Gerando relatório..."

python3 << EOF
import json
import os
from pathlib import Path
from datetime import datetime

output_dir = Path("$OUTPUT_DIR/detections")
labels_dir = output_dir / "labels"

# Coletar estatísticas
stats = {
    "video": "$VIDEO_PATH",
    "model": "$MODEL_PATH",
    "processed_at": datetime.now().isoformat(),
    "classes": {"grasper": 0, "blood": 0},
    "frames_with_detections": 0,
    "total_detections": 0,
}

if labels_dir.exists():
    for label_file in labels_dir.glob("*.txt"):
        with open(label_file) as f:
            lines = f.readlines()
            if lines:
                stats["frames_with_detections"] += 1
                for line in lines:
                    parts = line.strip().split()
                    if parts:
                        class_id = int(parts[0])
                        if class_id == 0:
                            stats["classes"]["grasper"] += 1
                        elif class_id == 1:
                            stats["classes"]["blood"] += 1
                        stats["total_detections"] += 1

# Salvar relatório
report_path = Path("$OUTPUT_DIR") / "report.json"
with open(report_path, "w") as f:
    json.dump(stats, f, indent=2)

print(f"Relatório salvo: {report_path}")
print(f"Total de detecções: {stats['total_detections']}")
print(f"  - Grasper: {stats['classes']['grasper']}")
print(f"  - Blood: {stats['classes']['blood']}")
EOF

# Upload para S3 (opcional)
echo ""
if [ "$UPLOAD_TO_S3" = true ]; then
    echo "[4/4] Fazendo upload para S3..."
    aws s3 sync "$OUTPUT_DIR/" "s3://$S3_RESULTS_BUCKET/$VIDEO_NAME\_$TIMESTAMP/" --only-show-errors
    echo "✅ Resultados enviados para S3"
else
    echo "[4/4] Upload para S3 pulado (use --upload para enviar)"
fi

echo ""
echo "========================================"
echo "  INFERÊNCIA CONCLUÍDA!"
echo "========================================"
echo ""
echo "Resultados em: $OUTPUT_DIR"
echo ""
echo "Arquivos gerados:"
ls -la "$OUTPUT_DIR/detections/" 2>/dev/null | head -10
