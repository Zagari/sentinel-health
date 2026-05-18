# =============================================================================
# Sentinel Health — Demo Environment
# =============================================================================
# Custo estimado: ~$0.04/h (EC2 t3.medium + EBS 30GB + EIP gratuito enquanto
#                          associado).
#
# Artefatos externos consumidos em runtime:
#   - best.pt: baixado do Hugging Face Hub no boot do container Surgical
#     (ver modules/surgical/web/entrypoint.sh).
#   - Clips GynSurg: lidos do bucket S3 `surgical-detection-datasets-dev`
#     (projeto surgical-video-ai), via IAM read-only cross-bucket.
#
# Workflow:
#   1. (Uma vez) Setar OPENAI_API_KEY no SSM Parameter Store:
#        aws ssm put-parameter \
#          --name /sentinel-health/demo/openai-api-key \
#          --type SecureString \
#          --value sk-...
#   2. terraform apply
#   3. Se o SSM param foi setado depois do apply, reinicie o compose no EC2:
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
# Runtime Module — EC2 + IAM + SG + EIP
# -----------------------------------------------------------------------------
module "runtime" {
  source = "../../modules/runtime"

  project_name  = var.project_name
  environment   = var.environment
  instance_type = var.instance_type
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

output "bootstrap_log_command" {
  description = "Comando para inspecionar o log de bootstrap"
  value       = module.runtime.bootstrap_log_command
}
