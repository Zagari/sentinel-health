import subprocess
import wave

import pytest

from app.utils import audio_converter
from app.utils.audio_converter import (
    convert_to_wav,
    prepare_audio_path_for_azure_speech,
    read_pcm_s16le_16k_mono_bytes,
)


def _write_wav(path, *, channels=1, sample_width=2, frame_rate=16000, frames=b"\x01\x00"):
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(frame_rate)
        wav_file.writeframes(frames)


def test_read_pcm_s16le_16k_mono_bytes_reads_azure_compatible_wav(tmp_path):
    wav_path = tmp_path / "compatible.wav"
    frames = b"\x01\x00\x02\x00"
    _write_wav(wav_path, frames=frames)

    assert read_pcm_s16le_16k_mono_bytes(str(wav_path)) == frames


def test_read_pcm_s16le_16k_mono_bytes_rejects_wrong_format(tmp_path):
    wav_path = tmp_path / "stereo.wav"
    _write_wav(wav_path, channels=2, frames=b"\x01\x00\x02\x00")

    with pytest.raises(ValueError, match="WAV deve ser PCM 16-bit mono 16 kHz"):
        read_pcm_s16le_16k_mono_bytes(str(wav_path))


def test_prepare_audio_path_reuses_compatible_wav(tmp_path):
    wav_path = tmp_path / "compatible.wav"
    _write_wav(wav_path)

    prepared_path, temporary_file = prepare_audio_path_for_azure_speech(str(wav_path))

    assert prepared_path == str(wav_path.resolve())
    assert temporary_file is None


def test_prepare_audio_path_converts_non_compatible_audio(monkeypatch, tmp_path):
    source_path = tmp_path / "audio.mp3"
    converted_path = tmp_path / "converted.wav"
    source_path.write_bytes(b"fake mp3")
    converted_path.write_bytes(b"fake wav")

    monkeypatch.setattr(
        "app.utils.audio_converter.convert_to_wav",
        lambda input_path: str(converted_path),
    )

    prepared_path, temporary_file = prepare_audio_path_for_azure_speech(str(source_path))

    assert prepared_path == str(converted_path)
    assert temporary_file == converted_path


def test_convert_to_wav_raises_runtime_error_when_ffmpeg_times_out(monkeypatch, tmp_path):
    source_path = tmp_path / "audio.mp3"
    source_path.write_bytes(b"fake mp3")

    monkeypatch.setattr(audio_converter, "_resolve_ffmpeg", lambda: "fake-ffmpeg")

    def _raise_timeout(*_args, **_kwargs):
        raise subprocess.TimeoutExpired(cmd="fake-ffmpeg", timeout=1)

    monkeypatch.setattr(audio_converter.subprocess, "run", _raise_timeout)

    with pytest.raises(RuntimeError, match="Tempo limite"):
        convert_to_wav(str(source_path))


def test_convert_to_wav_raises_runtime_error_when_ffmpeg_fails(monkeypatch, tmp_path):
    source_path = tmp_path / "audio.mp3"
    source_path.write_bytes(b"fake mp3")

    monkeypatch.setattr(audio_converter, "_resolve_ffmpeg", lambda: "fake-ffmpeg")

    def _raise_called_process_error(*_args, **_kwargs):
        raise subprocess.CalledProcessError(
            returncode=1,
            cmd="fake-ffmpeg",
            stderr="entrada inválida",
        )

    monkeypatch.setattr(audio_converter.subprocess, "run", _raise_called_process_error)

    with pytest.raises(RuntimeError, match="entrada inválida"):
        convert_to_wav(str(source_path))


def test_convert_to_wav_raises_runtime_error_when_ffmpeg_not_available(monkeypatch, tmp_path):
    source_path = tmp_path / "audio.mp3"
    source_path.write_bytes(b"fake mp3")

    monkeypatch.setattr(audio_converter, "_resolve_ffmpeg", lambda: None)

    with pytest.raises(RuntimeError, match="ffmpeg não encontrado"):
        convert_to_wav(str(source_path))
