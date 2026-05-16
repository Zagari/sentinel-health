# =============================================================================
# Training Environment - Terraform Configuration
# =============================================================================
# Custo estimado: ~$3.06/hora (EC2 p3.2xlarge)
# Para desligar: ./scripts/infra-down-training.sh
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

variable "key_name" {
  description = "Nome da key pair SSH (deve existir na AWS)"
  type        = string
  default     = "castellabate-key"
}

# -----------------------------------------------------------------------------
# Storage Module (S3 Buckets)
# -----------------------------------------------------------------------------
module "storage" {
  source = "../../modules/storage"

  project_name = var.project_name
  environment  = var.environment
}

# -----------------------------------------------------------------------------
# Training Module (EC2 com GPU)
# -----------------------------------------------------------------------------
module "training" {
  source = "../../modules/training"

  project_name = var.project_name
  environment  = var.environment
  key_name     = var.key_name

  datasets_bucket_arn = module.storage.datasets_bucket_arn
  models_bucket_arn   = module.storage.models_bucket_arn
  results_bucket_arn  = module.storage.results_bucket_arn

  depends_on = [module.storage]
}

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------
output "datasets_bucket" {
  description = "Nome do bucket de datasets"
  value       = module.storage.datasets_bucket_name
}

output "models_bucket" {
  description = "Nome do bucket de modelos"
  value       = module.storage.models_bucket_name
}

output "results_bucket" {
  description = "Nome do bucket de resultados"
  value       = module.storage.results_bucket_name
}

output "training_instance_ip" {
  description = "IP público da instância de treinamento"
  value       = module.training.instance_public_ip
}

output "ssh_command" {
  description = "Comando SSH para conectar"
  value       = module.training.ssh_command
}
