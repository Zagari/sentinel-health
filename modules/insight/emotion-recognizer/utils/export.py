"""Export utilities — JSON download and clipboard copy."""

import json
import numpy as np
import streamlit as st


class _NumpyEncoder(json.JSONEncoder):
    """Handle numpy types that aren't JSON-serializable."""
    def default(self, obj):
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


def prepare_export_data(results: list[dict]) -> list[dict]:
    """
    Strips non-serializable fields (numpy images) from results
    for JSON export.
    """
    clean = []
    for r in results:
        entry = {
            "frame": r["frame"],
            "timestamp_s": r["timestamp_s"],
            "face": r["face"],
            "dominant_emotion": r["dominant_emotion"],
            "confidence": r["confidence"],
            "all_emotions": r["all_emotions"],
            "bbox": r["bbox"],
        }
        clean.append(entry)
    return clean


def show_export_controls(results: list[dict]) -> None:
    """Renders JSON viewer, download button, and clipboard copy."""
    export_data = prepare_export_data(results)
    json_str = json.dumps(export_data, indent=2, cls=_NumpyEncoder)

    col1, col2 = st.columns(2)

    with col1:
        st.download_button(
            label="⬇️ Download JSON",
            data=json_str,
            file_name="emotion_results.json",
            mime="application/json",
        )

    with col2:
        if st.button("📋 Copy to Clipboard"):
            st.code(json_str, language="json")
            st.info(
                "Select the JSON above and copy manually, "
                "or use the copy icon in the code block."
            )

    with st.expander("📋 Full Results (JSON)"):
        st.json(export_data)
