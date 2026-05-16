#!/bin/bash
# =============================================================================
# Script para LIGAR infraestrutura de inferência
# Custo: ~$0.53/hora (SageMaker ml.g4dn.xlarge)
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "========================================"
echo "  SURGICAL VIDEO AI - INFERENCE INFRA"
echo "========================================"
echo ""
echo "Este script irá criar:"
echo "  - SageMaker Endpoint (ml.g4dn.xlarge)"
echo ""
echo "Custo estimado: ~\$0.53/hora"
echo ""

# Verificar Terraform
if ! command -v terraform &> /dev/null; then
    echo "ERRO: Terraform não instalado. Execute: brew install terraform"
    exit 1
fi

# Verificar AWS CLI
if ! aws sts get-caller-identity &> /dev/null; then
    echo "ERRO: AWS CLI não configurado. Execute: aws configure"
    exit 1
fi

# Verificar se modelo existe no S3
MODELS_BUCKET="surgical-detection-models-dev"
echo "Verificando modelo no S3..."
if ! aws s3 ls "s3://${MODELS_BUCKET}/trained/model.tar.gz" &> /dev/null; then
    echo ""
    echo "ERRO: Modelo não encontrado em s3://${MODELS_BUCKET}/trained/model.tar.gz"
    echo ""
    echo "Você precisa:"
    echo "  1. Treinar o modelo primeiro (./scripts/infra-up-training.sh)"
    echo "  2. Ou fazer upload manual:"
    echo "     aws s3 cp model.tar.gz s3://${MODELS_BUCKET}/trained/model.tar.gz"
    echo ""
    exit 1
fi

echo "Modelo encontrado no S3."

cd "$PROJECT_ROOT/terraform/environments/inference"

# Inicializar Terraform
echo ""
echo "Inicializando Terraform..."
terraform init

# Aplicar
echo ""
echo "Criando endpoint de inferência..."
echo "(Isso pode levar 10-15 minutos)"
terraform apply -var="models_bucket=${MODELS_BUCKET}" -auto-approve

echo ""
echo "========================================"
echo "  ENDPOINT CRIADO COM SUCESSO!"
echo "========================================"
echo ""
terraform output
echo ""
echo "PRÓXIMOS PASSOS:"
echo "  1. Testar o endpoint:"
echo "     python src/demo/run_demo.py --video videos/input/test.mp4"
echo ""
echo "  2. APÓS A DEMONSTRAÇÃO, destrua o endpoint:"
echo "     ./scripts/infra-down-inference.sh"
echo ""
echo "LEMBRE-SE: Este endpoint custa ~\$0.53/hora!"
