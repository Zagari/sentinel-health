# =============================================================================
# Training Module - EC2 Instance com GPU para Treinamento YOLOv8
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
  description = "Tipo da instância EC2"
  type        = string
  default     = "t3.xlarge"  # Temporário para teste - trocar por g4dn.xlarge depois
}

variable "key_name" {
  description = "Nome da key pair SSH"
  type        = string
}

variable "datasets_bucket_arn" {
  description = "ARN do bucket de datasets"
  type        = string
}

variable "models_bucket_arn" {
  description = "ARN do bucket de modelos"
  type        = string
}

variable "results_bucket_arn" {
  description = "ARN do bucket de resultados"
  type        = string
}

# -----------------------------------------------------------------------------
# Data Sources
# -----------------------------------------------------------------------------
data "aws_region" "current" {}

data "aws_ami" "deep_learning" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["Deep Learning OSS Nvidia Driver AMI GPU PyTorch*Ubuntu*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }
}

# -----------------------------------------------------------------------------
# Security Group
# -----------------------------------------------------------------------------
resource "aws_security_group" "training" {
  name        = "${var.project_name}-training-sg-${var.environment}"
  description = "Security group for training instance"

  # SSH
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "SSH access"
  }

  # Saída total
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound"
  }

  tags = {
    Name        = "${var.project_name}-training-sg"
    Environment = var.environment
  }
}

# -----------------------------------------------------------------------------
# IAM Role para EC2
# -----------------------------------------------------------------------------
resource "aws_iam_role" "training" {
  name = "${var.project_name}-training-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "training_s3" {
  name = "${var.project_name}-training-s3-policy"
  role = aws_iam_role.training.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket",
          "s3:DeleteObject"
        ]
        Resource = [
          var.datasets_bucket_arn,
          "${var.datasets_bucket_arn}/*",
          var.models_bucket_arn,
          "${var.models_bucket_arn}/*",
          var.results_bucket_arn,
          "${var.results_bucket_arn}/*"
        ]
      }
    ]
  })
}

resource "aws_iam_instance_profile" "training" {
  name = "${var.project_name}-training-profile-${var.environment}"
  role = aws_iam_role.training.name
}

# -----------------------------------------------------------------------------
# EC2 Instance
# -----------------------------------------------------------------------------
resource "aws_instance" "training" {
  ami                    = data.aws_ami.deep_learning.id
  instance_type          = var.instance_type
  key_name               = var.key_name
  vpc_security_group_ids = [aws_security_group.training.id]
  iam_instance_profile   = aws_iam_instance_profile.training.name

  root_block_device {
    volume_size = 200
    volume_type = "gp3"
  }

  user_data = <<-EOF
    #!/bin/bash
    set -e

    # ==========================================================================
    # User Data - Setup inicial da instância de treinamento
    # Os scripts de treinamento são baixados do repositório para manter
    # consistência e facilitar atualizações.
    # ==========================================================================

    WORK_DIR="/home/ubuntu/surgical-training"
    REPO_URL="https://github.com/Zagari/surgical-video-ai.git"

    # Criar diretório de trabalho
    mkdir -p $WORK_DIR
    cd /home/ubuntu

    # Clonar repositório com scripts atualizados
    echo "Clonando repositório..."
    git clone $REPO_URL surgical-video-ai || true

    # Copiar scripts para diretório de trabalho
    cp -r surgical-video-ai/scripts $WORK_DIR/

    # Dar permissão de execução
    chmod +x $WORK_DIR/scripts/*.sh

    # Criar ambiente virtual Python
    echo "Criando ambiente virtual..."
    python3 -m venv /home/ubuntu/surgical-venv
    source /home/ubuntu/surgical-venv/bin/activate
    pip install --upgrade pip
    pip install ultralytics boto3 opencv-python

    # Ajustar permissões
    chown -R ubuntu:ubuntu /home/ubuntu/surgical-training
    chown -R ubuntu:ubuntu /home/ubuntu/surgical-venv
    chown -R ubuntu:ubuntu /home/ubuntu/surgical-video-ai

    # Criar script de conveniência
    cat > /home/ubuntu/train.sh << 'CONVENIENCE_SCRIPT'
    #!/bin/bash
    # Script de conveniência para treinamento
    #
    # Modelos disponíveis:
    #   v1 (baseline):     ./scripts/server-train.sh
    #   v2 (class weights): ./scripts/server-train-v2-classweight.sh
    #   v3 (fine-tuning):  ./scripts/finetune-gynsurg.sh
    #
    # Modelo de produção atual: v3_finetuned (91.72% det, 13.44% FP)

    source /home/ubuntu/surgical-venv/bin/activate
    cd /home/ubuntu/surgical-training

    echo "=========================================="
    echo "  SURGICAL VIDEO AI - TREINAMENTO"
    echo "=========================================="
    echo ""
    echo "Scripts disponíveis:"
    echo "  1. ./scripts/server-train.sh           - v1 baseline"
    echo "  2. ./scripts/server-train-v2-classweight.sh - v2 com class weights"
    echo "  3. ./scripts/finetune-gynsurg.sh       - v3 fine-tuning"
    echo ""
    echo "Para validação:"
    echo "  ./scripts/validate-gynsurg.sh <path_gynsurg> --fixed --version <tag>"
    echo ""
    CONVENIENCE_SCRIPT

    chmod +x /home/ubuntu/train.sh
    chown ubuntu:ubuntu /home/ubuntu/train.sh

    echo ""
    echo "=========================================="
    echo "  SETUP CONCLUÍDO!"
    echo "=========================================="
    echo ""
    echo "Para começar, execute:"
    echo "  ./train.sh"
    echo ""
  EOF

  tags = {
    Name        = "${var.project_name}-training-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
  }
}

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------
output "instance_id" {
  value = aws_instance.training.id
}

output "instance_public_ip" {
  value = aws_instance.training.public_ip
}

output "ssh_command" {
  value = "ssh -i ${var.key_name}.pem ubuntu@${aws_instance.training.public_ip}"
}
