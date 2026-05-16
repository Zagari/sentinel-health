# =============================================================================
# Inference Environment - Terraform Configuration
# =============================================================================
# Custo estimado: ~$0.53/hora (SageMaker ml.g4dn.xlarge)
# Para desligar: ./scripts/infra-down-inference.sh
#
# Modelo de produção: v3_finetuned
# - Detecção: 91.72%
# - Falso Positivo: 13.44%
# - Threshold: 0.30
# =============================================================================

terraform {
  required_version = ">= 1.0.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "surgical-video-ai"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# -----------------------------------------------------------------------------
# Variables
# -----------------------------------------------------------------------------
variable "aws_region" {
  description = "Região AWS"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Ambiente"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Nome do projeto"
  type        = string
  default     = "surgical-detection"
}

variable "models_bucket" {
  description = "Nome do bucket de modelos (criado pelo ambiente de training)"
  type        = string
  default     = "surgical-detection-models-dev"
}

variable "model_version" {
  description = "Versão do modelo a usar (v1_baseline, v2_classweight, v3_finetuned)"
  type        = string
  default     = "v3_finetuned"
}

variable "confidence_threshold" {
  description = "Threshold de confiança para detecções (0.0-1.0)"
  type        = number
  default     = 0.30
}

# -----------------------------------------------------------------------------
# Inference Module (SageMaker Endpoint)
# -----------------------------------------------------------------------------
module "inference" {
  source = "../../modules/inference"

  project_name         = var.project_name
  environment          = var.environment
  models_bucket_name   = var.models_bucket
  model_version        = var.model_version
  confidence_threshold = var.confidence_threshold
}

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------
output "endpoint_name" {
  description = "Nome do endpoint SageMaker"
  value       = module.inference.endpoint_name
}

output "endpoint_arn" {
  description = "ARN do endpoint SageMaker"
  value       = module.inference.endpoint_arn
}

output "model_name" {
  description = "Nome do modelo SageMaker"
  value       = module.inference.model_name
}

output "model_version" {
  description = "Versão do modelo em uso"
  value       = module.inference.model_version
}

output "confidence_threshold" {
  description = "Threshold de confiança configurado"
  value       = module.inference.confidence_threshold
}

output "invoke_example" {
  description = "Exemplo de invocação do endpoint"
  value       = <<-EOT
    import boto3
    import json

    runtime = boto3.client('sagemaker-runtime')
    response = runtime.invoke_endpoint(
        EndpointName='${module.inference.endpoint_name}',
        ContentType='application/json',
        Body=json.dumps({'image': '<base64_encoded_image>'})
    )
  EOT
}
