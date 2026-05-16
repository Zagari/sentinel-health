"""Webcam recording module — captures video to a temporary file."""

import cv2
import tempfile
import streamlit as st


def record_webcam(duration_sec: int = 10) -> str | None:
    """
    Records from the default webcam for `duration_sec` seconds,
    displaying a live preview in the Streamlit UI.

    Returns:
        Path to the saved temporary video file, or None on failure.
    """
    tmp_file = tempfile.NamedTemporaryFile(suffix=".avi", delete=False)
    tmp_path = tmp_file.name
    tmp_file.close()

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        st.error("❌ Cannot access webcam. Check permissions and try again.")
        return None

    fps = cap.get(cv2.CAP_PROP_FPS) or 20.0
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = cv2.VideoWriter_fourcc(*"XVID")
    writer = cv2.VideoWriter(tmp_path, fourcc, fps, (width, height))

    total_frames = int(fps * duration_sec)
    progress     = st.progress(0, text="🔴 Recording from webcam…")

    # Live preview placeholder — updated every frame
    preview_col, info_col = st.columns([3, 1])
    with preview_col:
        frame_placeholder = st.empty()
    with info_col:
        elapsed_placeholder = st.empty()

    for i in range(total_frames):
        ret, frame = cap.read()
        if not ret:
            break

        writer.write(frame)

        # Update live preview (convert BGR → RGB for Streamlit)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_placeholder.image(frame_rgb, channels="RGB", use_container_width=True)

        elapsed_sec = round((i + 1) / fps, 1)
        elapsed_placeholder.metric("⏱ Elapsed", f"{elapsed_sec}s / {duration_sec}s")

        progress.progress(
            (i + 1) / total_frames,
            text=f"🔴 Recording… {elapsed_sec}s / {duration_sec}s",
        )

    cap.release()
    writer.release()
    progress.empty()
    frame_placeholder.empty()
    elapsed_placeholder.empty()
    st.success(f"✅ Recorded {duration_sec}s ({total_frames} frames)")
    return tmp_path
