# =============================================================================
# Sentinel Health — Demo Environment
# =============================================================================
# Custo estimado: ~$0.04/h (EC2 t3.medium + EBS 30GB + EIP gratuito enquanto
#                          associado). S3 dentro do free tier (5 GB/12 meses).
#
# Workflow:
#   1. (Uma vez) Subir best.pt para S3:
#        terraform apply
#        aws s3 cp /path/to/best.pt s3://$(terraform output -raw models_bucket)/best.pt
#   2. (Uma vez) Setar OPENAI_API_KEY no SSM Parameter Store:
#        aws ssm put-parameter \
#          --name /sentinel-health/demo/openai-api-key \
#          --type SecureString \
#          --value sk-...
#   3. Após Steps 1-2, o EC2 vai pegar tudo no bootstrap. Se subiu antes do
#      best.pt/SSM, reinicie o compose dentro do EC2:
#        aws ssm start-session --target <instance-id>
#        cd ~/sentinel-health/deploy && sudo docker compose restart
#   4. Quando terminar a demonstração:
#        terraform destroy
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
      Project     = "sentinel-health"
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
  default     = "demo"
}

variable "project_name" {
  description = "Nome do projeto"
  type        = string
  default     = "sentinel-health"
}

variable "instance_type" {
  description = "Tipo de instância EC2"
  type        = string
  default     = "t3.medium"
}

# -----------------------------------------------------------------------------
# Storage Module — S3 buckets
# -----------------------------------------------------------------------------
module "storage" {
  source = "../../modules/storage"

  project_name = var.project_name
  environment  = var.environment
}

# -----------------------------------------------------------------------------
# Runtime Module — EC2 + IAM + SG + EIP
# -----------------------------------------------------------------------------
module "runtime" {
  source = "../../modules/runtime"

  project_name      = var.project_name
  environment       = var.environment
  instance_type     = var.instance_type
  models_bucket_arn = module.storage.models_bucket_arn
  models_bucket_name = module.storage.models_bucket_name
  assets_bucket_arn = module.storage.assets_bucket_arn

  depends_on = [module.storage]
}

# -----------------------------------------------------------------------------
# Outputs (consolidados)
# -----------------------------------------------------------------------------
output "public_url" {
  description = "URL pública da landing"
  value       = module.runtime.public_url
}

output "surgical_url" {
  description = "URL do Sentinel Surgical"
  value       = module.runtime.surgical_url
}

output "insight_url" {
  description = "URL do Sentinel Insight"
  value       = module.runtime.insight_url
}

output "instance_id" {
  description = "ID da instância EC2"
  value       = module.runtime.instance_id
}

output "ssm_session_command" {
  description = "Comando para acessar o shell via SSM (sem SSH)"
  value       = module.runtime.ssm_session_command
}

output "models_bucket" {
  description = "Bucket S3 para upload do best.pt"
  value       = module.storage.models_bucket_name
}

output "assets_bucket" {
  description = "Bucket S3 para assets da landing"
  value       = module.storage.assets_bucket_name
}

output "bootstrap_log_command" {
  description = "Comando para inspecionar o log de bootstrap"
  value       = module.runtime.bootstrap_log_command
}
