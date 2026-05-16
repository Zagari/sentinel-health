# =============================================================================
# Storage Module - S3 Buckets para Datasets e Modelos
# =============================================================================
#
# Estrutura dos Buckets:
#
# surgical-detection-datasets-dev/
# ├── yolo_format/              # Dataset CholecSeg8k em formato YOLO
# │   ├── train/
# │   ├── val/
# │   └── data.yaml
# └── annotations_v3/           # Anotações do GynSurg para fine-tuning
#
# surgical-detection-models-dev/
# └── trained/
#     ├── best.pt               # Modelo de produção (v3_finetuned)
#     ├── best_v1_baseline.pt   # Baseline: 5.41% det, 76.11% FP
#     ├── best_v2_classweight.pt # Class weights: 12.14% det, 46.89% FP
#     ├── best_v3_finetuned.pt  # Fine-tuned: 91.72% det, 13.44% FP ✅
#     └── model.tar.gz          # Pacote para SageMaker
#
# surgical-detection-results-dev/
# └── validation_gynsurg_*/     # Resultados de validação
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

# -----------------------------------------------------------------------------
# S3 Bucket - Datasets
# -----------------------------------------------------------------------------
resource "aws_s3_bucket" "datasets" {
  bucket = "${var.project_name}-datasets-${var.environment}"

  tags = {
    Name        = "${var.project_name}-datasets"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_s3_bucket_versioning" "datasets" {
  bucket = aws_s3_bucket.datasets.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "datasets" {
  bucket = aws_s3_bucket.datasets.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# -----------------------------------------------------------------------------
# S3 Bucket - Models
# -----------------------------------------------------------------------------
resource "aws_s3_bucket" "models" {
  bucket = "${var.project_name}-models-${var.environment}"

  tags = {
    Name        = "${var.project_name}-models"
    Environment = var.environment
    Project     = var.project_name
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

# -----------------------------------------------------------------------------
# S3 Bucket - Results
# -----------------------------------------------------------------------------
resource "aws_s3_bucket" "results" {
  bucket = "${var.project_name}-results-${var.environment}"

  tags = {
    Name        = "${var.project_name}-results"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "results" {
  bucket = aws_s3_bucket.results.id

  rule {
    id     = "expire-old-results"
    status = "Enabled"

    expiration {
      days = 90
    }
  }
}

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------
output "datasets_bucket_name" {
  value = aws_s3_bucket.datasets.id
}

output "datasets_bucket_arn" {
  value = aws_s3_bucket.datasets.arn
}

output "models_bucket_name" {
  value = aws_s3_bucket.models.id
}

output "models_bucket_arn" {
  value = aws_s3_bucket.models.arn
}

output "results_bucket_name" {
  value = aws_s3_bucket.results.id
}

output "results_bucket_arn" {
  value = aws_s3_bucket.results.arn
}
