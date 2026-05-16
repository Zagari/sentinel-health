#!/bin/bash
# =============================================================================
# Compara resultados de validações do modelo
# Pode comparar duas validações específicas ou todas as validações existentes
# =============================================================================

set -e

WORK_DIR="$HOME/surgical-training"

show_help() {
    echo "Uso: $0 [diretório1] [diretório2]"
    echo ""
    echo "Modos:"
    echo "  Sem argumentos    Compara todas as validações encontradas"
    echo "  Com 2 diretórios  Compara apenas as duas validações especificadas"
    echo ""
    echo "Exemplos:"
    echo "  $0                                           # Compara todas"
    echo "  $0 validation_gynsurg_20260510_120000 validation_gynsurg_20260510_140000"
    echo ""
    echo "Validações são buscadas em: $WORK_DIR"
}

# Função para extrair métricas de um relatório
extract_metrics() {
    local report_file="$1"

    if [ ! -f "$report_file" ]; then
        echo "null|null|null|null|null"
        return
    fi

    python3 << EOF
import json
import sys

try:
    with open("$report_file") as f:
        data = json.load(f)

    version = data.get("model_version", "unknown")
    date = data.get("validation_date", "unknown")[:19]
    detection_rate = data.get("bleeding_clips", {}).get("blood_detection_rate", 0)
    false_positive = data.get("non_bleeding_clips", {}).get("false_positive_rate", 0)
    selection_mode = data.get("selection_mode", "unknown")

    print(f"{version}|{date}|{detection_rate}|{false_positive}|{selection_mode}")
except Exception as e:
    print(f"error|error|0|0|error")
EOF
}

# Função para comparar duas validações
compare_two() {
    local dir1="$1"
    local dir2="$2"

    local report1="$dir1/validation_report.json"
    local report2="$dir2/validation_report.json"

    echo ""
    echo "========================================"
    echo "  COMPARAÇÃO DE VALIDAÇÕES"
    echo "========================================"

    python3 << EOF
import json
from pathlib import Path

def load_report(path):
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return None

report1 = load_report("$report1")
report2 = load_report("$report2")

if not report1 or not report2:
    print("❌ Erro: Um ou ambos os relatórios não foram encontrados")
    exit(1)

v1 = report1.get("model_version", "unknown")
v2 = report2.get("model_version", "unknown")

det1 = report1.get("bleeding_clips", {}).get("blood_detection_rate", 0)
det2 = report2.get("bleeding_clips", {}).get("blood_detection_rate", 0)

fp1 = report1.get("non_bleeding_clips", {}).get("false_positive_rate", 0)
fp2 = report2.get("non_bleeding_clips", {}).get("false_positive_rate", 0)

det_diff = det2 - det1
fp_diff = fp2 - fp1

det_arrow = "↑" if det_diff > 0 else "↓" if det_diff < 0 else "="
fp_arrow = "↓" if fp_diff < 0 else "↑" if fp_diff > 0 else "="

# Determinar se é melhoria (detection up, false positive down)
det_color = "✅" if det_diff > 0 else "❌" if det_diff < 0 else "➖"
fp_color = "✅" if fp_diff < 0 else "❌" if fp_diff > 0 else "➖"

print(f"""
┌─────────────────────────────────────────────────────────────────┐
│                    COMPARAÇÃO DE MODELOS                        │
├─────────────────────────────────────────────────────────────────┤
│  Métrica              │  {v1:^12} │  {v2:^12} │  Diferença   │
├─────────────────────────────────────────────────────────────────┤
│  Taxa de Detecção     │  {det1:^10.2f}% │  {det2:^10.2f}% │ {det_color} {det_arrow} {abs(det_diff):+.2f}%   │
│  Falso Positivo       │  {fp1:^10.2f}% │  {fp2:^10.2f}% │ {fp_color} {fp_arrow} {abs(fp_diff):+.2f}%   │
└─────────────────────────────────────────────────────────────────┘
""")

# Resumo
improvements = 0
if det_diff > 0:
    improvements += 1
if fp_diff < 0:
    improvements += 1

if improvements == 2:
    print("🎉 RESULTADO: Melhoria em ambas as métricas!")
elif improvements == 1:
    print("⚠️  RESULTADO: Melhoria parcial (uma métrica melhorou, outra piorou)")
else:
    print("❌ RESULTADO: Regressão em ambas as métricas")
EOF
}

# Função para comparar todas as validações
compare_all() {
    echo ""
    echo "========================================"
    echo "  COMPARAÇÃO DE TODAS AS VALIDAÇÕES"
    echo "========================================"
    echo ""
    echo "Buscando validações em: $WORK_DIR"
    echo ""

    # Encontrar todos os diretórios de validação
    validation_dirs=$(find "$WORK_DIR" -maxdepth 1 -type d -name "validation_gynsurg_*" | sort)

    if [ -z "$validation_dirs" ]; then
        echo "❌ Nenhuma validação encontrada em $WORK_DIR"
        exit 1
    fi

    # Contar validações
    count=$(echo "$validation_dirs" | wc -l)
    echo "Encontradas $count validações"
    echo ""

    python3 << EOF
import json
from pathlib import Path
from datetime import datetime

validations = []
validation_dirs = """$validation_dirs""".strip().split('\n')

for dir_path in validation_dirs:
    report_path = Path(dir_path) / "validation_report.json"
    if report_path.exists():
        try:
            with open(report_path) as f:
                data = json.load(f)

            validations.append({
                "dir": Path(dir_path).name,
                "version": data.get("model_version", "unknown"),
                "date": data.get("validation_date", "")[:16],
                "detection_rate": data.get("bleeding_clips", {}).get("blood_detection_rate", 0),
                "false_positive": data.get("non_bleeding_clips", {}).get("false_positive_rate", 0),
                "selection_mode": data.get("selection_mode", "unknown")[:10]
            })
        except:
            pass

if not validations:
    print("❌ Nenhum relatório de validação encontrado")
    exit(1)

# Ordenar por data
validations.sort(key=lambda x: x["date"])

# Imprimir tabela
print("┌" + "─" * 100 + "┐")
print(f"│ {'Versão':<15} │ {'Data':<16} │ {'Detecção':<10} │ {'FP':<10} │ {'Δ Det':<8} │ {'Δ FP':<8} │ {'Modo':<10} │")
print("├" + "─" * 100 + "┤")

prev = None
for v in validations:
    det = v["detection_rate"]
    fp = v["false_positive"]

    if prev:
        det_diff = det - prev["detection_rate"]
        fp_diff = fp - prev["false_positive"]

        det_str = f"{det_diff:+.2f}%" if det_diff != 0 else "="
        fp_str = f"{fp_diff:+.2f}%" if fp_diff != 0 else "="

        # Colorir baseado em melhoria
        det_indicator = "✅" if det_diff > 0 else "❌" if det_diff < 0 else "➖"
        fp_indicator = "✅" if fp_diff < 0 else "❌" if fp_diff > 0 else "➖"

        det_col = f"{det_indicator}{det_str}"
        fp_col = f"{fp_indicator}{fp_str}"
    else:
        det_col = "(base)"
        fp_col = "(base)"

    print(f"│ {v['version']:<15} │ {v['date']:<16} │ {det:>8.2f}% │ {fp:>8.2f}% │ {det_col:<8} │ {fp_col:<8} │ {v['selection_mode']:<10} │")
    prev = v

print("└" + "─" * 100 + "┘")

# Resumo
if len(validations) >= 2:
    first = validations[0]
    last = validations[-1]

    total_det_change = last["detection_rate"] - first["detection_rate"]
    total_fp_change = last["false_positive"] - first["false_positive"]

    print(f"""
📊 RESUMO GERAL (primeira → última validação):
   Taxa de Detecção: {first["detection_rate"]:.2f}% → {last["detection_rate"]:.2f}% ({total_det_change:+.2f}%)
   Falso Positivo:   {first["false_positive"]:.2f}% → {last["false_positive"]:.2f}% ({total_fp_change:+.2f}%)
""")

# Melhor modelo
best_by_detection = max(validations, key=lambda x: x["detection_rate"])
best_by_fp = min(validations, key=lambda x: x["false_positive"])

print(f"🏆 Melhor detecção: {best_by_detection['version']} ({best_by_detection['detection_rate']:.2f}%)")
print(f"🏆 Menor FP:        {best_by_fp['version']} ({best_by_fp['false_positive']:.2f}%)")
EOF
}

# Main
if [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
    show_help
    exit 0
fi

if [ $# -eq 0 ]; then
    # Comparar todas as validações
    compare_all
elif [ $# -eq 2 ]; then
    # Comparar duas validações específicas
    dir1="$1"
    dir2="$2"

    # Se não for caminho absoluto, adicionar WORK_DIR
    [[ "$dir1" != /* ]] && dir1="$WORK_DIR/$dir1"
    [[ "$dir2" != /* ]] && dir2="$WORK_DIR/$dir2"

    compare_two "$dir1" "$dir2"
else
    echo "❌ Erro: Forneça 0 argumentos (comparar todas) ou 2 diretórios"
    show_help
    exit 1
fi
