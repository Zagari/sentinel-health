# Surgical Video AI - Dockerfile
# FIAP Tech Challenge - Fase 4

FROM python:3.10-slim

WORKDIR /app

# Instalar dependências do sistema
RUN apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get update --fix-missing && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Instalar yt-dlp para download de vídeos
RUN pip install --no-cache-dir yt-dlp

# Copiar requirements e instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código da aplicação
COPY app/ ./app/

# Entrypoint script — baixa best.pt do Hugging Face Hub no primeiro boot
# se o arquivo não existir em $MODEL_PATH (volume do host pode estar vazio).
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Criar diretórios necessários
RUN mkdir -p /tmp/surgical-uploads /tmp/surgical-results /app/models

# Variáveis de ambiente
ENV MODEL_PATH=/app/models/best.pt
ENV HF_MODEL_URL=https://huggingface.co/zagari/sentinel-surgical-yolov8m-bleeding/resolve/main/best.pt
ENV S3_BUCKET=surgical-detection-datasets-dev
ENV PYTHONUNBUFFERED=1

# Expor porta
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Entrypoint busca o modelo, depois cede pra CMD
ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
