#!/bin/sh
# =============================================================================
# Sentinel Surgical — container entrypoint
#
# Ensures the YOLOv8 model (best.pt) is present at MODEL_PATH before launching
# the FastAPI server. If missing, downloads it from Hugging Face Hub.
#
# Env vars (with defaults):
#   MODEL_PATH    — where the model file should live inside the container
#                   (default: /app/models/best.pt)
#   HF_MODEL_URL  — full URL to the .pt on Hugging Face Hub
#                   (default: zagari/sentinel-surgical-yolov8m-bleeding · main)
#
# The downloaded file persists if /app/models is mounted from the host as a
# read-write volume — subsequent restarts skip the download.
# =============================================================================
set -e

MODEL_PATH="${MODEL_PATH:-/app/models/best.pt}"
HF_MODEL_URL="${HF_MODEL_URL:-https://huggingface.co/zagari/sentinel-surgical-yolov8m-bleeding/resolve/main/best.pt}"

if [ ! -s "$MODEL_PATH" ]; then
    echo "[entrypoint] Model not found at $MODEL_PATH — fetching from Hugging Face..."
    echo "[entrypoint]   URL: $HF_MODEL_URL"
    mkdir -p "$(dirname "$MODEL_PATH")"

    # -fL: fail on HTTP errors, follow redirects (HF returns 302 to its CDN)
    # --retry: be resilient to transient network blips
    if curl -fL --retry 3 --retry-delay 2 -o "$MODEL_PATH" "$HF_MODEL_URL"; then
        echo "[entrypoint] Model downloaded ($(du -h "$MODEL_PATH" | cut -f1))"
    else
        echo "[entrypoint] WARNING: failed to download model from HF. The /health"
        echo "[entrypoint] endpoint will still work, but inference calls will fail"
        echo "[entrypoint] with a missing-file error on the first request."
        # Don't exit non-zero — we still want the container to come up so the
        # operator can introspect it and provide the model another way.
    fi
else
    echo "[entrypoint] Model already present at $MODEL_PATH ($(du -h "$MODEL_PATH" | cut -f1))"
fi

# Hand control to the original CMD
exec "$@"
