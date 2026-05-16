import logging
import os
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)

_FFMPEG_BASE_ARGS: tuple[str, ...] = ("-hide_banner", "-loglevel", "error", "-y")
_FFMPEG_TARGET_ARGS: tuple[str, ...] = ("-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le")


def _resolve_ffmpeg() -> str | None:
    if exe := shutil.which("ffmpeg"):
        return exe
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return None


def read_pcm_s16le_16k_mono_bytes(wav_path: str) -> bytes:
    """Lê amostras PCM 16-bit LE mono 16 kHz (sem cabeçalho) de um WAV compatível com o Azure."""
    path = Path(wav_path).expanduser().resolve()
    with wave.open(str(path), "rb") as wf:
        if wf.getcomptype() != "NONE":
            raise ValueError(f"WAV deve ser PCM linear (comptype={wf.getcomptype()!r}).")
        if wf.getsampwidth() != 2 or wf.getnchannels() != 1 or wf.getframerate() != 16000:
            raise ValueError(
                "WAV deve ser PCM 16-bit mono 16 kHz "
                f"(obtido: {wf.getframerate()} Hz, {wf.getnchannels()} canais, {wf.getsampwidth()} bytes/amostra)."
            )
        data = wf.readframes(wf.getnframes())
    if not data:
        raise ValueError("Áudio vazio.")
    return data


def _is_pcm_wav_16k_mono_s16le(path: Path) -> bool:
    try:
        with wave.open(str(path), "rb") as wf:
            return (
                wf.getcomptype() == "NONE"
                and wf.getsampwidth() == 2
                and wf.getnchannels() == 1
                and wf.getframerate() == 16000
            )
    except (wave.Error, OSError):
        return False


def _create_temporary_wav() -> Path:
    fd, tmp = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    return Path(tmp)


def _build_ffmpeg_command(ffmpeg: str, src: Path, out: Path) -> list[str]:
    return [ffmpeg, *_FFMPEG_BASE_ARGS, "-i", str(src), *_FFMPEG_TARGET_ARGS, str(out)]


def convert_to_wav(input_path: str) -> str:
    """
    Transcodifica o arquivo para WAV PCM 16-bit, mono, 16 kHz (formato esperado pelo Azure Speech).

    O resultado é sempre um arquivo temporário; quem chama deve removê-lo após uso.
    """
    src = Path(input_path).expanduser().resolve()
    if not src.is_file():
        raise FileNotFoundError(f"Arquivo de áudio não encontrado: {src}")

    ffmpeg = _resolve_ffmpeg()
    if not ffmpeg:
        raise RuntimeError(
            "ffmpeg não encontrado (PATH nem imageio-ffmpeg). "
            "Instale o ffmpeg ou mantenha a dependência imageio-ffmpeg."
        )

    out = _create_temporary_wav()
    command = _build_ffmpeg_command(ffmpeg, src, out)
    timeout_seconds = settings.audio_conversion_timeout_seconds

    try:
        subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as err:
        out.unlink(missing_ok=True)
        logger.error(
            "Tempo limite excedido na conversão de áudio com ffmpeg",
            extra={
                "event": "audio_conversion_failed",
                "service": "ffmpeg",
                "stage": "conversion",
                "reason": "timeout",
                "timeout_seconds": timeout_seconds,
                "source_path": str(src),
            },
        )
        raise RuntimeError(
            f"Tempo limite ({timeout_seconds}s) excedido na conversão do áudio."
        ) from err
    except subprocess.CalledProcessError as err:
        out.unlink(missing_ok=True)
        detail = (err.stderr or err.stdout or "").strip() or str(err)
        logger.error(
            "ffmpeg retornou erro ao converter áudio",
            extra={
                "event": "audio_conversion_failed",
                "service": "ffmpeg",
                "stage": "conversion",
                "reason": "ffmpeg_error",
                "source_path": str(src),
                "ffmpeg_detail": detail,
            },
        )
        raise RuntimeError(f"Falha ao converter áudio (ffmpeg): {detail}") from err

    return str(out.resolve())


def prepare_audio_path_for_azure_speech(input_path: str) -> tuple[str, Path | None]:
    """
    Devolve (caminho_wav_para_AudioConfig, arquivo_temporário_a_apagar_ou_None).

    Se já for WAV PCM 16 kHz mono 16-bit, reutiliza o arquivo original (sem conversão).
    """
    src = Path(input_path).expanduser().resolve()
    if not src.is_file():
        raise FileNotFoundError(f"Arquivo de áudio não encontrado: {src}")

    if src.suffix.lower() == ".wav" and _is_pcm_wav_16k_mono_s16le(src):
        return str(src), None

    converted = Path(convert_to_wav(str(src)))
    return str(converted), converted
