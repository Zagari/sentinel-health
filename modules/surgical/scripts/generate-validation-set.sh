#!/bin/bash
# =============================================================================
# Gera um conjunto de validação fixo para comparações reproduzíveis
# Executa uma única vez para criar os arquivos de referência
# =============================================================================

set -e

# Verificar argumentos
if [ -z "$1" ]; then
    echo "Uso: $0 <caminho_gynsurg_action_3sec> [num_clips]"
    echo ""
    echo "Exemplo:"
    echo "  $0 /path/to/GynSurg_Action_3sec"
    echo "  $0 /path/to/GynSurg_Action_3sec 20"
    echo ""
    echo "Gera arquivos:"
    echo "  - validation_set_bleeding.txt"
    echo "  - validation_set_non_bleeding.txt"
    exit 1
fi

GYNSURG_PATH="$1"
NUM_CLIPS=${2:-10}  # Default: 10 clips por categoria
SEED=42

# Verificar se diretório existe
if [ ! -d "$GYNSURG_PATH/GynSurg_bleeding_dataset" ]; then
    echo "❌ Dataset de bleeding não encontrado em: $GYNSURG_PATH/GynSurg_bleeding_dataset"
    exit 1
fi

BLEEDING_DIR="$GYNSURG_PATH/GynSurg_bleeding_dataset/Bleeding"
NON_BLEEDING_DIR="$GYNSURG_PATH/GynSurg_bleeding_dataset/Non_bleeding"
OUTPUT_DIR="$GYNSURG_PATH/validation_sets"

# Criar diretório de saída
mkdir -p "$OUTPUT_DIR"

echo "========================================"
echo "  GERAÇÃO DE VALIDATION SET FIXO"
echo "========================================"
echo ""
echo "Dataset: $GYNSURG_PATH"
echo "Clips por categoria: $NUM_CLIPS"
echo "Seed: $SEED"
echo ""

# Gerar lista de clips de bleeding com seed fixo
echo "Gerando lista de clips de BLEEDING..."
ls "$BLEEDING_DIR"/*.mp4 | shuf --random-source=<(yes $SEED) | head -$NUM_CLIPS > "$OUTPUT_DIR/validation_set_bleeding.txt"
BLEEDING_COUNT=$(wc -l < "$OUTPUT_DIR/validation_set_bleeding.txt")
echo "✅ $BLEEDING_COUNT clips de bleeding selecionados"

# Gerar lista de clips de non-bleeding com seed fixo
echo "Gerando lista de clips de NON-BLEEDING..."
ls "$NON_BLEEDING_DIR"/*.mp4 | shuf --random-source=<(yes $SEED) | head -$NUM_CLIPS > "$OUTPUT_DIR/validation_set_non_bleeding.txt"
NON_BLEEDING_COUNT=$(wc -l < "$OUTPUT_DIR/validation_set_non_bleeding.txt")
echo "✅ $NON_BLEEDING_COUNT clips de non-bleeding selecionados"

# Mostrar clips selecionados
echo ""
echo "--- Clips de BLEEDING selecionados ---"
cat "$OUTPUT_DIR/validation_set_bleeding.txt" | xargs -I {} basename {}

echo ""
echo "--- Clips de NON-BLEEDING selecionados ---"
cat "$OUTPUT_DIR/validation_set_non_bleeding.txt" | xargs -I {} basename {}

echo ""
echo "========================================"
echo "  VALIDATION SET GERADO!"
echo "========================================"
echo ""
echo "Arquivos criados em: $OUTPUT_DIR"
echo "  - validation_set_bleeding.txt"
echo "  - validation_set_non_bleeding.txt"
echo ""
echo "Use com validate-gynsurg.sh --fixed para validações reproduzíveis"
echo ""
