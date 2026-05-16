#!/bin/bash
# =============================================================================
# Validação de todas as versões do modelo
# Roda validação com o script corrigido para todas as versões e gera comparativo
# =============================================================================

set -e

WORK_DIR="$HOME/surgical-training"
VENV_DIR="$HOME/surgical-venv"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Verificar argumentos
if [ -z "$1" ]; then
    echo "Uso: $0 <caminho_gynsurg>"
    echo ""
    echo "Exemplo:"
    echo "  $0 /path/to/GynSurg_Action_3sec"
    exit 1
fi

GYNSURG_PATH="$1"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
COMPARISON_DIR="$WORK_DIR/comparison_$TIMESTAMP"

# Definir versões a validar (adicione ou remova conforme necessário)
declare -A MODELS
MODELS["v1_baseline"]="best_v1_baseline.pt"
MODELS["v2_classweight"]="best_v2_classweight.pt"
MODELS["v3_finetuned"]="best_v3_finetuned.pt"
MODELS["v4_smallbbox"]="best_v4_smallbbox.pt"
MODELS["v5_negative_only"]="best_v5_negative_only.pt"

echo "========================================"
echo "  VALIDAÇÃO DE TODAS AS VERSÕES"
echo "========================================"
echo ""
echo "GynSurg path: $GYNSURG_PATH"
echo "Output: $COMPARISON_DIR"
echo ""

# Criar diretório de comparação
mkdir -p "$COMPARISON_DIR"

# Ativar ambiente virtual
source "$VENV_DIR/bin/activate"

# Array para guardar resultados
declare -A RESULTS

# Validar cada versão
for version in "${!MODELS[@]}"; do
    model_file="${MODELS[$version]}"
    model_path="$WORK_DIR/models/$model_file"

    echo ""
    echo "========================================"
    echo "  Validando: $version"
    echo "========================================"

    # Verificar se modelo existe
    if [ ! -f "$model_path" ]; then
        echo "⚠️  Modelo não encontrado: $model_path"
        echo "   Pulando $version..."
        RESULTS[$version]="MODELO_NAO_ENCONTRADO"
        continue
    fi

    # Copiar modelo para best.pt
    echo "Copiando $model_file -> best.pt"
    cp "$model_path" "$WORK_DIR/models/best.pt"

    # Rodar validação
    echo "Rodando validação..."
    "$SCRIPT_DIR/validate-gynsurg.sh" "$GYNSURG_PATH" --fixed --version "$version"

    # Encontrar o diretório de resultado mais recente
    LATEST_RESULT=$(ls -td "$WORK_DIR"/validation_gynsurg_* 2>/dev/null | head -1)

    if [ -n "$LATEST_RESULT" ] && [ -f "$LATEST_RESULT/validation_report.json" ]; then
        # Copiar resultado para diretório de comparação
        cp "$LATEST_RESULT/validation_report.json" "$COMPARISON_DIR/${version}_report.json"
        RESULTS[$version]="OK"
        echo "✅ $version validado com sucesso"
    else
        RESULTS[$version]="FALHA"
        echo "❌ Falha na validação de $version"
    fi
done

# Gerar relatório comparativo
echo ""
echo "========================================"
echo "  Gerando relatório comparativo..."
echo "========================================"

python3 << EOF
import json
from pathlib import Path

comparison_dir = Path("$COMPARISON_DIR")
versions = ["v1_baseline", "v2_classweight", "v3_finetuned", "v4_smallbbox", "v5_negative_only"]

results = []

for version in versions:
    report_file = comparison_dir / f"{version}_report.json"
    if report_file.exists():
        with open(report_file) as f:
            data = json.load(f)
            results.append({
                "version": version,
                "detection_rate": data["bleeding_clips"]["blood_detection_rate"],
                "false_positive_rate": data["non_bleeding_clips"]["false_positive_rate"],
                "bleeding_frames": data["bleeding_clips"]["total_frames"],
                "non_bleeding_frames": data["non_bleeding_clips"]["total_frames"],
                "conf_threshold": data.get("confidence_threshold", 0.3)
            })
    else:
        results.append({
            "version": version,
            "detection_rate": None,
            "false_positive_rate": None,
            "bleeding_frames": None,
            "non_bleeding_frames": None,
            "conf_threshold": None
        })

# Imprimir tabela comparativa
print("\n" + "="*80)
print("COMPARATIVO DE TODAS AS VERSÕES DO MODELO")
print("="*80)
print(f"\n{'Versão':<20} {'Det. Rate':<12} {'FP Rate':<12} {'Frames Bleed':<14} {'Frames Non':<12}")
print("-"*80)

for r in results:
    if r["detection_rate"] is not None:
        print(f"{r['version']:<20} {r['detection_rate']:>8.2f}%    {r['false_positive_rate']:>8.2f}%    {r['bleeding_frames']:>10}     {r['non_bleeding_frames']:>10}")
    else:
        print(f"{r['version']:<20} {'N/A':>10}    {'N/A':>10}    {'N/A':>12}     {'N/A':>10}")

print("-"*80)

# Encontrar melhor modelo (maior detecção com menor FP)
valid_results = [r for r in results if r["detection_rate"] is not None]
if valid_results:
    # Calcular score: detection_rate - false_positive_rate
    for r in valid_results:
        r["score"] = r["detection_rate"] - r["false_positive_rate"]

    best = max(valid_results, key=lambda x: x["score"])
    print(f"\n🏆 Melhor modelo: {best['version']}")
    print(f"   Detecção: {best['detection_rate']:.2f}% | Falso Positivo: {best['false_positive_rate']:.2f}%")
    print(f"   Score (Det - FP): {best['score']:.2f}")

# Salvar comparativo em JSON
comparison_data = {
    "timestamp": "$TIMESTAMP",
    "gynsurg_path": "$GYNSURG_PATH",
    "results": results
}

with open(comparison_dir / "comparison_report.json", "w") as f:
    json.dump(comparison_data, f, indent=2)

print(f"\nRelatório salvo em: {comparison_dir / 'comparison_report.json'}")
EOF

echo ""
echo "========================================"
echo "  VALIDAÇÃO COMPLETA!"
echo "========================================"
echo ""
echo "Resultados em: $COMPARISON_DIR"
echo ""
echo "Arquivos gerados:"
ls -la "$COMPARISON_DIR"
echo ""
