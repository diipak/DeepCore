"""
The Ears — local Speech-To-Text (STT) engine for DeepCore.

Auto-selects Apple Silicon Metal GPU acceleration via mlx-whisper on macOS arm64,
falling back to faster-whisper or CPU where appropriate.
Zero cloud API costs; all transcription runs on-device.
"""
import os
import platform
import re
import sys
import tempfile
import threading
from typing import Optional
import numpy as np

from deepcore2.config import settings

_NONSPEECH = re.compile(r"[\[(][^\])]*[\])]")


class AudioTranscriptionError(Exception):
    """Raised when an audio recording cannot be processed or transcribed."""
    pass


class Ears:
    """Synchronous speech-to-text transcriber with Apple Silicon Metal acceleration."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        backend: Optional[str] = None,
    ):
        self.model_name = model_name or settings.AUDIO_STT_MODEL
        self.backend_pref = (backend or settings.AUDIO_STT_BACKEND).lower()
        self._lock = threading.Lock()
        self._faster_whisper_model = None

    def _is_apple_silicon_available(self) -> bool:
        """Check if Apple Silicon MLX GPU backend is available."""
        if self.backend_pref == "whisper":
            return False
        if sys.platform != "darwin" or platform.machine() != "arm64":
            return False
        try:
            import mlx_whisper  # noqa: F401
            return True
        except ImportError:
            return False

    def transcribe_audio_bytes(self, audio_bytes: bytes, file_extension: str = "wav") -> str:
        """
        Transcribe raw audio bytes by persisting temporarily to disk for decoder ingestion.
        Supports WAV, WebM, MP3, OGG, and M4A.
        """
        if not audio_bytes or len(audio_bytes) < 100:
            return ""

        suffix = f".{file_extension.lstrip('.')}"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp_file:
            tmp_path = tmp_file.name
            tmp_file.write(audio_bytes)

        try:
            return self.transcribe_file(tmp_path)
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

    def transcribe_file(self, file_path: str) -> str:
        """Transcribe an audio file from disk using the active STT backend."""
        if not os.path.exists(file_path):
            raise AudioTranscriptionError(f"Audio file not found at path: {file_path}")

        try:
            if self._is_apple_silicon_available():
                import mlx_whisper
                result = mlx_whisper.transcribe(
                    file_path,
                    path_or_hf_repo=self.model_name,
                )
                raw_text = result.get("text", "")
            else:
                # Fallback to faster-whisper
                with self._lock:
                    if self._faster_whisper_model is None:
                        from faster_whisper import WhisperModel
                        # Base model fallback name if MLX repo string was passed
                        fw_name = self.model_name.split("/")[-1].replace("-mlx", "").replace("whisper-", "") or "base.en"
                        self._faster_whisper_model = WhisperModel(fw_name, device="cpu", compute_type="int8")

                segments, _ = self._faster_whisper_model.transcribe(file_path, beam_size=1)
                raw_text = " ".join(seg.text for seg in segments)

        except Exception as exc:
            raise AudioTranscriptionError(f"Transcription failed: {exc}") from exc

        return self.clean_transcript(raw_text)

    def clean_transcript(self, text: str) -> str:
        """Strip non-speech hallucination brackets (e.g. [BLANK_AUDIO], (muffled)) and trailing whitespace."""
        if not text:
            return ""
        return _NONSPEECH.sub("", text).strip()
