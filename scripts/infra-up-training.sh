#!/bin/bash
# =============================================================================
# Script para LIGAR infraestrutura de treinamento
# Custo: ~$3.06/hora (EC2 p3.2xlarge)
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "========================================"
echo "  SURGICAL VIDEO AI - TRAINING INFRA"
echo "========================================"
echo ""
echo "Este script irá criar:"
echo "  - S3 Buckets (datasets, models, results)"
echo "  - EC2 p3.2xlarge com GPU V100"
echo ""
echo "Custo estimado: ~\$3.06/hora"
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

cd "$PROJECT_ROOT/terraform/environments/training"

# Inicializar Terraform
echo "Inicializando Terraform..."
terraform init

# Planejar
echo ""
echo "Planejando infraestrutura..."
terraform plan -out=tfplan

# Confirmar
echo ""
read -p "Deseja criar a infraestrutura? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "Operação cancelada."
    exit 0
fi

# Aplicar
echo ""
echo "Criando infraestrutura..."
terraform apply tfplan

echo ""
echo "========================================"
echo "  INFRAESTRUTURA CRIADA COM SUCESSO!"
echo "========================================"
echo ""
terraform output
echo ""
echo "PRÓXIMOS PASSOS:"
echo "  1. Faça upload do dataset para S3:"
echo "     aws s3 sync data/yolo_format/ s3://surgical-detection-datasets-dev/yolo_format/"
echo ""
echo "  2. Conecte via SSH e execute o treinamento:"
echo "     $(terraform output -raw ssh_command 2>/dev/null || echo 'ssh -i your-key.pem ubuntu@<IP>')"
echo "     cd /home/ubuntu/training && ./train.sh"
echo ""
echo "  3. APÓS O TREINO, destrua a infraestrutura:"
echo "     ./scripts/infra-down-training.sh"
echo ""
echo "LEMBRE-SE: Esta instância custa ~\$3.06/hora!"
