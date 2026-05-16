# =============================================================================
# Storage Module — S3 Buckets para Sentinel Health
# =============================================================================
#
# Estrutura dos buckets:
#
# sentinel-health-assets-{env}/
# └── landing-assets/              # logos, screenshots para a landing institucional
#
# sentinel-health-models-{env}/
# ├── best.pt                      # modelo YOLOv8m do Surgical (v3_finetuned)
# └── best_v3_finetuned.pt         # backup com tag explícita
#
# Não há bucket de "datasets" nem de "results": esta plataforma não treina
# nem armazena outputs em massa (uploads/results ficam em volumes locais do
# EC2 com retention pequeno).
# =============================================================================

variable "project_name" {
  description = "Nome do projeto"
  type        = string
  default     = "sentinel-health"
}

variable "environment" {
  description = "Ambiente (demo, staging, prod)"
  type        = string
  default     = "demo"
}

# -----------------------------------------------------------------------------
# S3 Bucket — Static Assets (logos, screenshots da landing)
# -----------------------------------------------------------------------------
resource "aws_s3_bucket" "assets" {
  bucket = "${var.project_name}-assets-${var.environment}"

  # Demo environment: allow `terraform destroy` to wipe objects/versions
  # automatically. Set this to false for staging/prod where data loss
  # would be costly.
  force_destroy = true

  tags = {
    Name        = "${var.project_name}-assets"
    Environment = var.environment
    Project     = var.project_name
    Purpose     = "landing-static-assets"
  }
}

resource "aws_s3_bucket_versioning" "assets" {
  bucket = aws_s3_bucket.assets.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "assets" {
  bucket = aws_s3_bucket.assets.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Block public access by default. The landing reads via EC2's IAM role.
# If we ever serve static directly from S3 + CloudFront, this can be relaxed.
resource "aws_s3_bucket_public_access_block" "assets" {
  bucket                  = aws_s3_bucket.assets.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# -----------------------------------------------------------------------------
# S3 Bucket — Trained Models (best.pt do Surgical)
# -----------------------------------------------------------------------------
resource "aws_s3_bucket" "models" {
  bucket = "${var.project_name}-models-${var.environment}"

  # Demo environment: allow `terraform destroy` to wipe objects/versions
  # automatically. Set this to false for staging/prod where data loss
  # would be costly.
  force_destroy = true

  tags = {
    Name        = "${var.project_name}-models"
    Environment = var.environment
    Project     = var.project_name
    Purpose     = "trained-yolov8-models"
  }
}

resource "aws_s3_bucket_versioning" "models" {
  bucket = aws_s3_bucket.models.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "models" {
  bucket = aws_s3_bucket.models.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "models" {
  bucket                  = aws_s3_bucket.models.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------
output "assets_bucket_name" {
  description = "Nome do bucket de assets"
  value       = aws_s3_bucket.assets.id
}

output "assets_bucket_arn" {
  description = "ARN do bucket de assets"
  value       = aws_s3_bucket.assets.arn
}

output "models_bucket_name" {
  description = "Nome do bucket de modelos"
  value       = aws_s3_bucket.models.id
}

output "models_bucket_arn" {
  description = "ARN do bucket de modelos"
  value       = aws_s3_bucket.models.arn
}
