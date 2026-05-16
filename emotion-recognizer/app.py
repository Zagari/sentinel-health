"""
🎭 Multimodal Emotion Recognizer
Entry point — Streamlit UI wiring all modules together.
"""

import os
import tempfile
import streamlit as st

from video.recorder import record_webcam
from video.youtube import download_youtube
from analysis.analyzer import analyze_video
from analysis.visualizer import (
    show_summary_table,
    show_emotion_chart,
    show_frame_previews,
    show_voice_analysis,
    show_llm_summary,
)
from audio.extractor import extract_audio
from audio.transcriber import transcribe_audio
from audio.voice_analyzer import analyze_voice_emotions
from utils.export import show_export_controls


def main():
    # ── Page config ──────────────────────────
    st.set_page_config(
        page_title="Domestic Violence Recognizer",
        page_icon="⚠️",
        layout="wide",
    )

    st.title("⚠️ Multimodal Domestice Violence Recognizer")
    st.caption("Powered by DeepFace & Whisper — video + audio emotion detection for identifying evidence of potential domestic violence")

    # ── Sidebar settings ─────────────────────
    with st.sidebar:
        st.header("⚙️ Settings")

        analysis_mode = st.radio(
            "Analysis Mode",
            ["🎬 Video + Audio", "🎥 Video Only", "🎤 Audio Only"],
            index=0,
        )

        st.divider()

        if analysis_mode != "🎤 Audio Only":
            every_n = st.slider(
                "Analyze every N frames", min_value=1, max_value=30, value=5
            )
            max_previews = st.slider(
                "Max frame previews", min_value=4, max_value=60, value=20
            )
            st.divider()

            st.markdown(
            "**Tip:** Lower N = more detail but slower analysis."
        )       

    # ── Audio Only mode ──────────────────────
    if analysis_mode == "🎤 Audio Only":
        _run_audio_only_mode()
        return

    # ── Source selection ─────────────────────
    mode = st.radio(
        "Choose video source:",
        ["📹 Webcam", "🌐 YouTube URL"],
        horizontal=True,
    )

    video_path = None

    # ── Webcam Mode ──────────────────────────
    if mode == "📹 Webcam":
        duration = st.slider("Recording duration (seconds)", 5, 60, 10)
        if st.button("🔴 Start Recording", type="primary"):
            video_path = record_webcam(duration_sec=duration)

    # ── YouTube Mode ─────────────────────────
    else:
        url = st.text_input("Paste YouTube URL:", placeholder="https://www.youtube.com/watch?v=...")
        if st.button("⬇️ Download & Analyze", type="primary") and url:
            video_path = download_youtube(url)

    # ── Run Analysis ─────────────────────────
    if video_path:
        st.divider()
        results = analyze_video(video_path, every_n=every_n)

        # ── Voice analysis pipeline (only in Video+Audio mode) ──
        voice_result = None
        if analysis_mode == "🎬 Video + Audio":
            voice_result = _run_voice_pipeline(video_path)

        if results:
            # Summary table
            st.subheader("📊 Detection Summary")
            show_summary_table(results)

            # Emotion over time chart
            st.subheader("📈 Emotion Over Time")
            show_emotion_chart(results)

            # Frame previews with bounding boxes
            show_frame_previews(results, max_previews=max_previews)

            # Voice analysis results
            if voice_result:
                st.divider()
                show_voice_analysis(voice_result)

            # AI-generated multimodal emotion summary
            st.divider()
            show_llm_summary(results, voice_result=voice_result)

            # Export controls
            st.divider()
            st.subheader("💾 Export Results")
            show_export_controls(results)
        else:
            st.warning("No faces or emotions detected in sampled frames.")

        # Cleanup temp file
        _cleanup(video_path)


def _run_audio_only_mode():
    """Audio-only analysis: upload a file or extract from YouTube."""
    st.subheader("🎤 Audio Source")
    audio_source = st.radio(
        "Choose audio source:",
        ["Upload audio file", "Extract from YouTube video"],
        horizontal=True,
        key="audio_source_radio",
    )

    # ── Persist audio path across reruns ──────
    if "audio_only_path" not in st.session_state:
        st.session_state.audio_only_path = None
    if "audio_only_result" not in st.session_state:
        st.session_state.audio_only_result = None

    if audio_source == "Upload audio file":
        uploaded = st.file_uploader(
            "Upload an audio file",
            type=["wav", "mp3", "m4a", "mp4", "webm", "mpga", "mpeg"],
            key="audio_upload",
        )
        if uploaded is not None:
            suffix = os.path.splitext(uploaded.name)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(uploaded.read())
                st.session_state.audio_only_path = tmp.name
                st.session_state.audio_only_result = None  # reset old result

    else:  # Extract from YouTube
        url = st.text_input("YouTube URL:", key="audio_yt_url")
        if url and st.button("⬇️ Download & Extract Audio", type="primary"):
            with st.spinner("Downloading YouTube video…"):
                video_path = download_youtube(url)
            if video_path:
                with st.spinner("Extracting audio…"):
                    audio_path = extract_audio(video_path)
                _cleanup(video_path)
                if audio_path:
                    st.session_state.audio_only_path = audio_path
                    st.session_state.audio_only_result = None
                    st.success("Audio extracted — click Analyse Audio below.")

    audio_path = st.session_state.audio_only_path

    if audio_path is None:
        st.info("Upload an audio file or provide a YouTube URL to begin.")
        return

    if st.button("🎙️ Analyse Audio", key="btn_audio_only", type="primary"):
        with st.spinner("Transcribing audio (Whisper)…"):
            transcription = transcribe_audio(audio_path)

        if not transcription:
            st.error("Transcription returned empty — no speech detected.")
            st.session_state.audio_only_path = None
            _cleanup(audio_path)
            return

        with st.spinner("Analysing voice emotions…"):
            voice_result = analyze_voice_emotions(transcription)
            voice_result["transcription"] = transcription

        # Persist result so it survives reruns
        st.session_state.audio_only_result = voice_result
        # Clean up temp audio file now that we're done with it
        st.session_state.audio_only_path = None
        _cleanup(audio_path)

    # ── Display persisted results ────────────
    voice_result = st.session_state.audio_only_result
    if voice_result:
        st.divider()

        # Voice analysis results (same display as Video+Audio mode)
        show_voice_analysis(voice_result)

        # AI-generated emotion summary
        st.divider()
        show_llm_summary(results=None, voice_result=voice_result)

        # Export voice results as JSON
        st.divider()
        st.subheader("💾 Export Results")
        import json
        voice_json = json.dumps(voice_result, indent=2, default=str)
        st.download_button(
            label="📥 Download Voice Analysis (JSON)",
            data=voice_json,
            file_name="voice_analysis.json",
            mime="application/json",
        )


def _run_voice_pipeline(video_path: str) -> dict | None:
    """Extract audio, transcribe, and analyze voice emotions."""
    wav_path = None
    try:
        with st.spinner("🎵 Extracting audio from video…"):
            wav_path = extract_audio(video_path)

        if not wav_path:
            st.info("No audio track found in the video.")
            return None

        with st.spinner("🗣️ Transcribing speech…"):
            transcription = transcribe_audio(wav_path)

        if not transcription:
            st.info("No speech detected in the audio.")
            return {
                "source": "none",
                "sentiment": "neutral",
                "risk_level": "low",
                "score": 0,
                "summary": "No speech detected in the audio.",
                "keywords": [],
                "detected_signals": [],
                "justification": "Transcription was empty.",
                "recommended_action": "No action required.",
            }

        with st.spinner("🔍 Analyzing voice emotions…"):
            result = analyze_voice_emotions(transcription)
            result["transcription"] = transcription

        return result

    except Exception as e:
        st.warning(f"⚠️ Voice analysis unavailable: {e}")
        return None
    finally:
        if wav_path:
            _cleanup(wav_path)


def _cleanup(path: str) -> None:
    """Silently remove temporary video file."""
    try:
        os.remove(path)
    except OSError:
        pass


if __name__ == "__main__":
    main()
