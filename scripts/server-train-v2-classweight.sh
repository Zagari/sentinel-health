#!/bin/bash
# =============================================================================
# Script de treinamento YOLOv8 v2 - Com Class Weights
# Melhoria: Aumenta peso da loss de classificação para compensar desbalanceamento
#
# Problema: Dataset tem 5.4:1 ratio (grasper vs blood)
# Solução: cls=3.0 aumenta peso da classificação na loss function
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
MODEL_BASE="yolov8m.pt"
EXPERIMENT_NAME="surgical_detection_v2_classweight"
MODEL_VERSION="v2_classweight"

# Parâmetros de class weight
CLS_WEIGHT=3.0  # Aumenta peso da loss de classificação (default: 0.5)

echo "========================================"
echo "  TREINAMENTO YOLOV8 v2 - CLASS WEIGHTS"
echo "========================================"
echo ""
echo "Configurações:"
echo "  Modelo base: $MODEL_BASE"
echo "  Epochs: $EPOCHS"
echo "  Batch size: $BATCH_SIZE"
echo "  Imagem: ${IMG_SIZE}x${IMG_SIZE}"
echo "  Class weight (cls): $CLS_WEIGHT"
echo ""

# Verificar AWS CLI
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
mkdir -p "$WORK_DIR/models"
cd "$WORK_DIR"

# Baixar dataset do S3 (se não existir)
echo ""
echo "[4/6] Verificando dataset..."
TRAIN_IMAGES=$(ls "$WORK_DIR/data/train/images/" 2>/dev/null | wc -l)

if [ "$TRAIN_IMAGES" -lt 100 ]; then
    echo "   Baixando dataset do S3..."
    aws s3 sync "s3://$S3_BUCKET/yolo_format/" "$WORK_DIR/data/" --only-show-errors
    TRAIN_IMAGES=$(ls "$WORK_DIR/data/train/images/" 2>/dev/null | wc -l)
fi

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
echo "[5/6] Iniciando treinamento v2 com class weights..."
echo ""
echo "┌────────────────────────────────────────┐"
echo "│  DIFERENÇA DO v1 (baseline):           │"
echo "│  + cls=$CLS_WEIGHT (era 0.5)                   │"
echo "│  Objetivo: Compensar desbalanceamento  │"
echo "│  de classes (5.4:1 grasper vs blood)   │"
echo "└────────────────────────────────────────┘"
echo ""

source "$VENV_DIR/bin/activate"

# Filtrar warnings do NNPACK (irrelevante quando usando GPU)
filter_nnpack() { grep -v "NNPACK.cpp" || true; }

# Treinar com class weights aumentado
yolo detect train \
    data="$WORK_DIR/data/data.yaml" \
    model=$MODEL_BASE \
    epochs=$EPOCHS \
    imgsz=$IMG_SIZE \
    batch=$BATCH_SIZE \
    project="$WORK_DIR/results" \
    name="$EXPERIMENT_NAME" \
    exist_ok=True \
    patience=20 \
    save=True \
    plots=True \
    cls=$CLS_WEIGHT 2>&1 | filter_nnpack

# Upload do modelo para S3
echo ""
echo "[6/6] Fazendo upload do modelo para S3..."

BEST_MODEL="$WORK_DIR/results/$EXPERIMENT_NAME/weights/best.pt"
if [ -f "$BEST_MODEL" ]; then
    # Upload para S3 com nome versionado
    aws s3 cp "$BEST_MODEL" "s3://$S3_MODELS_BUCKET/trained/best_${MODEL_VERSION}.pt"
    aws s3 cp "$WORK_DIR/results/$EXPERIMENT_NAME/weights/last.pt" "s3://$S3_MODELS_BUCKET/trained/last_${MODEL_VERSION}.pt"

    # Upload das métricas e plots
    aws s3 sync "$WORK_DIR/results/$EXPERIMENT_NAME/" "s3://$S3_MODELS_BUCKET/training_results_${MODEL_VERSION}/" \
        --exclude "weights/*" --only-show-errors

    # Copiar para pasta local de modelos (para validação)
    cp "$BEST_MODEL" "$WORK_DIR/models/best.pt"
    cp "$BEST_MODEL" "$WORK_DIR/models/best_${MODEL_VERSION}.pt"

    echo "✅ Modelo enviado para S3"
else
    echo "❌ Modelo não encontrado: $BEST_MODEL"
    exit 1
fi

echo ""
echo "========================================"
echo "  TREINAMENTO v2 CONCLUÍDO!"
echo "========================================"
echo ""
echo "Modelo salvo em:"
echo "  Local: $WORK_DIR/models/best_${MODEL_VERSION}.pt"
echo "  S3: s3://$S3_MODELS_BUCKET/trained/best_${MODEL_VERSION}.pt"
echo ""
echo "Métricas e plots em:"
echo "  s3://$S3_MODELS_BUCKET/training_results_${MODEL_VERSION}/"
echo ""
echo "Próximo passo: validar com GynSurg"
echo "  ./scripts/validate-gynsurg.sh /path/to/GynSurg --fixed --version $MODEL_VERSION"
echo ""
