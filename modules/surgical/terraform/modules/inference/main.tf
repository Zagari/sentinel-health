# =============================================================================
# Inference Module - SageMaker Endpoint para Inferência YOLOv8
# =============================================================================
#
# Modelo de produção: v3_finetuned
# - Detecção: 91.72%
# - Falso Positivo: 13.44%
# - Threshold: 0.30
#
# =============================================================================

variable "project_name" {
  description = "Nome do projeto"
  type        = string
  default     = "surgical-detection"
}

variable "environment" {
  description = "Ambiente (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "instance_type" {
  description = "Tipo da instância SageMaker"
  type        = string
  default     = "ml.g4dn.xlarge"  # GPU T4, ~$0.53/hora
}

variable "models_bucket_name" {
  description = "Nome do bucket de modelos"
  type        = string
}

variable "model_version" {
  description = "Versão do modelo (v1_baseline, v2_classweight, v3_finetuned)"
  type        = string
  default     = "v3_finetuned"
}

variable "confidence_threshold" {
  description = "Threshold de confiança para detecções (0.0-1.0)"
  type        = number
  default     = 0.30
}

# -----------------------------------------------------------------------------
# Data Sources
# -----------------------------------------------------------------------------
data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

# -----------------------------------------------------------------------------
# IAM Role para SageMaker
# -----------------------------------------------------------------------------
resource "aws_iam_role" "sagemaker" {
  name = "${var.project_name}-sagemaker-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "sagemaker.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "sagemaker_full" {
  role       = aws_iam_role.sagemaker.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSageMakerFullAccess"
}

resource "aws_iam_role_policy" "sagemaker_s3" {
  name = "${var.project_name}-sagemaker-s3-policy"
  role = aws_iam_role.sagemaker.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::${var.models_bucket_name}",
          "arn:aws:s3:::${var.models_bucket_name}/*"
        ]
      }
    ]
  })
}

# -----------------------------------------------------------------------------
# SageMaker Model
# -----------------------------------------------------------------------------
#
# NOTA: O modelo YOLOv8 (.pt) precisa ser empacotado em model.tar.gz junto
# com um script inference.py para funcionar no SageMaker.
#
# Estrutura do model.tar.gz:
#   model.tar.gz/
#   ├── best.pt              # Modelo YOLOv8 (v3_finetuned)
#   └── code/
#       └── inference.py     # Script de inferência
#
# Para criar o pacote:
#   cd ~/surgical-training/models
#   mkdir -p code
#   cp best_v3_finetuned.pt best.pt
#   # Criar inference.py (ver documentação)
#   tar -czvf model.tar.gz best.pt code/
#   aws s3 cp model.tar.gz s3://surgical-detection-models-dev/trained/
#
# -----------------------------------------------------------------------------
resource "aws_sagemaker_model" "yolo" {
  name               = "${var.project_name}-model-${var.environment}"
  execution_role_arn = aws_iam_role.sagemaker.arn

  primary_container {
    image          = "763104351884.dkr.ecr.${data.aws_region.current.name}.amazonaws.com/pytorch-inference:2.0.1-gpu-py310-cu118-ubuntu20.04-sagemaker"
    model_data_url = "s3://${var.models_bucket_name}/trained/model.tar.gz"
    environment = {
      SAGEMAKER_PROGRAM             = "inference.py"
      SAGEMAKER_SUBMIT_DIRECTORY    = "s3://${var.models_bucket_name}/trained/model.tar.gz"
      SAGEMAKER_CONTAINER_LOG_LEVEL = "20"
      # Configurações do modelo
      MODEL_VERSION                 = var.model_version
      CONFIDENCE_THRESHOLD          = tostring(var.confidence_threshold)
    }
  }

  tags = {
    Name          = "${var.project_name}-model"
    Environment   = var.environment
    ModelVersion  = var.model_version
  }
}

# -----------------------------------------------------------------------------
# SageMaker Endpoint Configuration
# -----------------------------------------------------------------------------
resource "aws_sagemaker_endpoint_configuration" "yolo" {
  name = "${var.project_name}-config-${var.environment}"

  production_variants {
    variant_name           = "primary"
    model_name             = aws_sagemaker_model.yolo.name
    initial_instance_count = 1
    instance_type          = var.instance_type
  }

  tags = {
    Name        = "${var.project_name}-config"
    Environment = var.environment
  }
}

# -----------------------------------------------------------------------------
# SageMaker Endpoint
# -----------------------------------------------------------------------------
resource "aws_sagemaker_endpoint" "yolo" {
  name                 = "${var.project_name}-endpoint-${var.environment}"
  endpoint_config_name = aws_sagemaker_endpoint_configuration.yolo.name

  tags = {
    Name        = "${var.project_name}-endpoint"
    Environment = var.environment
  }
}

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------
output "endpoint_name" {
  value = aws_sagemaker_endpoint.yolo.name
}

output "endpoint_arn" {
  value = aws_sagemaker_endpoint.yolo.arn
}

output "model_name" {
  value = aws_sagemaker_model.yolo.name
}

output "model_version" {
  value       = var.model_version
  description = "Versão do modelo em uso"
}

output "confidence_threshold" {
  value       = var.confidence_threshold
  description = "Threshold de confiança configurado"
}
