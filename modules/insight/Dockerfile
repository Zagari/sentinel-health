# =============================================================================
# Sentinel Insight — Multimodal Emotion Analysis (Streamlit)
# Part of Sentinel Health platform (FIAP Tech Challenge - Phase 4)
# =============================================================================

FROM python:3.12-slim

WORKDIR /app

# System deps:
# - ffmpeg: audio extraction from video
# - libgl1, libglib2.0-0, libsm6, libxext6, libxrender-dev: OpenCV runtime
# - curl: healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# yt-dlp for YouTube URL ingestion in audio-only mode
RUN pip install --no-cache-dir yt-dlp

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY emotion-recognizer/ ./emotion-recognizer/

# Streamlit runtime config
ENV PYTHONUNBUFFERED=1 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    STREAMLIT_SERVER_BASE_URL_PATH=/insight \
    STREAMLIT_SERVER_ENABLE_CORS=false \
    STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=false

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -fsS http://localhost:8501/insight/_stcore/health || exit 1

CMD ["streamlit", "run", "emotion-recognizer/app.py"]
