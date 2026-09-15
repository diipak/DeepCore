"""
Interactive Voice Test Bench for DeepCore 2.0 (Phase 3: The Voice).

Allows push-to-talk voice interactions in terminal, speaking out loud through Mac speakers.
"""
import io
import time
import numpy as np
import sounddevice as sd
import soundfile as sf

from deepcore2.config import settings
from deepcore2.core.assistant.service import ConversationService
from deepcore2.runtime.audio.service import AudioService
from deepcore2.runtime.audio.ears import Ears
from deepcore2.runtime.audio.mouth import Mouth
from deepcore2.storage.sqlite.db import get_db


def record_audio_clip(sample_rate: int = 16000) -> bytes:
    """Records audio from microphone until user presses Enter."""
    input("\n🎤 Press [ENTER] to START recording your question...")
    print("🔴 Recording... (speak now into your microphone)")

    frames = []
    stop_event = False

    def callback(indata, frame_count, time_info, status):
        if not stop_event:
            frames.append(indata.copy())

    stream = sd.InputStream(samplerate=sample_rate, channels=1, dtype="float32", callback=callback)
    with stream:
        input("⏹️  Press [ENTER] again to STOP recording...")
        stop_event = True

    if not frames:
        return b""

    recording = np.concatenate(frames, axis=0)
    buf = io.BytesIO()
    sf.write(buf, recording, sample_rate, format="WAV")
    return buf.getvalue()


def play_audio_bytes(wav_bytes: bytes):
    """Plays WAV audio bytes through default audio output device."""
    if not wav_bytes or len(wav_bytes) < 100:
        return
    buf = io.BytesIO(wav_bytes)
    data, fs = sf.read(buf, dtype="float32")
    sd.play(data, fs)
    sd.wait()


def main():
    print("=" * 65)
    print("🎙️ DeepCore 2.0 — Interactive Voice Test Bench")
    print("=" * 65)
    print(f"STT Model: {settings.AUDIO_STT_MODEL}")
    print(f"TTS Voice: {settings.AUDIO_TTS_VOICE} (speed: {settings.AUDIO_TTS_SPEED})")
    print("Initializing ConversationService and Audio Engines...")

    db = next(get_db())
    try:
        conv_service = ConversationService(db=db, workspace_id=1)
        ears = Ears()
        mouth = Mouth()
        audio_service = AudioService(conv_service, ears=ears, mouth=mouth)

        session = conv_service.start_session("CONTINUE_THINKING")
        print(f"Session UUID: {session.session_uuid}")
        print(f"Assistant: {session.messages[0].content}\n")
        print("Initial greeting playing through speakers...")
        greeting_audio = mouth.synthesize_to_wav_bytes(session.messages[0].content)
        play_audio_bytes(greeting_audio)

        while True:
            try:
                audio_clip = record_audio_clip(sample_rate=16000)
                if not audio_clip:
                    print("No audio captured.")
                    continue

                t0 = time.time()
                print("⚡ Processing voice turn (STT -> Grounded RAG -> TTS)...")
                state, reply_audio, transcript = audio_service.process_voice_turn(
                    session_uuid=session.session_uuid,
                    audio_bytes=audio_clip,
                    audio_format="wav"
                )
                elapsed = time.time() - t0

                print(f"\nUser (transcribed) > {transcript}")
                print(f"DeepCore ({elapsed:.2f}s total pipeline latency) > {state.messages[-1].content}")

                if state.messages[-1].evidence:
                    print("\n[Evidential Citations]:")
                    for ev in state.messages[-1].evidence:
                        print(f"  • [{ev.source_uuid}] ({','.join(ev.relationship_path)}): {ev.reason}")

                print("🔊 Speaking reply...")
                play_audio_bytes(reply_audio)

                cont = input("\nContinue talking? [Y/n]: ").strip().lower()
                if cont in ("n", "no", "exit", "quit"):
                    break
            except KeyboardInterrupt:
                print("\nVoice session closed.")
                break
    finally:
        db.close()


if __name__ == "__main__":
    main()
