"""
Visualization module.
Renders summary table, emotion-over-time chart,
and frame previews with bounding boxes.
"""

import cv2
import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image

from analysis.summarizer import summarize_emotions
from utils.export import prepare_export_data


# ── Color map for bounding boxes ────────────────────
EMOTION_COLORS = {
    "angry":    (255, 0, 0),
    "disgust":  (0, 128, 0),
    "fear":     (128, 0, 128),
    "happy":    (0, 200, 0),
    "sad":      (0, 0, 255),
    "surprise": (255, 165, 0),
    "neutral":  (180, 180, 180),
    "error":    (100, 100, 100),
}


def show_summary_table(results: list[dict]) -> None:
    """Displays a summary DataFrame of all detections."""
    rows = [
        {
            "Frame": r["frame"],
            "Time (s)": r["timestamp_s"],
            "Face #": r["face"],
            "Dominant Emotion": r["dominant_emotion"],
            "Confidence (%)": r["confidence"],
        }
        for r in results
    ]
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)


def show_emotion_chart(results: list[dict]) -> None:
    """Plots emotion confidence over time as a line chart."""
    # Build a DataFrame with one column per emotion
    records = []
    for r in results:
        if not r["all_emotions"] or isinstance(r["all_emotions"], str):
            continue
        row = {"timestamp_s": r["timestamp_s"], "face": r["face"]}
        row.update(r["all_emotions"])
        records.append(row)

    if not records:
        st.info("Not enough data for chart.")
        return

    df = pd.DataFrame(records)

    # If multiple faces, let user pick one
    faces = sorted(df["face"].dropna().unique())
    if len(faces) > 1:
        selected_face = st.selectbox(
            "Select face for chart:", faces, index=0
        )
        df = df[df["face"] == selected_face]

    emotion_cols = [
        "angry", "disgust", "fear", "happy", "sad", "surprise", "neutral"
    ]
    available = [c for c in emotion_cols if c in df.columns]

    chart_df = df.set_index("timestamp_s")[available]
    st.line_chart(chart_df, use_container_width=True)


def show_frame_previews(results: list[dict], max_previews: int = 20) -> None:
    """
    Shows sampled frames with bounding boxes drawn around detected faces.
    """
    # Deduplicate by frame index — draw all faces on same image
    frames_map: dict[int, dict] = {}
    for r in results:
        fidx = r["frame"]
        if fidx not in frames_map:
            frames_map[fidx] = {
                "image": r["frame_image"].copy(),
                "faces": [],
            }
        frames_map[fidx]["faces"].append(r)

    frame_keys = sorted(frames_map.keys())[:max_previews]

    if not frame_keys:
        return

    st.subheader("🖼️ Frame Previews")
    cols_per_row = 4

    for row_start in range(0, len(frame_keys), cols_per_row):
        cols = st.columns(cols_per_row)
        for col_idx, col in enumerate(cols):
            key_idx = row_start + col_idx
            if key_idx >= len(frame_keys):
                break

            fidx = frame_keys[key_idx]
            entry = frames_map[fidx]
            annotated = _draw_bboxes(entry["image"], entry["faces"])
            img = Image.fromarray(annotated)

            with col:
                st.image(img, caption=f"Frame {fidx}", use_container_width=True)


def _draw_bboxes(image: np.ndarray, faces: list[dict]) -> np.ndarray:
    """Draws bounding boxes and emotion labels on an RGB image."""
    img = image.copy()
    for f in faces:
        bbox = f.get("bbox")
        if not bbox or bbox["w"] == 0:
            continue

        emotion = f["dominant_emotion"]
        color = EMOTION_COLORS.get(emotion, (255, 255, 255))
        x, y, w, h = bbox["x"], bbox["y"], bbox["w"], bbox["h"]

        cv2.rectangle(img, (x, y), (x + w, y + h), color, 2)

        label = f'{emotion} {f["confidence"]:.0f}%'
        font_scale = 0.5
        thickness = 1
        (tw, th), _ = cv2.getTextSize(
            label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness
        )
        cv2.rectangle(img, (x, y - th - 8), (x + tw + 4, y), color, -1)
        cv2.putText(
            img, label, (x + 2, y - 4),
            cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), thickness,
        )

    return img


def show_voice_analysis(voice_result: dict) -> None:
    """
    Displays the voice/audio emotion analysis results in the Streamlit app.

    Args:
        voice_result: Dict from audio.voice_analyzer.analyze_voice_emotions().
    """
    st.subheader("🎙️ Voice Emotion Analysis")

    if voice_result.get("source") == "none":
        st.info("No speech was detected in the audio track.")
        return

    # Top-level metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        sentiment = voice_result.get("sentiment", "unknown")
        emoji = {"positive": "😊", "neutral": "😐", "negative": "😟"}.get(sentiment, "❓")
        st.metric("Sentiment", f"{emoji} {sentiment.capitalize()}")
    with col2:
        risk = voice_result.get("risk_level", "unknown")
        risk_color = {"low": "🟢", "moderate": "🟡", "high": "🔴"}.get(risk, "⚪")
        st.metric("Risk Level", f"{risk_color} {risk.capitalize()}")
    with col3:
        st.metric("Score", f"{voice_result.get('score', 0)} / 10")
    with col4:
        source = voice_result.get("source", "unknown")
        st.metric("Source", source.replace("_", " ").title())

    # Summary
    if summary := voice_result.get("summary"):
        st.markdown(f"**Summary:** {summary}")

    # Detected signals
    signals = voice_result.get("detected_signals", [])
    if signals:
        st.markdown("**Detected Signals:**")
        signal_tags = " ".join(f"`{s}`" for s in signals)
        st.markdown(signal_tags)

    # Keywords
    keywords = voice_result.get("keywords", [])
    if keywords:
        st.markdown("**Keywords:**")
        kw_tags = " ".join(f"`{k}`" for k in keywords)
        st.markdown(kw_tags)

    # Justification & recommended action
    with st.expander("📝 Details"):
        if justification := voice_result.get("justification"):
            st.markdown(f"**Justification:** {justification}")
        if action := voice_result.get("recommended_action"):
            st.markdown(f"**Recommended Action:** {action}")
        if llm_error := voice_result.get("llm_error"):
            st.warning(f"LLM fallback used: {llm_error}")

    # Transcription
    if transcription := voice_result.get("transcription"):
        with st.expander("📜 Full Transcription"):
            st.text(transcription)


def show_llm_summary(results: list[dict] | None = None,
                     voice_result: dict | None = None) -> None:
    """
    Sends the analyzer JSON payload to the LLM and displays
    the natural-language emotion summary in the Streamlit app.
    Optionally includes voice analysis data for a multimodal summary.
    """
    st.subheader("🧠 AI Emotion Summary")

    if not results and not voice_result:
        st.info("No data available for summarisation.")
        return

    export_data = prepare_export_data(results) if results else None

    with st.spinner("Generating AI summary…"):
        summary = summarize_emotions(export_data, voice_result=voice_result)

    if summary:
        st.info(summary)
    else:
        st.warning("Could not generate an AI summary. Check your API key.")
