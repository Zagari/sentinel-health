#!/bin/bash
# =============================================================================
# Script de treinamento YOLOv8 no servidor
# Baixa dados do S3, treina, e faz upload do modelo
# =============================================================================

set -e

# Configurações
S3_BUCKET="surgical-detection-datasets-dev"
S3_MODELS_BUCKET="surgical-detection-models-dev"
WORK_DIR="$HOME/surgical-training"
VENV_DIR="$HOME/surgical-venv"
EPOCHS=100
BATCH_SIZE=16
IMG_SIZE=640
MODEL_BASE="yolov8m.pt"  # medium model - bom equilíbrio

echo "========================================"
echo "  TREINAMENTO YOLOV8 - SURGICAL VIDEO AI"
echo "========================================"

# Verificar AWS CLI
echo ""
echo "[1/6] Verificando AWS CLI..."
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI não encontrado. Instalando..."
    curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
    unzip -q awscliv2.zip
    sudo ./aws/install
    rm -rf aws awscliv2.zip
fi
aws --version
echo "✅ AWS CLI OK"

# Verificar credenciais AWS
echo ""
echo "[2/6] Verificando credenciais AWS..."
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ Credenciais AWS não configuradas."
    echo "   Execute: aws configure"
    exit 1
fi
echo "✅ Credenciais AWS OK"

# Criar diretório de trabalho
echo ""
echo "[3/6] Preparando diretórios..."
mkdir -p "$WORK_DIR/data"
mkdir -p "$WORK_DIR/results"
cd "$WORK_DIR"

# Baixar dataset do S3
echo ""
echo "[4/6] Baixando dataset do S3..."
echo "   Isso pode levar alguns minutos..."
aws s3 sync "s3://$S3_BUCKET/yolo_format/" "$WORK_DIR/data/" --only-show-errors

# Verificar dataset
TRAIN_IMAGES=$(ls "$WORK_DIR/data/train/images/" 2>/dev/null | wc -l)
VAL_IMAGES=$(ls "$WORK_DIR/data/val/images/" 2>/dev/null | wc -l)
echo "   Imagens de treino: $TRAIN_IMAGES"
echo "   Imagens de validação: $VAL_IMAGES"

if [ "$TRAIN_IMAGES" -lt 100 ]; then
    echo "❌ Dataset incompleto. Verifique o S3."
    exit 1
fi

# Atualizar data.yaml com caminho correto
cat > "$WORK_DIR/data/data.yaml" << EOF
path: $WORK_DIR/data
train: train/images
val: val/images
nc: 2
names:
  0: grasper
  1: blood
EOF

echo "✅ Dataset pronto"

# Ativar ambiente virtual e treinar
echo ""
echo "[5/6] Iniciando treinamento..."
echo "   Modelo base: $MODEL_BASE"
echo "   Epochs: $EPOCHS"
echo "   Batch size: $BATCH_SIZE"
echo "   Imagem: ${IMG_SIZE}x${IMG_SIZE}"
echo ""

source "$VENV_DIR/bin/activate"

# Filtrar warnings do NNPACK (irrelevante quando usando GPU)
filter_nnpack() { grep -v "NNPACK.cpp" || true; }

# Treinar
yolo detect train \
    data="$WORK_DIR/data/data.yaml" \
    model=$MODEL_BASE \
    epochs=$EPOCHS \
    imgsz=$IMG_SIZE \
    batch=$BATCH_SIZE \
    project="$WORK_DIR/results" \
    name="surgical_detection" \
    exist_ok=True \
    patience=20 \
    save=True \
    plots=True 2>&1 | filter_nnpack

# Upload do modelo para S3
echo ""
echo "[6/6] Fazendo upload do modelo para S3..."

BEST_MODEL="$WORK_DIR/results/surgical_detection/weights/best.pt"
if [ -f "$BEST_MODEL" ]; then
    aws s3 cp "$BEST_MODEL" "s3://$S3_MODELS_BUCKET/trained/best.pt"
    aws s3 cp "$WORK_DIR/results/surgical_detection/weights/last.pt" "s3://$S3_MODELS_BUCKET/trained/last.pt"

    # Upload das métricas e plots
    aws s3 sync "$WORK_DIR/results/surgical_detection/" "s3://$S3_MODELS_BUCKET/training_results/" \
        --exclude "weights/*" --only-show-errors

    echo "✅ Modelo enviado para S3"
else
    echo "❌ Modelo não encontrado: $BEST_MODEL"
    exit 1
fi

echo ""
echo "========================================"
echo "  TREINAMENTO CONCLUÍDO!"
echo "========================================"
echo ""
echo "Modelo salvo em:"
echo "  Local: $BEST_MODEL"
echo "  S3: s3://$S3_MODELS_BUCKET/trained/best.pt"
echo ""
echo "Métricas e plots em:"
echo "  s3://$S3_MODELS_BUCKET/training_results/"
echo ""
echo "Próximo passo: testar inferência"
echo "  ./server-inference.sh video.mp4"
