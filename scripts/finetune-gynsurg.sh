#!/bin/bash
# =============================================================================
# Fine-tuning com dados anotados do GynSurg
# Usa o modelo atual como base e treina com as anotações da interface web
# =============================================================================

set -e

WORK_DIR="$HOME/surgical-training"
VENV_DIR="$HOME/surgical-venv"
S3_MODELS_BUCKET="surgical-detection-models-dev"

# Diretório padrão das anotações (pode ser alterado)
ANNOTATIONS_DIR="${1:-/tmp/annotations/yolo_export}"
BASE_MODEL="${2:-$WORK_DIR/models/best.pt}"
MODEL_VERSION="v3_finetuned"
EXPERIMENT_NAME="surgical_detection_$MODEL_VERSION"

# Parâmetros de fine-tuning (menos agressivos que treino completo)
EPOCHS=30
BATCH_SIZE=8
LR0=0.001  # Learning rate menor para fine-tuning
IMG_SIZE=640

show_help() {
    echo "Uso: $0 [diretorio_anotacoes] [modelo_base]"
    echo ""
    echo "Argumentos:"
    echo "  diretorio_anotacoes   Caminho para export YOLO (default: /tmp/annotations/yolo_export)"
    echo "  modelo_base           Modelo a ser usado como base (default: ~/surgical-training/models/best.pt)"
    echo ""
    echo "Exemplo:"
    echo "  $0                                                    # Usa defaults"
    echo "  $0 /tmp/annotations/yolo_export models/best_v2.pt   # Especifica paths"
    echo ""
    echo "IMPORTANTE: Execute primeiro a exportacao na interface /annotation"
}

if [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
    show_help
    exit 0
fi

echo "========================================"
echo "  FINE-TUNING COM DADOS GYNSURG"
echo "========================================"
echo ""
echo "Diretorio de anotacoes: $ANNOTATIONS_DIR"
echo "Modelo base: $BASE_MODEL"
echo "Versao de saida: $MODEL_VERSION"
echo ""

# Verificar se existem dados
if [ ! -d "$ANNOTATIONS_DIR/images/train" ]; then
    echo "Erro: Nenhum dado de anotacao encontrado em $ANNOTATIONS_DIR"
    echo ""
    echo "Certifique-se de:"
    echo "  1. Anotar frames na interface /annotation"
    echo "  2. Clicar em 'Exportar Anotacoes'"
    echo ""
    echo "Ou especifique o caminho correto como argumento."
    exit 1
fi

# Contar imagens
NUM_IMAGES=$(ls "$ANNOTATIONS_DIR/images/train/"*.jpg 2>/dev/null | wc -l)
echo "Imagens encontradas: $NUM_IMAGES"

if [ "$NUM_IMAGES" -lt 10 ]; then
    echo ""
    echo "AVISO: Poucas imagens para fine-tuning ($NUM_IMAGES)."
    echo "Recomendado: pelo menos 50 imagens anotadas."
    echo ""
    read -p "Continuar mesmo assim? (s/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Ss]$ ]]; then
        exit 1
    fi
fi

# Verificar modelo base
if [ ! -f "$BASE_MODEL" ]; then
    echo "Erro: Modelo base nao encontrado: $BASE_MODEL"
    exit 1
fi

# Verificar/criar data.yaml
DATA_YAML="$ANNOTATIONS_DIR/data.yaml"
if [ ! -f "$DATA_YAML" ]; then
    echo "Criando data.yaml..."
    cat > "$DATA_YAML" << EOF
path: $ANNOTATIONS_DIR
train: images/train
val: images/train
nc: 2
names:
  0: grasper
  1: blood
EOF
fi

# Criar diretórios de saída
mkdir -p "$WORK_DIR/results"
mkdir -p "$WORK_DIR/models"

# Ativar ambiente virtual
echo ""
echo "Ativando ambiente virtual..."
source "$VENV_DIR/bin/activate"

# Filtrar warnings do NNPACK
filter_nnpack() { grep -v "NNPACK.cpp" || true; }

# Fine-tuning
echo ""
echo "========================================"
echo "  INICIANDO FINE-TUNING"
echo "========================================"
echo ""
echo "Parametros:"
echo "  Epochs: $EPOCHS"
echo "  Batch size: $BATCH_SIZE"
echo "  Learning rate: $LR0"
echo "  Imagem: ${IMG_SIZE}x${IMG_SIZE}"
echo ""

yolo detect train \
    data="$DATA_YAML" \
    model="$BASE_MODEL" \
    epochs=$EPOCHS \
    imgsz=$IMG_SIZE \
    batch=$BATCH_SIZE \
    lr0=$LR0 \
    project="$WORK_DIR/results" \
    name="$EXPERIMENT_NAME" \
    exist_ok=True \
    patience=10 \
    save=True \
    plots=True \
    freeze=10 2>&1 | filter_nnpack

# Verificar se treino foi bem sucedido
BEST_MODEL="$WORK_DIR/results/$EXPERIMENT_NAME/weights/best.pt"
if [ ! -f "$BEST_MODEL" ]; then
    echo "Erro: Modelo nao foi gerado"
    exit 1
fi

# Copiar modelo
echo ""
echo "Salvando modelo..."
cp "$BEST_MODEL" "$WORK_DIR/models/best_${MODEL_VERSION}.pt"
cp "$BEST_MODEL" "$WORK_DIR/models/best.pt"

# Upload para S3 (opcional)
echo ""
read -p "Fazer upload para S3? (s/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Ss]$ ]]; then
    echo "Enviando para S3..."
    aws s3 cp "$BEST_MODEL" "s3://$S3_MODELS_BUCKET/trained/best_${MODEL_VERSION}.pt"
    aws s3 sync "$WORK_DIR/results/$EXPERIMENT_NAME/" "s3://$S3_MODELS_BUCKET/training_results_${MODEL_VERSION}/" \
        --exclude "weights/*" --only-show-errors
    echo "Upload concluido!"
fi

echo ""
echo "========================================"
echo "  FINE-TUNING CONCLUIDO!"
echo "========================================"
echo ""
echo "Modelo salvo em:"
echo "  $WORK_DIR/models/best_${MODEL_VERSION}.pt"
echo ""
echo "Proximo passo: validar com GynSurg"
echo "  ./scripts/validate-gynsurg.sh /path/to/GynSurg --fixed --version $MODEL_VERSION"
echo ""
