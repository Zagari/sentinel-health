# =============================================================================
# Runtime Module — EC2 instance hosting the Sentinel Health docker stack
# =============================================================================
#
# Roda a mesma topologia do deploy local (nginx + landing + surgical + insight)
# num único EC2 t3.medium. Acesso ao host via SSM Session Manager (sem SSH
# público). OPENAI_API_KEY vem do SSM Parameter Store.
#
# Pattern: provisiona → demo → destrói, mesmo padrão do surgical-video-ai
# para minimizar custos.
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

variable "instance_type" {
  description = "Tipo de instância EC2 (t3.medium: 2 vCPU, 4 GB RAM, ~$0.04/h)"
  type        = string
  default     = "t3.medium"
}

variable "repo_url" {
  description = "URL pública do repositório Git a clonar no boot"
  type        = string
  default     = "https://github.com/Zagari/sentinel-health.git"
}

variable "repo_branch" {
  description = "Branch a clonar"
  type        = string
  default     = "main"
}

variable "models_bucket_name" {
  description = "Nome do bucket de modelos (sem 'arn:aws:s3:::')"
  type        = string
}

variable "models_bucket_arn" {
  description = "ARN do bucket de modelos"
  type        = string
}

variable "assets_bucket_arn" {
  description = "ARN do bucket de assets"
  type        = string
}

variable "openai_api_key_ssm_param" {
  description = "Nome do parâmetro SSM (SecureString) com a OPENAI_API_KEY"
  type        = string
  default     = "/sentinel-health/demo/openai-api-key"
}

variable "root_volume_size_gb" {
  description = "Tamanho do volume root (GB). 30GB ≤ free tier por 12 meses."
  type        = number
  default     = 30
}

# -----------------------------------------------------------------------------
# Data Sources
# -----------------------------------------------------------------------------
data "aws_region" "current" {}

# Amazon Linux 2023 — leve, free-tier compatible base, com dnf
data "aws_ami" "al2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-x86_64"]
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
# Security Group — apenas 80 e 443 (HTTPS para futuro), sem SSH
# Acesso administrativo via SSM Session Manager (não precisa de porta aberta)
# -----------------------------------------------------------------------------
resource "aws_security_group" "runtime" {
  name        = "${var.project_name}-runtime-sg-${var.environment}"
  description = "Sentinel Health runtime: HTTP/HTTPS in, all out. SSH via SSM only."

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTP (nginx)"
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS (futuro, se TLS for adicionado)"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound (Docker pulls, S3, OpenAI API)"
  }

  tags = {
    Name        = "${var.project_name}-runtime-sg"
    Environment = var.environment
    Project     = var.project_name
  }
}

# -----------------------------------------------------------------------------
# IAM Role + Instance Profile
#  - AmazonSSMManagedInstanceCore: habilita Session Manager
#  - Policy custom: leitura nos 2 S3 buckets + leitura do parâmetro SSM
# -----------------------------------------------------------------------------
resource "aws_iam_role" "runtime" {
  name = "${var.project_name}-runtime-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = "sts:AssumeRole"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
    }]
  })

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

# SSM Session Manager + CloudWatch Logs default
resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.runtime.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# S3 read access para baixar best.pt e (futuramente) assets da landing
resource "aws_iam_role_policy" "s3_read" {
  name = "${var.project_name}-runtime-s3-read-${var.environment}"
  role = aws_iam_role.runtime.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "s3:GetObject",
        "s3:ListBucket"
      ]
      Resource = [
        var.models_bucket_arn,
        "${var.models_bucket_arn}/*",
        var.assets_bucket_arn,
        "${var.assets_bucket_arn}/*"
      ]
    }]
  })
}

# Permissão para ler o parâmetro SSM com a OPENAI_API_KEY
resource "aws_iam_role_policy" "ssm_param_read" {
  name = "${var.project_name}-runtime-ssm-param-${var.environment}"
  role = aws_iam_role.runtime.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "ssm:GetParameter",
        "ssm:GetParameters"
      ]
      Resource = "arn:aws:ssm:*:*:parameter${var.openai_api_key_ssm_param}"
    }]
  })
}

resource "aws_iam_instance_profile" "runtime" {
  name = "${var.project_name}-runtime-profile-${var.environment}"
  role = aws_iam_role.runtime.name
}

# -----------------------------------------------------------------------------
# EC2 Instance
# -----------------------------------------------------------------------------
resource "aws_instance" "runtime" {
  ami                    = data.aws_ami.al2023.id
  instance_type          = var.instance_type
  vpc_security_group_ids = [aws_security_group.runtime.id]
  iam_instance_profile   = aws_iam_instance_profile.runtime.name

  root_block_device {
    volume_size           = var.root_volume_size_gb
    volume_type           = "gp3"
    delete_on_termination = true
  }

  user_data = <<-EOF
    #!/bin/bash
    set -e
    exec > >(tee -a /var/log/sentinel-bootstrap.log) 2>&1
    echo "=== Sentinel Health bootstrap starting at $(date -u) ==="

    # ── Instalar Docker (Amazon Linux 2023 usa dnf) ──────────────────────
    dnf update -y
    dnf install -y docker git

    systemctl enable docker
    systemctl start docker
    usermod -a -G docker ec2-user

    # ── Instalar Docker Compose v2 plugin ────────────────────────────────
    DOCKER_COMPOSE_VERSION="v2.30.0"
    mkdir -p /usr/local/lib/docker/cli-plugins
    curl -SL "https://github.com/docker/compose/releases/download/$${DOCKER_COMPOSE_VERSION}/docker-compose-linux-x86_64" \
      -o /usr/local/lib/docker/cli-plugins/docker-compose
    chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

    # ── Instalar AWS CLI v2 (Amazon Linux 2023 já vem com aws cli) ───────
    aws --version || (curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o /tmp/awscliv2.zip && \
                       cd /tmp && unzip -q awscliv2.zip && ./aws/install)

    # ── Clonar repositório ───────────────────────────────────────────────
    cd /home/ec2-user
    sudo -u ec2-user git clone -b ${var.repo_branch} ${var.repo_url} sentinel-health

    # ── Configurar .env do Insight com a OPENAI_API_KEY do SSM ───────────
    REGION="${data.aws_region.current.name}"
    OPENAI_KEY=$(aws ssm get-parameter \
      --name "${var.openai_api_key_ssm_param}" \
      --with-decryption \
      --query "Parameter.Value" \
      --output text \
      --region "$${REGION}" 2>/dev/null || echo "")

    if [ -z "$${OPENAI_KEY}" ]; then
      echo "WARNING: SSM parameter ${var.openai_api_key_ssm_param} not found." \
           "Set it before re-running compose: aws ssm put-parameter --name ${var.openai_api_key_ssm_param} --type SecureString --value <key>"
      OPENAI_KEY="REPLACE_ME"
    fi

    INSIGHT_ENV=/home/ec2-user/sentinel-health/modules/insight/emotion-recognizer/.env
    echo "OPENAI_API_KEY=$${OPENAI_KEY}" > "$${INSIGHT_ENV}"
    chown ec2-user:ec2-user "$${INSIGHT_ENV}"
    chmod 600 "$${INSIGHT_ENV}"

    # ── Baixar best.pt do S3 (se existir no bucket) ──────────────────────
    aws s3 cp "s3://${var.models_bucket_name}/best.pt" \
              "/home/ec2-user/sentinel-health/modules/surgical/web/models/best.pt" \
              --region "$${REGION}" 2>/dev/null && \
      echo "best.pt baixado do S3" || \
      echo "best.pt não encontrado em S3 — endpoints de detecção do Surgical falharão até o modelo ser carregado"

    chown -R ec2-user:ec2-user /home/ec2-user/sentinel-health

    # ── Subir a stack via docker compose ─────────────────────────────────
    cd /home/ec2-user/sentinel-health/deploy
    sudo -u ec2-user docker compose up -d

    echo "=== Sentinel Health bootstrap concluído at $(date -u) ==="
    echo "URL pública: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)/"
  EOF

  tags = {
    Name        = "${var.project_name}-runtime-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
  }
}

# -----------------------------------------------------------------------------
# Elastic IP — endereço estável (free quando associado a instância em execução)
# -----------------------------------------------------------------------------
resource "aws_eip" "runtime" {
  instance = aws_instance.runtime.id
  domain   = "vpc"

  tags = {
    Name        = "${var.project_name}-runtime-eip"
    Environment = var.environment
    Project     = var.project_name
  }
}

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------
output "instance_id" {
  description = "ID da instância EC2"
  value       = aws_instance.runtime.id
}

output "public_ip" {
  description = "IP público (Elastic IP)"
  value       = aws_eip.runtime.public_ip
}

output "public_url" {
  description = "URL da landing institucional"
  value       = "http://${aws_eip.runtime.public_ip}/"
}

output "surgical_url" {
  description = "URL do Sentinel Surgical"
  value       = "http://${aws_eip.runtime.public_ip}/surgical/"
}

output "insight_url" {
  description = "URL do Sentinel Insight"
  value       = "http://${aws_eip.runtime.public_ip}/insight/"
}

output "ssm_session_command" {
  description = "Comando para abrir sessão SSM (acesso ao shell sem SSH)"
  value       = "aws ssm start-session --target ${aws_instance.runtime.id} --region ${data.aws_region.current.name}"
}

output "bootstrap_log_command" {
  description = "Comando para ver o log de bootstrap via SSM"
  value       = "aws ssm send-command --instance-ids ${aws_instance.runtime.id} --document-name AWS-RunShellScript --parameters 'commands=[\"tail -n 200 /var/log/sentinel-bootstrap.log\"]' --region ${data.aws_region.current.name}"
}
