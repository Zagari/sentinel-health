#!/bin/bash
# =============================================================================
# Script para DESLIGAR infraestrutura de treinamento
# Preserva: S3 buckets (datasets e modelos)
# Destrói: EC2 instance
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "========================================"
echo "  DESTRUINDO INFRA DE TREINAMENTO"
echo "========================================"
echo ""

cd "$PROJECT_ROOT/terraform/environments/training"

# Verificar se há estado
if [ ! -f "terraform.tfstate" ]; then
    echo "Nenhuma infraestrutura encontrada para destruir."
    exit 0
fi

echo "ATENÇÃO: Este script irá destruir:"
echo "  - EC2 Instance (GPU de treinamento)"
echo ""
echo "Os seguintes recursos serão PRESERVADOS:"
echo "  - S3 Buckets (datasets, models, results)"
echo ""

read -p "O modelo foi salvo no S3? (yes/no): " saved
if [ "$saved" != "yes" ]; then
    echo ""
    echo "AVISO: Certifique-se de que o modelo foi salvo antes de destruir!"
    echo "Execute na instância EC2:"
    echo "  aws s3 cp ./results/surgical_detection/weights/best.pt s3://surgical-detection-models-dev/trained/"
    echo ""
    read -p "Deseja continuar mesmo assim? (yes/no): " continue_anyway
    if [ "$continue_anyway" != "yes" ]; then
        echo "Operação cancelada."
        exit 0
    fi
fi

# Destruir apenas o módulo de treinamento (preserva storage)
echo ""
echo "Destruindo infraestrutura de treinamento..."
terraform destroy -target=module.training -auto-approve

echo ""
echo "========================================"
echo "  INFRAESTRUTURA DESTRUÍDA!"
echo "========================================"
echo ""
echo "Custos de EC2 interrompidos."
echo "Buckets S3 preservados."
echo ""
echo "Para verificar seus modelos:"
echo "  aws s3 ls s3://surgical-detection-models-dev/trained/"
