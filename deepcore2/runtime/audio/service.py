"""
Audio Service — orchestrates Ears (STT), Mouth (TTS), and ConversationService.

Provides the end-to-end bridge between audio I/O adapters and the deterministic
kernel and grounded reasoning engine.
"""
from typing import Optional, Tuple
from sqlalchemy.orm import Session

from deepcore2.core.assistant.schema import ConversationState
from deepcore2.core.assistant.service import ConversationService
from deepcore2.runtime.audio.ears import Ears, AudioTranscriptionError
from deepcore2.runtime.audio.mouth import Mouth, AudioSynthesisError


class AudioService:
    """Coordinates speech transcription, conversation evolution, and speech synthesis."""

    def __init__(
        self,
        conversation_service: ConversationService,
        ears: Optional[Ears] = None,
        mouth: Optional[Mouth] = None,
    ):
        self.conversation_service = conversation_service
        self.ears = ears or Ears()
        self.mouth = mouth or Mouth()

    def process_voice_turn(
        self,
        session_uuid: str,
        audio_bytes: bytes,
        audio_format: str = "wav"
    ) -> Tuple[ConversationState, bytes, str]:
        """
        Processes one full audio conversation turn:
        1. Transcribe speech audio into text via Ears.
        2. Post message to ConversationService (grounded Ollama reasoning + OpenMemory citations).
        3. Synthesize assistant response into WAV audio bytes via Mouth.
        
        Returns:
            (updated_conversation_state, response_wav_bytes, transcribed_user_text)
        """
        # 1. Transcribe user speech
        transcript = self.ears.transcribe_audio_bytes(audio_bytes, file_extension=audio_format)
        if not transcript.strip():
            current_state = self.conversation_service.get_session_state(session_uuid)
            return current_state, b"", ""

        # 2. Advance Conversation via ConversationService
        state = self.conversation_service.post_message(session_uuid, transcript)
        assistant_message = state.messages[-1]
        reply_text = assistant_message.content

        # 3. Synthesize assistant reply into audio
        try:
            audio_out = self.mouth.synthesize_to_wav_bytes(reply_text)
        except AudioSynthesisError:
            # Degrade gracefully: return state with empty audio rather than failing the whole turn
            audio_out = b""

        return state, audio_out, transcript
