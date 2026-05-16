#!/bin/bash
# =============================================================================
# Prepara amostra do GynSurg para upload no S3
# Seleciona clips representativos de bleeding e non-bleeding
# =============================================================================

set -e

# Configurações
S3_BUCKET="surgical-detection-datasets-dev"
SAMPLE_SIZE=50  # clips por categoria

# Verificar argumentos
if [ -z "$1" ]; then
    echo "Uso: $0 <caminho_gynsurg_action_3sec>"
    echo ""
    echo "Exemplo:"
    echo "  $0 /path/to/GynSurg_Action_3sec"
    exit 1
fi

GYNSURG_PATH="$1"
SAMPLE_DIR="/tmp/gynsurg_sample"

# Verificar se diretório existe
if [ ! -d "$GYNSURG_PATH/GynSurg_bleeding_dataset" ]; then
    echo "❌ Dataset de bleeding não encontrado em: $GYNSURG_PATH/GynSurg_bleeding_dataset"
    exit 1
fi

echo "========================================"
echo "  PREPARAÇÃO AMOSTRA GYNSURG"
echo "========================================"
echo ""
echo "Origem: $GYNSURG_PATH"
echo "Clips por categoria: $SAMPLE_SIZE"

# Criar diretório temporário
rm -rf "$SAMPLE_DIR"
mkdir -p "$SAMPLE_DIR/bleeding"
mkdir -p "$SAMPLE_DIR/non_bleeding"

# Selecionar clips de bleeding (aleatório)
echo ""
echo "[1/4] Selecionando clips de BLEEDING..."
BLEEDING_DIR="$GYNSURG_PATH/GynSurg_bleeding_dataset/Bleeding"
ls "$BLEEDING_DIR"/*.mp4 | shuf | head -$SAMPLE_SIZE | while read clip; do
    cp "$clip" "$SAMPLE_DIR/bleeding/"
    echo "   ✓ $(basename "$clip")"
done

# Selecionar clips de non-bleeding (aleatório)
echo ""
echo "[2/4] Selecionando clips de NON-BLEEDING..."
NON_BLEEDING_DIR="$GYNSURG_PATH/GynSurg_bleeding_dataset/Non_bleeding"
ls "$NON_BLEEDING_DIR"/*.mp4 | shuf | head -$SAMPLE_SIZE | while read clip; do
    cp "$clip" "$SAMPLE_DIR/non_bleeding/"
    echo "   ✓ $(basename "$clip")"
done

# Calcular tamanho
echo ""
echo "[3/4] Calculando tamanho da amostra..."
SAMPLE_SIZE_MB=$(du -sm "$SAMPLE_DIR" | cut -f1)
echo "   Tamanho total: ${SAMPLE_SIZE_MB} MB"

# Criar arquivo de metadados
echo ""
echo "[4/4] Criando metadados..."
cat > "$SAMPLE_DIR/metadata.json" << EOF
{
    "dataset": "GynSurg Action Recognition",
    "type": "sample",
    "created_at": "$(date -Iseconds)",
    "clips_per_category": $SAMPLE_SIZE,
    "categories": {
        "bleeding": {
            "count": $(ls "$SAMPLE_DIR/bleeding"/*.mp4 2>/dev/null | wc -l | tr -d ' '),
            "description": "Clips com sangramento visível durante cirurgia"
        },
        "non_bleeding": {
            "count": $(ls "$SAMPLE_DIR/non_bleeding"/*.mp4 2>/dev/null | wc -l | tr -d ' '),
            "description": "Clips sem sangramento visível"
        }
    },
    "source": {
        "original_bleeding_clips": 977,
        "original_non_bleeding_clips": 1064,
        "resolution": "3840x2160",
        "fps": 30,
        "duration_seconds": 3
    },
    "license": "CC BY-NC-ND 4.0",
    "citation": "GynSurg: A Comprehensive Gynecology Laparoscopic Surgery Dataset (2025)"
}
EOF

# Listar conteúdo
cat > "$SAMPLE_DIR/bleeding/clips.txt" << EOF
# Lista de clips de bleeding selecionados
$(ls "$SAMPLE_DIR/bleeding"/*.mp4 | xargs -n1 basename)
EOF

cat > "$SAMPLE_DIR/non_bleeding/clips.txt" << EOF
# Lista de clips non-bleeding selecionados
$(ls "$SAMPLE_DIR/non_bleeding"/*.mp4 | xargs -n1 basename)
EOF

echo ""
echo "========================================"
echo "  AMOSTRA PREPARADA"
echo "========================================"
echo ""
echo "Localização: $SAMPLE_DIR"
echo "Bleeding clips: $(ls "$SAMPLE_DIR/bleeding"/*.mp4 | wc -l | tr -d ' ')"
echo "Non-bleeding clips: $(ls "$SAMPLE_DIR/non_bleeding"/*.mp4 | wc -l | tr -d ' ')"
echo "Tamanho total: ${SAMPLE_SIZE_MB} MB"
echo ""
echo "Para fazer upload no S3, execute:"
echo "  aws s3 sync $SAMPLE_DIR s3://$S3_BUCKET/gynsurg_sample/ --only-show-errors"
echo ""
read -p "Deseja fazer upload agora? (s/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Ss]$ ]]; then
    echo ""
    echo "Fazendo upload para S3..."
    aws s3 sync "$SAMPLE_DIR" "s3://$S3_BUCKET/gynsurg_sample/" --only-show-errors
    echo ""
    echo "✅ Upload concluído!"
    echo "   s3://$S3_BUCKET/gynsurg_sample/"
    echo ""
    echo "Para listar os arquivos:"
    echo "  aws s3 ls s3://$S3_BUCKET/gynsurg_sample/ --recursive --human-readable"
fi
