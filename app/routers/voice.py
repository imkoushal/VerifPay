"""
POST /voice — Voice Transcription + Fraud Analysis

Accepts audio file uploads, transcribes using Groq Whisper,
then passes the transcribed text through the /analyse pipeline.
Returns both the transcription and the fraud analysis result.
"""

import logging
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional

from app.models.schemas import (
    AnalyseRequest,
    AnalyseResponse,
    VoiceAnalyseResponse,
    InputType,
)
from app.services.transcription import transcription_service
from app.routers.analyse import analyse_text

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Voice"])

# Allowed audio MIME types
ALLOWED_TYPES = {
    "audio/mpeg", "audio/mp3", "audio/wav", "audio/x-wav",
    "audio/ogg", "audio/webm", "audio/flac", "audio/m4a",
    "audio/mp4", "audio/x-m4a", "audio/aac",
    "video/mp4",  # Some voice recorders save as mp4
    "application/octet-stream",  # Fallback for unknown types
}

# Max file size: 25MB (Groq Whisper limit)
MAX_FILE_SIZE = 25 * 1024 * 1024


@router.post("/voice", response_model=VoiceAnalyseResponse)
async def analyse_voice(
    file: UploadFile = File(..., description="Audio file to transcribe and analyse"),
    language: Optional[str] = Form("hi", description="Language hint: hi=Hindi, en=English"),
):
    """
    Transcribe a voice recording and analyse the transcribed text for fraud.

    Pipeline:
        1. Validate audio file (type + size)
        2. Send to Groq Whisper for transcription
        3. Pass transcribed text through /analyse pipeline
        4. Return both transcription and fraud verdict

    Supports: MP3, WAV, OGG, WebM, FLAC, M4A, AAC
    Max size: 25MB
    Languages: Hindi (hi), English (en)
    """
    # ── Validate file ──────────────────────────────────────────
    if file.content_type and file.content_type not in ALLOWED_TYPES:
        logger.warning(f"Rejected file type: {file.content_type}")
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format: {file.content_type}. Supported: MP3, WAV, OGG, WebM, FLAC, M4A, AAC",
        )

    # Read file content
    audio_bytes = await file.read()

    if len(audio_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large ({len(audio_bytes) / 1024 / 1024:.1f}MB). Max: 25MB.",
        )

    if len(audio_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty audio file.")

    logger.info(f"Voice upload: {file.filename} ({len(audio_bytes) / 1024:.1f}KB, type={file.content_type}, lang={language})")

    # ── Step 1: Transcribe with Groq Whisper ───────────────────
    try:
        transcribed_text = transcription_service.transcribe(
            audio_file=audio_bytes,
            filename=file.filename or "audio.wav",
            language=language or "hi",
        )
    except ValueError as e:
        # API key not set
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Voice transcription failed. Please try again or paste the text manually.",
        )

    if not transcribed_text or not transcribed_text.strip():
        raise HTTPException(
            status_code=400,
            detail="Could not transcribe any speech from the audio. Please try a clearer recording.",
        )

    logger.info(f"Transcribed ({language}): {transcribed_text[:100]}...")

    # ── Step 2: Analyse transcribed text ───────────────────────
    try:
        analyse_request = AnalyseRequest(text=transcribed_text)
        analysis = await analyse_text(analyse_request)

        # Override input_type to voice
        analysis.input_type = InputType.VOICE

    except Exception as e:
        logger.error(f"Analysis of transcribed text failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Transcription succeeded but analysis failed. Please try again.",
        )

    return VoiceAnalyseResponse(
        transcribed_text=transcribed_text,
        analysis=analysis,
    )
