"""YouTube download module — fetches video via yt-dlp."""

import os
import sys
import tempfile
import shutil
import subprocess
import streamlit as st


def _find_yt_dlp() -> str:
    """Locate the yt-dlp executable."""
    # 1. Check alongside the current Python interpreter
    scripts_dir = os.path.dirname(sys.executable)
    candidate = os.path.join(scripts_dir, "yt-dlp.exe" if sys.platform == "win32" else "yt-dlp")
    if os.path.isfile(candidate):
        return candidate
    # 2. Check the user Scripts dir (pip install --user)
    if sys.platform == "win32":
        user_candidate = os.path.join(
            os.environ.get("APPDATA", ""), "Python",
            f"Python{sys.version_info.major}{sys.version_info.minor}",
            "Scripts", "yt-dlp.exe",
        )
        if os.path.isfile(user_candidate):
            return user_candidate
    # 3. Fall back to PATH lookup
    found = shutil.which("yt-dlp")
    if found:
        return found
    raise FileNotFoundError("yt-dlp executable not found. Install it with: pip install yt-dlp")


_YT_DLP = _find_yt_dlp()


def download_youtube(url: str) -> str | None:
    """
    Downloads a YouTube video to a temporary MP4 file.

    Args:
        url: Full YouTube URL.

    Returns:
        Path to the downloaded file, or None on failure.
    """
    tmp_dir = tempfile.mkdtemp()
    output_path = os.path.join(tmp_dir, "video.mp4")

    cmd = [
        _YT_DLP,
        "-f", "worst[ext=mp4]",     # smallest quality for speed
        "--no-playlist",
        "--no-check-certificates",  # bypass SSL issues (corporate proxy)
        "--js-runtimes", "node:C:/Program Files/nodejs/node.exe",  # use Node.js JS runtime
        "-o", output_path,
        url,
    ]

    with st.spinner("⬇️ Downloading YouTube video…"):
        result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        st.error(f"yt-dlp error:\n```\n{result.stderr.strip()}\n```")
        return None

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    st.success(f"✅ Downloaded ({size_mb:.1f} MB)")
    return output_path
