"""
Audio extraction module — extracts audio track from a video file using ffmpeg.

Produces a WAV file (PCM 16-bit, mono, 16 kHz) suitable for Azure Speech
transcription. Adapted from the multimodal-ai-health-monitoring project.
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path


# ── ffmpeg resolution ────────────────────────────────────────────────────

_FFMPEG_BASE_ARGS: tuple[str, ...] = ("-hide_banner", "-loglevel", "error", "-y")
_FFMPEG_TARGET_ARGS: tuple[str, ...] = ("-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le")
_CONVERSION_TIMEOUT_SECONDS = 120


def _resolve_ffmpeg() -> str | None:
    """Find ffmpeg: PATH first, then imageio-ffmpeg fallback."""
    if exe := shutil.which("ffmpeg"):
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return None


# ── Public API ───────────────────────────────────────────────────────────

def extract_audio(video_path: str) -> str | None:
    """
    Extract the audio track from a video file into a temporary WAV file
    (PCM 16-bit, mono, 16 kHz).

    Args:
        video_path: Path to the video file.

    Returns:
        Path to the temporary WAV file, or None if extraction fails.
        Caller is responsible for deleting the temp file.
    """
    src = Path(video_path).expanduser().resolve()
    if not src.is_file():
        raise FileNotFoundError(f"Video file not found: {src}")

    ffmpeg = _resolve_ffmpeg()
    if not ffmpeg:
        raise RuntimeError(
            "ffmpeg not found (not on PATH, imageio-ffmpeg not installed). "
            "Install ffmpeg or: pip install imageio-ffmpeg"
        )

    # Create temp WAV
    fd, tmp_path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)

    cmd = [
        ffmpeg,
        *_FFMPEG_BASE_ARGS,
        "-i", str(src),
        *_FFMPEG_TARGET_ARGS,
        tmp_path,
    ]

    try:
        subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            timeout=_CONVERSION_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        Path(tmp_path).unlink(missing_ok=True)
        raise RuntimeError(
            f"Audio extraction timed out after {_CONVERSION_TIMEOUT_SECONDS}s."
        )
    except subprocess.CalledProcessError as err:
        Path(tmp_path).unlink(missing_ok=True)
        detail = (err.stderr or err.stdout or "").strip() or str(err)
        raise RuntimeError(f"ffmpeg audio extraction failed: {detail}") from err

    # Verify the output file is non-empty
    if not os.path.isfile(tmp_path) or os.path.getsize(tmp_path) == 0:
        Path(tmp_path).unlink(missing_ok=True)
        return None

    return tmp_path
