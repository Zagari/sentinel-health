#!/bin/bash
# =============================================================================
# Validação do modelo com dataset GynSurg
# Testa o modelo treinado em CholecSeg8k nos clips de cirurgia ginecológica
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
    echo "Uso: $0 <caminho_gynsurg_action_3sec> [opções]"
    echo ""
    echo "Opções:"
    echo "  --fixed          Usa validation set fixo (requer generate-validation-set.sh primeiro)"
    echo "  --seed           Usa shuf com seed 42 (reproduzível, mas não usa arquivo fixo)"
    echo "  --version TAG    Tag de versão do modelo (ex: v1_baseline, v2_classweight)"
    echo "  --conf VALUE     Confidence threshold (default: 0.3)"
    echo "  --upload         Faz upload dos resultados para S3"
    echo ""
    echo "Exemplos:"
    echo "  $0 /path/to/GynSurg --fixed --version v1_baseline"
    echo "  $0 /path/to/GynSurg --fixed --version v2_classweight"
    echo "  $0 /path/to/GynSurg --fixed --version v3_finetuned --upload"
    exit 1
fi

GYNSURG_PATH="$1"
UPLOAD_TO_S3=false
USE_FIXED_SET=false
USE_SEED=false
SEED=42
MODEL_VERSION="baseline"  # Tag de versão do modelo
CONF_THRESHOLD=0.3        # Confidence threshold

# Processar argumentos
shift  # Remove primeiro argumento (path)
while [[ $# -gt 0 ]]; do
    case $1 in
        --upload)
            UPLOAD_TO_S3=true
            shift
            ;;
        --fixed)
            USE_FIXED_SET=true
            shift
            ;;
        --seed)
            USE_SEED=true
            shift
            ;;
        --version)
            MODEL_VERSION="$2"
            shift 2
            ;;
        --conf)
            CONF_THRESHOLD="$2"
            shift 2
            ;;
        *)
            echo "Opção desconhecida: $1"
            exit 1
            ;;
    esac
done

# Verificar se diretório existe
if [ ! -d "$GYNSURG_PATH/GynSurg_bleeding_dataset" ]; then
    echo "❌ Dataset de bleeding não encontrado em: $GYNSURG_PATH/GynSurg_bleeding_dataset"
    exit 1
fi

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_DIR="$WORK_DIR/validation_gynsurg_$TIMESTAMP"

# Determinar modo de seleção para exibição
if [ "$USE_FIXED_SET" = true ]; then
    SELECTION_MODE="FIXED (validation set file)"
elif [ "$USE_SEED" = true ]; then
    SELECTION_MODE="SEED ($SEED - reproduzível)"
else
    SELECTION_MODE="RANDOM (não reproduzível)"
fi

echo "========================================"
echo "  VALIDAÇÃO GYNSURG - SURGICAL VIDEO AI"
echo "========================================"
echo ""
echo "Dataset: $GYNSURG_PATH"
echo "Versão do modelo: $MODEL_VERSION"
echo "Confidence threshold: $CONF_THRESHOLD"
echo "Modo de seleção: $SELECTION_MODE"
echo "Saída: $OUTPUT_DIR"

# Criar diretórios
mkdir -p "$OUTPUT_DIR"
mkdir -p "$WORK_DIR/models"

# Baixar modelo do S3 se necessário
echo ""
echo "[1/5] Verificando modelo..."
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

# Filtrar warnings do NNPACK (irrelevante quando usando GPU)
filter_nnpack() { grep -v "NNPACK.cpp" || true; }

# Processar clips de bleeding
echo ""
echo "[2/5] Processando clips de BLEEDING..."
BLEEDING_DIR="$GYNSURG_PATH/GynSurg_bleeding_dataset/Bleeding"
BLEEDING_OUTPUT="$OUTPUT_DIR/bleeding_results"
mkdir -p "$BLEEDING_OUTPUT"

# Selecionar clips baseado no modo escolhido
VALIDATION_SET_DIR="$GYNSURG_PATH/validation_sets"

if [ "$USE_FIXED_SET" = true ]; then
    # Usar arquivo de validation set fixo
    if [ ! -f "$VALIDATION_SET_DIR/validation_set_bleeding.txt" ]; then
        echo "❌ Validation set não encontrado. Execute primeiro:"
        echo "   ./scripts/generate-validation-set.sh $GYNSURG_PATH"
        exit 1
    fi
    echo "   Modo: FIXED (arquivo de validation set)"
    BLEEDING_CLIPS=$(cat "$VALIDATION_SET_DIR/validation_set_bleeding.txt")
elif [ "$USE_SEED" = true ]; then
    # Usar shuf com seed fixo
    echo "   Modo: SEED ($SEED)"
    BLEEDING_CLIPS=$(ls "$BLEEDING_DIR"/*.mp4 | shuf --random-source=<(yes $SEED) | head -10)
else
    # Usar shuf aleatório (não reproduzível)
    echo "   Modo: RANDOM (não reproduzível)"
    BLEEDING_CLIPS=$(ls "$BLEEDING_DIR"/*.mp4 | shuf | head -10)
fi

for clip in $BLEEDING_CLIPS; do
    clip_name=$(basename "$clip" .mp4)
    echo "   Processando: $clip_name"

    yolo detect predict \
        model="$MODEL_PATH" \
        source="$clip" \
        project="$BLEEDING_OUTPUT" \
        name="$clip_name" \
        exist_ok=True \
        save=True \
        save_txt=True \
        save_conf=True \
        conf=$CONF_THRESHOLD \
        verbose=False 2>&1 | filter_nnpack
done

# Processar clips de non-bleeding
echo ""
echo "[3/5] Processando clips de NON-BLEEDING..."
NON_BLEEDING_DIR="$GYNSURG_PATH/GynSurg_bleeding_dataset/Non_bleeding"
NON_BLEEDING_OUTPUT="$OUTPUT_DIR/non_bleeding_results"
mkdir -p "$NON_BLEEDING_OUTPUT"

if [ "$USE_FIXED_SET" = true ]; then
    # Usar arquivo de validation set fixo
    if [ ! -f "$VALIDATION_SET_DIR/validation_set_non_bleeding.txt" ]; then
        echo "❌ Validation set não encontrado. Execute primeiro:"
        echo "   ./scripts/generate-validation-set.sh $GYNSURG_PATH"
        exit 1
    fi
    NON_BLEEDING_CLIPS=$(cat "$VALIDATION_SET_DIR/validation_set_non_bleeding.txt")
elif [ "$USE_SEED" = true ]; then
    # Usar shuf com seed fixo
    NON_BLEEDING_CLIPS=$(ls "$NON_BLEEDING_DIR"/*.mp4 | shuf --random-source=<(yes $SEED) | head -10)
else
    # Usar shuf aleatório (não reproduzível)
    NON_BLEEDING_CLIPS=$(ls "$NON_BLEEDING_DIR"/*.mp4 | shuf | head -10)
fi

for clip in $NON_BLEEDING_CLIPS; do
    clip_name=$(basename "$clip" .mp4)
    echo "   Processando: $clip_name"

    yolo detect predict \
        model="$MODEL_PATH" \
        source="$clip" \
        project="$NON_BLEEDING_OUTPUT" \
        name="$clip_name" \
        exist_ok=True \
        save=True \
        save_txt=True \
        save_conf=True \
        conf=$CONF_THRESHOLD \
        verbose=False 2>&1 | filter_nnpack
done

# Gerar relatório de validação
echo ""
echo "[4/5] Gerando relatório de validação..."

python3 << EOF
import os
import json
import subprocess
from pathlib import Path
from datetime import datetime

output_dir = Path("$OUTPUT_DIR")
bleeding_dir = output_dir / "bleeding_results"
non_bleeding_dir = output_dir / "non_bleeding_results"

def get_video_frame_count(video_path):
    """Obtém número de frames de um vídeo usando ffprobe."""
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-count_frames",
            "-show_entries", "stream=nb_read_frames",
            "-of", "csv=p=0",
            str(video_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            return int(result.stdout.strip())
    except:
        pass
    # Fallback: assume 3 segundos @ 30fps = 90 frames
    return 90

def count_detections(results_dir, class_names=["grasper", "blood"]):
    """Conta detecções nos arquivos de labels e frames totais dos vídeos."""
    stats = {name: 0 for name in class_names}
    stats["total_frames"] = 0
    stats["frames_with_blood"] = 0
    stats["frames_with_grasper"] = 0

    for clip_dir in results_dir.iterdir():
        if not clip_dir.is_dir():
            continue

        # Contar frames reais do vídeo de saída (AVI)
        avi_files = list(clip_dir.glob("*.avi"))
        if avi_files:
            clip_frames = get_video_frame_count(avi_files[0])
            stats["total_frames"] += clip_frames
        else:
            # Se não houver AVI, assumir 90 frames (3s @ 30fps)
            stats["total_frames"] += 90

        # Contar detecções nos labels
        labels_dir = clip_dir / "labels"
        if not labels_dir.exists():
            continue

        for label_file in labels_dir.glob("*.txt"):
            has_blood = False
            has_grasper = False

            with open(label_file) as f:
                for line in f:
                    parts = line.strip().split()
                    if parts:
                        class_id = int(parts[0])
                        if class_id == 0:
                            stats["grasper"] += 1
                            has_grasper = True
                        elif class_id == 1:
                            stats["blood"] += 1
                            has_blood = True

            if has_blood:
                stats["frames_with_blood"] += 1
            if has_grasper:
                stats["frames_with_grasper"] += 1

    return stats

# Coletar estatísticas
bleeding_stats = count_detections(bleeding_dir)
non_bleeding_stats = count_detections(non_bleeding_dir)

# Calcular métricas
report = {
    "validation_date": datetime.now().isoformat(),
    "model_version": "$MODEL_VERSION",
    "model_path": "$MODEL_PATH",
    "confidence_threshold": $CONF_THRESHOLD,
    "selection_mode": "$SELECTION_MODE",
    "dataset": "GynSurg Action Recognition (Bleeding subset)",
    "bleeding_clips": {
        "clips_processed": 10,
        "total_frames": bleeding_stats["total_frames"],
        "blood_detections": bleeding_stats["blood"],
        "grasper_detections": bleeding_stats["grasper"],
        "frames_with_blood": bleeding_stats["frames_with_blood"],
        "blood_detection_rate": round(bleeding_stats["frames_with_blood"] / max(bleeding_stats["total_frames"], 1) * 100, 2)
    },
    "non_bleeding_clips": {
        "clips_processed": 10,
        "total_frames": non_bleeding_stats["total_frames"],
        "blood_detections": non_bleeding_stats["blood"],
        "grasper_detections": non_bleeding_stats["grasper"],
        "frames_with_blood": non_bleeding_stats["frames_with_blood"],
        "false_positive_rate": round(non_bleeding_stats["frames_with_blood"] / max(non_bleeding_stats["total_frames"], 1) * 100, 2)
    }
}

# Salvar relatório
report_path = output_dir / "validation_report.json"
with open(report_path, "w") as f:
    json.dump(report, f, indent=2)

# Imprimir resumo
print("\n" + "="*50)
print("RELATÓRIO DE VALIDAÇÃO CROSS-DATASET")
print("="*50)
print(f"\nModelo treinado em: CholecSeg8k")
print(f"Validado em: GynSurg (Cirurgias Ginecológicas)")
print(f"\n--- CLIPS COM BLEEDING ---")
print(f"Frames analisados: {bleeding_stats['total_frames']}")
print(f"Detecções de blood: {bleeding_stats['blood']}")
print(f"Detecções de grasper: {bleeding_stats['grasper']}")
print(f"Taxa de detecção de blood: {report['bleeding_clips']['blood_detection_rate']}%")
print(f"\n--- CLIPS SEM BLEEDING ---")
print(f"Frames analisados: {non_bleeding_stats['total_frames']}")
print(f"Detecções de blood (falso positivo): {non_bleeding_stats['blood']}")
print(f"Detecções de grasper: {non_bleeding_stats['grasper']}")
print(f"Taxa de falso positivo: {report['non_bleeding_clips']['false_positive_rate']}%")
print(f"\nRelatório salvo em: {report_path}")
EOF

# Upload para S3 (opcional)
echo ""
if [ "$UPLOAD_TO_S3" = true ]; then
    echo "[5/5] Fazendo upload para S3..."
    aws s3 sync "$OUTPUT_DIR/" "s3://$S3_RESULTS_BUCKET/validation_gynsurg_$TIMESTAMP/" --only-show-errors
    echo "✅ Resultados enviados para S3"
else
    echo "[5/5] Upload para S3 pulado (use --upload para enviar)"
fi

echo ""
echo "========================================"
echo "  VALIDAÇÃO CONCLUÍDA!"
echo "========================================"
echo ""
echo "Resultados em: $OUTPUT_DIR"
echo ""
