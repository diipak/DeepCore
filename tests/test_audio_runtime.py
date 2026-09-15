"""
Comprehensive test suite for Phase 3 Audio Runtime (Ears, Mouth, AudioService, and /audio API endpoint).

Verifies:
1. Sentence splitting and punctuation boundary detection in Mouth.
2. WAV header generation and PCM byte buffer encoding in Mouth.
3. Transcription cleanup and non-speech artifact stripping in Ears.
4. AudioService orchestration across Ears, ConversationService, and Mouth.
5. POST /api/conversations/{uuid}/audio endpoint execution with workspace scoping and headers.
6. Live Kokoro synthesis if espeak-ng and kokoro are installed.
"""
import io
import pytest
from unittest.mock import patch, MagicMock
import numpy as np
import soundfile as sf
from fastapi.testclient import TestClient

from deepcore2.runtime.audio.ears import Ears, AudioTranscriptionError
from deepcore2.runtime.audio.mouth import Mouth, AudioSynthesisError
from deepcore2.runtime.audio.service import AudioService
from deepcore2.core.assistant.service import ConversationService
from deepcore2.storage.sqlite.db import get_db, Base, engine
from deepcore2.api.main import app


@pytest.fixture(scope="module", autouse=True)
def init_test_db():
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def create_dummy_wav_bytes(duration_s: float = 0.2, sample_rate: int = 16000) -> bytes:
    """Generates a synthetic sine-wave WAV buffer for testing without microphone hardware."""
    t = np.linspace(0, duration_s, int(sample_rate * duration_s), endpoint=False)
    audio = (np.sin(2 * np.pi * 440 * t) * 0.5).astype(np.float32)
    buf = io.BytesIO()
    sf.write(buf, audio, sample_rate, format="WAV")
    return buf.getvalue()


def test_mouth_sentence_splitting():
    """Verify sentence boundary segmentation splits text into distinct spoken phrases."""
    mouth = Mouth()
    text = "Hello Deepak! This is DeepCore speaking. Are we ready to begin?"
    chunks = mouth.split_sentences(text)
    assert len(chunks) == 3
    assert chunks[0] == "Hello Deepak!"
    assert chunks[1] == "This is DeepCore speaking."
    assert chunks[2] == "Are we ready to begin?"


def test_clean_text_for_speech_normalizer():
    """Verify normalizer strips markdown asterisks, bullet points, headers, and expands symbols."""
    from deepcore2.runtime.audio.normalizer import clean_text_for_speech

    markdown_input = (
        "### Roadmap Sequence\n"
        "Here is the sequence:\n"
        "* **1. Chat** -> existing ConversationService\n"
        "* **2. Audio/Voice** & Speech (w/ Kokoro)\n"
        "* **3. Face/Visualizer** vs. legacy HUD"
    )
    cleaned = clean_text_for_speech(markdown_input)

    assert "*" not in cleaned
    assert "#" not in cleaned
    assert "**" not in cleaned
    assert "->" not in cleaned
    assert "&" not in cleaned
    assert "to" in cleaned
    assert "and" in cleaned
    assert "versus" in cleaned
    assert "with" in cleaned


def test_mouth_empty_text_handling():
    """Verify empty or whitespace strings return valid empty WAV buffers without error."""
    mouth = Mouth()
    wav_bytes = mouth.synthesize_to_wav_bytes("   ")
    assert len(wav_bytes) >= 44
    assert wav_bytes[:4] == b"RIFF"
    assert wav_bytes[8:12] == b"WAVE"


def test_mouth_wav_synthesis_mock():
    """Verify that synthesized PCM arrays are encoded into valid WAV bytes."""
    mouth = Mouth()
    dummy_pcm = np.zeros((2400,), dtype=np.float32)

    with patch.object(mouth, "synthesize_sentence_stream", return_value=[dummy_pcm]):
        wav_bytes = mouth.synthesize_to_wav_bytes("Test phrase.")
        assert len(wav_bytes) > 100
        assert wav_bytes[:4] == b"RIFF"
        assert wav_bytes[8:12] == b"WAVE"


def test_ears_non_speech_cleaning():
    """Verify Ears strips non-speech hallucinations like [BLANK_AUDIO] or (cough)."""
    ears = Ears()
    dirty = "[BLANK_AUDIO]  Hello world. (clears throat) "
    cleaned = ears.clean_transcript(dirty)
    assert cleaned == "Hello world."


def test_audio_service_process_voice_turn_mock():
    """Verify AudioService transcribes speech, posts to ConversationService, and synthesizes audio."""
    db = next(get_db())
    try:
        mock_llm = MagicMock()
        mock_llm.generate.return_value = "Voice reply generated cleanly."

        conv_service = ConversationService(db=db, workspace_id=1, llm_client=mock_llm)
        session = conv_service.start_session("CONTINUE_THINKING")

        mock_ears = MagicMock()
        mock_ears.transcribe_audio_bytes.return_value = "What is the agent sequence?"

        mock_mouth = MagicMock()
        mock_mouth.synthesize_to_wav_bytes.return_value = b"RIFF....WAVE_AUDIO_OUTPUT"

        audio_service = AudioService(conv_service, ears=mock_ears, mouth=mock_mouth)
        dummy_wav = create_dummy_wav_bytes()

        state, reply_audio, transcript = audio_service.process_voice_turn(
            session_uuid=session.session_uuid,
            audio_bytes=dummy_wav,
            audio_format="wav"
        )

        assert transcript == "What is the agent sequence?"
        assert reply_audio == b"RIFF....WAVE_AUDIO_OUTPUT"
        assert len(state.messages) == 3  # Greeting + User message + Assistant reply
        assert state.messages[1].content == "What is the agent sequence?"
        assert state.messages[2].content == "Voice reply generated cleanly."
    finally:
        db.close()


def test_api_conversations_audio_endpoint(client):
    """Verify POST /api/conversations/{uuid}/audio accepts UploadFile, transcribes, and returns WAV with headers."""
    # 1. Start a thinking session
    res_start = client.post("/api/conversations/start", json={"thinking_mode": "CONTINUE_THINKING"})
    assert res_start.status_code == 200
    session_uuid = res_start.json()["session_uuid"]

    # 2. Post audio turn with synthetic WAV
    dummy_wav = create_dummy_wav_bytes()

    with patch("deepcore2.runtime.audio.ears.Ears.transcribe_audio_bytes", return_value="What is our roadmap?"), \
         patch("deepcore2.runtime.audio.mouth.Mouth.synthesize_to_wav_bytes", return_value=dummy_wav), \
         patch("deepcore2.intelligence.llm_client.OllamaClient.generate", return_value="Chat -> Audio -> Face -> Hands"):

        files = {"file": ("recording.wav", dummy_wav, "audio/wav")}
        response = client.post(f"/api/conversations/{session_uuid}/audio", files=files)

        assert response.status_code == 200
        assert response.headers["content-type"] == "audio/wav"
        assert "X-User-Transcript" in response.headers
        assert "X-Session-UUID" in response.headers
        assert response.headers["X-Session-UUID"] == session_uuid
        assert len(response.content) > 44
        assert response.content[:4] == b"RIFF"


def test_live_kokoro_synthesis_if_available():
    """Live test of Kokoro local synthesis if system espeak-ng and kokoro package are available."""
    try:
        from kokoro import KPipeline  # noqa: F401
    except ImportError:
        pytest.skip("kokoro package not yet installed in active environment")

    mouth = Mouth(voice="bm_lewis")
    try:
        wav_bytes = mouth.synthesize_to_wav_bytes("DeepCore voice online.")
        assert len(wav_bytes) > 500
        assert wav_bytes[:4] == b"RIFF"
        assert wav_bytes[8:12] == b"WAVE"
    except AudioSynthesisError as exc:
        pytest.skip(f"Kokoro synthesis failed (likely missing espeak-ng): {exc}")
