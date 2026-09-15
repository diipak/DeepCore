"""
The Mouth — local streaming Text-To-Speech (TTS) engine for DeepCore.

Uses Kokoro (82M parameter lightweight model) for in-process high-fidelity synthesis.
Generates streaming audio or WAV byte buffers with zero cloud dependencies.
"""
import io
import os
import re
import threading
from typing import Generator, List, Optional
import numpy as np

from deepcore2.config import settings

_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


def _ensure_espeak():
    """Ensure phonemizer locates libespeak-ng on macOS Homebrew or standard system paths."""
    if os.environ.get("PHONEMIZER_ESPEAK_LIBRARY"):
        return
    candidates = (
        "/opt/homebrew/lib/libespeak-ng.dylib",          # macOS arm64 (brew)
        "/usr/local/lib/libespeak-ng.dylib",             # macOS x86 (brew)
        "/usr/lib/x86_64-linux-gnu/libespeak-ng.so.1",   # Ubuntu/Debian
        "/usr/lib/libespeak-ng.so.1",                    # Generic Linux
    )
    for lib in candidates:
        if os.path.exists(lib):
            os.environ["PHONEMIZER_ESPEAK_LIBRARY"] = lib
            break


class AudioSynthesisError(Exception):
    """Raised when text cannot be converted into speech audio."""
    pass


class Mouth:
    """Local text-to-speech synthesizer powered by Kokoro."""

    def __init__(
        self,
        voice: Optional[str] = None,
        speed: Optional[float] = None,
        sample_rate: Optional[int] = None,
    ):
        self.voice = voice or settings.AUDIO_TTS_VOICE
        self.speed = speed if speed is not None else settings.AUDIO_TTS_SPEED
        self.sample_rate = sample_rate or settings.AUDIO_SAMPLE_RATE
        self._lock = threading.Lock()
        self._pipeline = None

    def _get_pipeline(self):
        """Lazily initialize Kokoro KPipeline with system phonemizer."""
        with self._lock:
            if self._pipeline is None:
                _ensure_espeak()
                try:
                    from kokoro import KPipeline
                    # Language code is derived from voice prefix (e.g. 'b' for British, 'a' for American)
                    lang_code = self.voice[0] if self.voice and len(self.voice) > 1 else 'b'
                    self._pipeline = KPipeline(lang_code=lang_code, repo_id="hexgrad/Kokoro-82M")
                except Exception as exc:
                    raise AudioSynthesisError(
                        f"Failed to initialize Kokoro TTS pipeline: {exc}. "
                        "Ensure 'brew install espeak-ng' and 'kokoro' are installed."
                    ) from exc
            return self._pipeline

    def split_sentences(self, text: str) -> List[str]:
        """Sanitize text of markdown syntax/asterisks and split into sentence chunks."""
        from deepcore2.runtime.audio.normalizer import clean_text_for_speech
        clean_text = clean_text_for_speech(text)
        if not clean_text:
            return []
        chunks = _SENTENCE_RE.split(clean_text)
        return [c.strip() for c in chunks if c.strip()]

    def synthesize_sentence_stream(self, text: str) -> Generator[np.ndarray, None, None]:
        """
        Synthesize text sentence-by-sentence, yielding numpy PCM audio arrays.
        Enables first-sentence audio playback while subsequent sentences render in the background.
        """
        sentences = self.split_sentences(text)
        if not sentences:
            return

        pipeline = self._get_pipeline()
        for sentence in sentences:
            try:
                generator = pipeline(sentence, voice=self.voice, speed=self.speed, split_pattern=r'\n+')
                for _, _, audio in generator:
                    if audio is not None and len(audio) > 0:
                        yield audio
            except Exception as exc:
                raise AudioSynthesisError(f"Error synthesizing sentence '{sentence[:30]}...': {exc}") from exc

    def synthesize_to_wav_bytes(self, text: str) -> bytes:
        """Synthesize entire text into an in-memory WAV byte buffer."""
        import soundfile as sf

        audio_chunks = list(self.synthesize_sentence_stream(text))
        if not audio_chunks:
            # Return valid empty 44-byte WAV buffer
            buf = io.BytesIO()
            empty_arr = np.zeros((0,), dtype=np.float32)
            sf.write(buf, empty_arr, self.sample_rate, format="WAV")
            return buf.getvalue()

        combined = np.concatenate(audio_chunks)
        buf = io.BytesIO()
        sf.write(buf, combined, self.sample_rate, format="WAV")
        return buf.getvalue()
