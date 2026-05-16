"""
Unit tests for audio.extractor — audio extraction from video files.
"""

import os
import sys
import types
import subprocess

import pytest

# Ensure emotion-recognizer is importable
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from audio.extractor import extract_audio, _resolve_ffmpeg


# ── Tests ────────────────────────────────────────────────────────────────

def test_resolve_ffmpeg():
    """ffmpeg should be discoverable (PATH or imageio-ffmpeg)."""
    result = _resolve_ffmpeg()
    # It's OK if ffmpeg isn't installed in CI — test is informational
    if result is None:
        pytest.skip("ffmpeg not available in this environment")
    assert os.path.isfile(result) or result == "ffmpeg"


def test_extract_audio_file_not_found():
    """extract_audio should raise FileNotFoundError for missing files."""
    with pytest.raises(FileNotFoundError):
        extract_audio("/nonexistent/video.mp4")


def test_extract_audio_mocked(tmp_path, monkeypatch):
    """
    extract_audio should call ffmpeg and return a .wav path.
    We mock subprocess.run to avoid needing a real video file.
    """
    # Create a fake video file
    fake_video = tmp_path / "test_video.mp4"
    fake_video.write_bytes(b"\x00" * 100)

    # Mock _resolve_ffmpeg
    monkeypatch.setattr("audio.extractor._resolve_ffmpeg", lambda: "ffmpeg")

    # Track subprocess.run calls
    calls = []

    def mock_run(cmd, **kwargs):
        calls.append(cmd)
        # Create the output file (the last arg before the url)
        # Find the output path — it's the argument after the target args
        out_path = cmd[-1]
        with open(out_path, "wb") as f:
            # Write a minimal WAV-like content
            f.write(b"RIFF" + b"\x00" * 100)
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr("subprocess.run", mock_run)

    result = extract_audio(str(fake_video))

    assert result is not None
    assert result.endswith(".wav")
    assert os.path.isfile(result)
    assert len(calls) == 1
    assert "ffmpeg" in calls[0][0]

    # Cleanup
    os.unlink(result)


def test_extract_audio_ffmpeg_failure(tmp_path, monkeypatch):
    """extract_audio should raise RuntimeError if ffmpeg fails."""
    fake_video = tmp_path / "bad_video.mp4"
    fake_video.write_bytes(b"\x00" * 100)

    monkeypatch.setattr("audio.extractor._resolve_ffmpeg", lambda: "ffmpeg")

    def mock_run(cmd, **kwargs):
        raise subprocess.CalledProcessError(1, cmd, stderr="decode error")

    monkeypatch.setattr("subprocess.run", mock_run)

    with pytest.raises(RuntimeError, match="ffmpeg audio extraction failed"):
        extract_audio(str(fake_video))


def test_extract_audio_no_ffmpeg(tmp_path, monkeypatch):
    """extract_audio should raise RuntimeError if ffmpeg is not found."""
    fake_video = tmp_path / "video.mp4"
    fake_video.write_bytes(b"\x00" * 100)

    monkeypatch.setattr("audio.extractor._resolve_ffmpeg", lambda: None)

    with pytest.raises(RuntimeError, match="ffmpeg not found"):
        extract_audio(str(fake_video))
