"""
Core analysis module.
Samples every Nth frame, detects faces with OpenCV Haar cascades,
classifies emotion with DeepFace, and returns structured results.

Architecture (two-stage pipeline):
 1. FACE DETECTION  — OpenCV Haar cascade (haarcascade_frontalface_default).
    • Uses cv2.CascadeClassifier, no extra model files needed.
    • Reliable and lightweight face detection.
 2. EMOTION CLASSIFICATION — DeepFace.analyze on the face ROI.
    • The face ROI is converted to grayscale then back to RGB
      (matches the proven test.py approach).
    • enforce_detection=False avoids crashes on ambiguous crops.

Other design choices:
 - Sequential frame reading (reliable for AVI/webcam/all codecs).
 - frame.copy() before storing to avoid OpenCV buffer reuse.
 - Resize frames to max 960 px wide before processing.
 - Single-threaded analysis (TF model not truly thread-safe).
 - Model pre-warmed with a dummy inference before the loop.
"""

import cv2
import numpy as np
import streamlit as st
from deepface import DeepFace

# ── Constants ──────────────────────────────────────────────────────────────
_MAX_WIDTH   = 960    # max frame width before processing
_MIN_FACE_PX = 30     # ignore detections smaller than 30 × 30 px

# ── Haar cascade face detector (loaded once at module level) ──────────────
_FACE_CASCADE = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)


# ── Helpers ────────────────────────────────────────────────────────────────

def _resize_frame(frame: np.ndarray) -> np.ndarray:
    """Downscale frame to at most _MAX_WIDTH wide, preserving aspect ratio."""
    h, w = frame.shape[:2]
    if w > _MAX_WIDTH:
        scale = _MAX_WIDTH / w
        frame = cv2.resize(
            frame, (int(w * scale), int(h * scale)),
            interpolation=cv2.INTER_AREA,
        )
    return frame


def _detect_faces(frame_bgr: np.ndarray) -> list[tuple[int, int, int, int]]:
    """
    Detect faces using Haar cascade classifier.
    Returns list of (x, y, w, h) bounding boxes in pixel coordinates.
    """
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    faces = _FACE_CASCADE.detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5, minSize=(_MIN_FACE_PX, _MIN_FACE_PX)
    )
    # detectMultiScale may return an empty tuple or ndarray
    if len(faces) == 0:
        return []
    return [(int(x), int(y), int(w), int(h)) for (x, y, w, h) in faces]


def _classify_emotion(face_bgr: np.ndarray) -> dict | None:
    """
    Classify emotion on an already-cropped BGR face image.
    Converts to grayscale → RGB (same pipeline as the proven test.py)
    and runs DeepFace.analyze with enforce_detection=False.
    Returns dict with dominant_emotion, confidence, all_emotions — or None.
    """
    # Convert to grayscale then back to RGB (matches test.py logic)
    gray_face = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2GRAY)
    rgb_face = cv2.cvtColor(gray_face, cv2.COLOR_GRAY2RGB)

    try:
        results = DeepFace.analyze(
            img_path=rgb_face,
            actions=["emotion"],
            enforce_detection=False,
        )
    except Exception:
        return None

    if not results:
        return None

    face = results[0] if isinstance(results, list) else results
    dominant = face.get("dominant_emotion", "")
    emotions = face.get("emotion", {})
    if not dominant or not emotions:
        return None

    return {
        "dominant_emotion": dominant,
        "confidence":       round(emotions.get(dominant, 0.0), 2),
        "all_emotions":     {k: round(v, 2) for k, v in emotions.items()},
    }


def _prewarm_models() -> None:
    """Pre-load the DeepFace emotion model with a dummy inference."""
    dummy = np.zeros((48, 48, 3), dtype="uint8")
    try:
        DeepFace.analyze(
            img_path=dummy,
            actions=["emotion"],
            enforce_detection=False,
        )
    except Exception:
        pass


# ── Public API ─────────────────────────────────────────────────────────────

def analyze_video(video_path: str, every_n: int = 5) -> list[dict]:
    """
    Analyzes a video file for emotions.

    Pipeline per sampled frame:
      1. Haar cascade face detection → bounding boxes.
      2. Crop each face → grayscale → RGB → DeepFace emotion classification.

    Args:
        video_path: Path to the video file.
        every_n:    Analyze one frame every N frames.

    Returns:
        Chronologically sorted list of result dicts with keys:
            frame, timestamp_s, face, dominant_emotion, confidence,
            all_emotions, bbox, frame_image
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        st.error("❌ Could not open video source.")
        return []

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
    fps          = cap.get(cv2.CAP_PROP_FPS) or 25.0

    # ── Collect sampled frames (sequential read — most reliable) ─────────
    sampled: list[tuple[int, float, np.ndarray]] = []
    frame_idx = 0
    progress  = st.progress(0, text="⏩ Collecting frames…")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % every_n == 0:
            timestamp = round(frame_idx / fps, 2)
            sampled.append((frame_idx, timestamp, _resize_frame(frame.copy())))

        frame_idx += 1
        if total_frames > 0:
            progress.progress(
                min(frame_idx / total_frames, 1.0),
                text=f"⏩ Reading frame {frame_idx}/{total_frames}",
            )

    cap.release()

    if not sampled:
        st.warning("No frames could be read from the video.")
        return []

    # ── Pre-warm models ──────────────────────────────────────────────────
    progress.progress(0, text="🔥 Loading models…")
    _prewarm_models()

    # ── Analyze each sampled frame ───────────────────────────────────────
    results: list[dict] = []

    for i, (fidx, timestamp, frame_bgr) in enumerate(sampled):
        progress.progress(
            (i + 1) / len(sampled),
            text=f"🔍 Analyzing frame {i + 1}/{len(sampled)}…",
        )

        frame_rgb  = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        face_rects = _detect_faces(frame_bgr)

        for face_no, (x, y, w, h) in enumerate(face_rects):
            face_crop = frame_bgr[y:y + h, x:x + w]
            if face_crop.size == 0:
                continue

            emo = _classify_emotion(face_crop)
            if emo is None:
                continue

            results.append({
                "frame":            fidx,
                "timestamp_s":      timestamp,
                "face":             face_no,
                "dominant_emotion": emo["dominant_emotion"],
                "confidence":       emo["confidence"],
                "all_emotions":     emo["all_emotions"],
                "bbox":             {"x": x, "y": y, "w": w, "h": h},
                "frame_image":      frame_rgb,
            })

    progress.empty()

    results.sort(key=lambda r: (r["frame"], r["face"] or 0))
    return results
