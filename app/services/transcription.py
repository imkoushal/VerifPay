"""
VerifPay — Voice Transcription Service

Sends audio files to Groq Whisper API for transcription.
Supports Hindi, English, and Hinglish voice recordings.
"""

import asyncio
import logging
from typing import Optional

from groq import Groq

from app.config import settings

logger = logging.getLogger(__name__)


class TranscriptionService:
    """Groq Whisper powered audio transcription."""

    def __init__(self):
        self._client: Optional[Groq] = None

    def _get_client(self) -> Groq:
        """Lazy-initialize the Groq client."""
        if self._client is None:
            if not settings.GROQ_API_KEY:
                raise ValueError("GROQ_API_KEY not set in environment variables")
            self._client = Groq(api_key=settings.GROQ_API_KEY)
        return self._client

    async def transcribe(
        self,
        audio_file,
        filename: str = "audio.wav",
        language: str = "hi",
    ) -> str:
        """
        Transcribe audio using Groq Whisper API.
        Runs the synchronous Groq SDK call in a thread to avoid blocking the event loop.

        Args:
            audio_file: File-like object or bytes of the audio
            filename: Original filename (helps Whisper detect format)
            language: Language hint — 'hi' for Hindi, 'en' for English
        
        Returns:
            Transcribed text string
        """
        return await asyncio.to_thread(
            self._transcribe_sync, audio_file, filename, language,
        )

    def _transcribe_sync(
        self,
        audio_file,
        filename: str = "audio.wav",
        language: str = "hi",
    ) -> str:
        """Synchronous transcription — called via asyncio.to_thread()."""
        try:
            client = self._get_client()

            transcription = client.audio.transcriptions.create(
                file=(filename, audio_file),
                model=settings.GROQ_WHISPER_MODEL,
                language=language,
                response_format="text",
                temperature=0.0,  # Deterministic transcription
            )

            text = str(transcription).strip()
            logger.info(f"Transcription ({language}): {text[:100]}...")
            return text

        except Exception as e:
            logger.error(f"Whisper transcription failed: {e}")
            raise


# Global singleton
transcription_service = TranscriptionService()
