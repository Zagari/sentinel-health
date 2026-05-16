#!/bin/bash
# =============================================================================
# Analisa diferentes thresholds de confiança para encontrar o ponto ótimo
# Executa validações com múltiplos thresholds e gera relatório comparativo
# =============================================================================

set -e

WORK_DIR="$HOME/surgical-training"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

show_help() {
    echo "Uso: $0 <caminho_gynsurg_action_3sec> [opções]"
    echo ""
    echo "Opções:"
    echo "  --version TAG    Tag de versão do modelo (ex: v1_baseline)"
    echo "  --thresholds     Lista de thresholds separados por vírgula (default: 0.1,0.2,0.3,0.4,0.5,0.6,0.7)"
    echo ""
    echo "Exemplo:"
    echo "  $0 /path/to/GynSurg --version v1_baseline"
    echo "  $0 /path/to/GynSurg --version v1_baseline --thresholds 0.3,0.4,0.5,0.6"
    echo ""
    echo "IMPORTANTE: Requer que o validation set fixo já tenha sido gerado com:"
    echo "  ./scripts/generate-validation-set.sh /path/to/GynSurg"
}

# Verificar argumentos
if [ -z "$1" ] || [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
    show_help
    exit 0
fi

GYNSURG_PATH="$1"
MODEL_VERSION="baseline"
THRESHOLDS="0.1,0.2,0.3,0.4,0.5,0.6,0.7"

# Processar argumentos
shift
while [[ $# -gt 0 ]]; do
    case $1 in
        --version)
            MODEL_VERSION="$2"
            shift 2
            ;;
        --thresholds)
            THRESHOLDS="$2"
            shift 2
            ;;
        *)
            echo "Opção desconhecida: $1"
            show_help
            exit 1
            ;;
    esac
done

# Verificar se diretório existe
if [ ! -d "$GYNSURG_PATH/GynSurg_bleeding_dataset" ]; then
    echo "❌ Dataset de bleeding não encontrado em: $GYNSURG_PATH/GynSurg_bleeding_dataset"
    exit 1
fi

# Verificar se validation set existe
if [ ! -f "$GYNSURG_PATH/validation_sets/validation_set_bleeding.txt" ]; then
    echo "❌ Validation set não encontrado. Execute primeiro:"
    echo "   ./scripts/generate-validation-set.sh $GYNSURG_PATH"
    exit 1
fi

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_DIR="$WORK_DIR/threshold_analysis_$TIMESTAMP"
mkdir -p "$OUTPUT_DIR"

echo "========================================"
echo "  ANÁLISE DE CONFIDENCE THRESHOLD"
echo "========================================"
echo ""
echo "Dataset: $GYNSURG_PATH"
echo "Versão do modelo: $MODEL_VERSION"
echo "Thresholds a testar: $THRESHOLDS"
echo "Saída: $OUTPUT_DIR"
echo ""

# Converter thresholds para array
IFS=',' read -ra THRESHOLD_ARRAY <<< "$THRESHOLDS"

# Executar validação para cada threshold
for conf in "${THRESHOLD_ARRAY[@]}"; do
    echo ""
    echo "========================================"
    echo "  Testando threshold: $conf"
    echo "========================================"

    # Executar validação
    "$SCRIPT_DIR/validate-gynsurg.sh" "$GYNSURG_PATH" \
        --fixed \
        --version "${MODEL_VERSION}_conf${conf}" \
        --conf "$conf"

    # Encontrar o diretório de validação mais recente
    LATEST_VALIDATION=$(ls -td "$WORK_DIR"/validation_gynsurg_* 2>/dev/null | head -1)

    if [ -n "$LATEST_VALIDATION" ] && [ -f "$LATEST_VALIDATION/validation_report.json" ]; then
        # Copiar relatório para o diretório de análise
        cp "$LATEST_VALIDATION/validation_report.json" "$OUTPUT_DIR/report_conf_${conf}.json"
        echo "✅ Relatório salvo: report_conf_${conf}.json"
    else
        echo "⚠️ Relatório não encontrado para threshold $conf"
    fi
done

# Gerar relatório comparativo
echo ""
echo "========================================"
echo "  GERANDO RELATÓRIO COMPARATIVO"
echo "========================================"

python3 << EOF
import json
import glob
from pathlib import Path

output_dir = Path("$OUTPUT_DIR")
reports = []

# Carregar todos os relatórios
for report_file in sorted(output_dir.glob("report_conf_*.json")):
    try:
        with open(report_file) as f:
            data = json.load(f)

        conf = data.get("confidence_threshold", 0)
        detection_rate = data.get("bleeding_clips", {}).get("blood_detection_rate", 0)
        false_positive = data.get("non_bleeding_clips", {}).get("false_positive_rate", 0)

        reports.append({
            "conf": conf,
            "detection_rate": detection_rate,
            "false_positive": false_positive,
            "blood_detections_bleeding": data.get("bleeding_clips", {}).get("blood_detections", 0),
            "blood_detections_non_bleeding": data.get("non_bleeding_clips", {}).get("blood_detections", 0)
        })
    except Exception as e:
        print(f"Erro ao processar {report_file}: {e}")

if not reports:
    print("❌ Nenhum relatório encontrado!")
    exit(1)

# Ordenar por threshold
reports.sort(key=lambda x: x["conf"])

# Imprimir tabela
print("")
print("┌" + "─" * 85 + "┐")
print(f"│ {'Threshold':^10} │ {'Detecção':^12} │ {'Falso Pos':^12} │ {'Det Blood':^12} │ {'FP Blood':^12} │")
print("├" + "─" * 85 + "┤")

for r in reports:
    print(f"│ {r['conf']:^10.2f} │ {r['detection_rate']:^10.2f}% │ {r['false_positive']:^10.2f}% │ {r['blood_detections_bleeding']:^12} │ {r['blood_detections_non_bleeding']:^12} │")

print("└" + "─" * 85 + "┘")

# Encontrar melhor threshold (balanceando detecção e FP)
# Métrica: maximizar (detection_rate - false_positive)
best = max(reports, key=lambda x: x["detection_rate"] - x["false_positive"])
best_detection = max(reports, key=lambda x: x["detection_rate"])
best_fp = min(reports, key=lambda x: x["false_positive"])

print(f"""
📊 ANÁLISE:

🎯 Melhor balanço (det - FP):  conf={best['conf']:.2f}
   → Detecção: {best['detection_rate']:.2f}% | FP: {best['false_positive']:.2f}%

📈 Maior detecção:            conf={best_detection['conf']:.2f}
   → Detecção: {best_detection['detection_rate']:.2f}% | FP: {best_detection['false_positive']:.2f}%

📉 Menor falso positivo:      conf={best_fp['conf']:.2f}
   → Detecção: {best_fp['detection_rate']:.2f}% | FP: {best_fp['false_positive']:.2f}%
""")

# Salvar resumo em JSON
summary = {
    "analysis_date": "$TIMESTAMP",
    "model_version": "$MODEL_VERSION",
    "thresholds_tested": [r["conf"] for r in reports],
    "results": reports,
    "recommendations": {
        "best_balance": {"threshold": best["conf"], "detection": best["detection_rate"], "false_positive": best["false_positive"]},
        "best_detection": {"threshold": best_detection["conf"], "detection": best_detection["detection_rate"], "false_positive": best_detection["false_positive"]},
        "lowest_fp": {"threshold": best_fp["conf"], "detection": best_fp["detection_rate"], "false_positive": best_fp["false_positive"]}
    }
}

summary_path = output_dir / "threshold_analysis_summary.json"
with open(summary_path, 'w') as f:
    json.dump(summary, f, indent=2)

print(f"📁 Resumo salvo em: {summary_path}")
EOF

echo ""
echo "========================================"
echo "  ANÁLISE CONCLUÍDA!"
echo "========================================"
echo ""
echo "Resultados em: $OUTPUT_DIR"
echo ""
