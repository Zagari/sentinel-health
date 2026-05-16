#!/bin/bash
# =============================================================================
# Script para DESLIGAR infraestrutura de inferência
# Destrói: SageMaker Endpoint
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "========================================"
echo "  DESTRUINDO INFRA DE INFERÊNCIA"
echo "========================================"
echo ""

cd "$PROJECT_ROOT/terraform/environments/inference"

# Verificar se há estado
if [ ! -f "terraform.tfstate" ]; then
    echo "Nenhuma infraestrutura encontrada para destruir."
    exit 0
fi

echo "Este script irá destruir:"
echo "  - SageMaker Endpoint"
echo "  - SageMaker Endpoint Configuration"
echo "  - SageMaker Model"
echo ""

read -p "Confirma a destruição do endpoint? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "Operação cancelada."
    exit 0
fi

# Destruir
echo ""
echo "Destruindo endpoint de inferência..."
terraform destroy -auto-approve

echo ""
echo "========================================"
echo "  ENDPOINT DESTRUÍDO!"
echo "========================================"
echo ""
echo "Custos de SageMaker interrompidos."
echo ""
echo "Para recriar o endpoint posteriormente:"
echo "  ./scripts/infra-up-inference.sh"
