"""
VerifPay — Telegram Bot Service

Handles all Telegram bot interactions:
    - /start: Welcome message with usage instructions
    - /help: Detailed help with examples
    - Text messages: Forward to /analyse pipeline, return formatted verdict
    - Voice notes: Download audio, transcribe via Groq Whisper, analyse
    - Multi-turn context: Stores last 3 messages per chat for follow-ups
"""

import io
import logging
from collections import defaultdict, deque
from typing import Optional

from telegram import Update, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

from app.config import settings
from app.models.schemas import AnalyseRequest, AnalyseResponse, VerdictLabel, InputType
from app.services.ml_classifier import ml_classifier
from app.services.rag_retriever import rag_retriever
from app.services.fraud_explainer import fraud_explainer
from app.services.url_checker import extract_urls, check_urls
from app.services.transcription import transcription_service

logger = logging.getLogger(__name__)

# ─── Multi-turn Context Store ──────────────────────────────────
# Stores last 3 messages per chat_id for follow-up context
_chat_context: dict[int, deque] = defaultdict(lambda: deque(maxlen=3))


# ─── Message Formatting ───────────────────────────────────────

WELCOME_MESSAGE = """
🛡️ *Welcome to VerifPay!*

I'm your AI-powered financial fraud detective, built specifically for Indian consumers.

*What I can do:*
• Detect fake UPI requests, phishing links, and scam messages
• Analyse suspicious SMS, WhatsApp forwards, and emails
• Transcribe and analyse scam voice recordings
• Explain exactly *why* something is suspicious

*How to use:*
Simply forward or paste any suspicious message to me, and I'll tell you if it's safe or a scam.

You can also send me voice notes of suspicious calls!

Type /help for more details.
""".strip()


HELP_MESSAGE = """
🛡️ *VerifPay — Help Guide*

*Commands:*
/start — Show welcome message
/help — Show this help guide

*How to check a message:*
1️⃣ *Forward a message:* Forward any suspicious SMS, WhatsApp message, or email directly to me
2️⃣ *Paste text:* Copy-paste the suspicious message text
3️⃣ *Send a voice note:* Record or forward a suspicious call recording

*What I check:*
• 🔗 Phishing links (fake bank URLs, suspicious domains)
• 🏦 Fake KYC messages (SBI, HDFC, ICICI impersonation)
• 💸 UPI fraud (fake payment/collect requests)
• 💳 Card scams (fake credit card offers)
• 🔑 OTP theft attempts
• 📈 Investment/lottery scams

*Examples of scams I detect:*
_"Your SBI KYC has expired. Update at http://sbi-kyc.xyz"_
_"You won Rs 50 lakh! Click to claim your prize"_
_"TRAI will disconnect your number in 2 hours"_

*Follow-up questions:*
After I analyse a message, you can ask follow-up questions like:
_"How do I report this to RBI?"_
_"Is this type of scam common?"_

Stay safe! 🇮🇳
""".strip()


def _format_verdict(result: AnalyseResponse, input_type: str = "text") -> str:
    """Format the analysis result as a Telegram message with emojis."""
    if result.verdict == VerdictLabel.SUSPICIOUS:
        verdict_line = "🚨 *SUSPICIOUS — Likely Fraud*"
    else:
        verdict_line = "✅ *SAFE — Appears Legitimate*"

    # Fraud type badge
    type_badges = {
        "PHISHING": "🔗 Phishing",
        "FAKE_KYC": "🏦 Fake KYC",
        "UPI_MANIPULATION": "💸 UPI Fraud",
        "CARD_SCAM": "💳 Card Scam",
        "OTP_FRAUD": "🔑 OTP Theft",
        "INVESTMENT_SCAM": "📈 Investment Scam",
        "SAFE": "✅ Safe",
    }
    fraud_badge = type_badges.get(result.fraud_type.value, result.fraud_type.value)

    # Confidence bar
    pct = int(result.confidence * 100)
    filled = pct // 10
    bar = "█" * filled + "░" * (10 - filled)

    lines = [
        verdict_line,
        "",
        f"*Type:* {fraud_badge}",
        f"*Confidence:* {bar} {pct}%",
    ]

    # Input type indicator
    if input_type == "voice":
        lines.append("*Input:* 🎤 Voice note")

    # Explanation
    if result.explanation:
        lines.append(f"\n💬 *Explanation:*\n{result.explanation}")

    # Red flags
    if result.red_flags:
        flags = "\n".join([f"  ⚠️ {flag}" for flag in result.red_flags])
        lines.append(f"\n🚩 *Red Flags:*\n{flags}")

    # URL checks
    if result.url_checks:
        url_lines = []
        for uc in result.url_checks:
            status = "🚫 PHISHING" if uc.is_phishing else "✅ Clean"
            url_lines.append(f"  {status}: {uc.url}")
        lines.append(f"\n🔗 *URL Checks:*\n" + "\n".join(url_lines))

    # Recommended action
    if result.recommended_action:
        lines.append(f"\n📋 *Action:* {result.recommended_action}")

    return "\n".join(lines)


async def _run_analysis(text: str) -> AnalyseResponse:
    """Run the full analysis pipeline (same as /analyse endpoint)."""
    # URL extraction + checking
    url_results = []
    try:
        urls = extract_urls(text)
        if urls:
            url_results = await check_urls(urls)
    except Exception as e:
        logger.error(f"URL check failed in bot: {e}")

    # ML classification
    ml_result = None
    try:
        ml_result = ml_classifier.classify(text)
    except Exception as e:
        logger.error(f"ML classification failed in bot: {e}")

    # RAG retrieval
    retrieved_patterns = []
    try:
        retrieved_patterns = rag_retriever.retrieve_fraud_patterns(text, top_k=5)
    except Exception as e:
        logger.error(f"RAG retrieval failed in bot: {e}")

    # LLM explanation
    explanation = None
    try:
        ml_verdict = ml_result.label.value if ml_result else "unknown"
        ml_confidence = ml_result.confidence if ml_result else 0.0
        url_dicts = [{"url": r.url, "is_phishing": r.is_phishing, "source": r.source, "threat_type": r.threat_type} for r in url_results] if url_results else None
        explanation = fraud_explainer.explain(
            text=text,
            ml_verdict=ml_verdict,
            ml_confidence=ml_confidence,
            retrieved_patterns=retrieved_patterns,
            url_results=url_dicts,
        )
    except Exception as e:
        logger.error(f"LLM explanation failed in bot: {e}")

    # Build response (same logic as analyse router)
    from app.routers.analyse import _build_response
    return _build_response(ml_result, explanation, url_results)


# ─── Bot Handlers ──────────────────────────────────────────────

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    await update.message.reply_text(WELCOME_MESSAGE, parse_mode="Markdown")
    logger.info(f"Bot /start from chat_id={update.effective_chat.id}")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    await update.message.reply_text(HELP_MESSAGE, parse_mode="Markdown")
    logger.info(f"Bot /help from chat_id={update.effective_chat.id}")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle any text message — analyse for fraud."""
    text = update.message.text.strip()
    chat_id = update.effective_chat.id

    if not text:
        await update.message.reply_text("Please send me a message to analyse.")
        return

    logger.info(f"Bot text from chat_id={chat_id}: {text[:80]}...")

    # Store in context for follow-ups
    _chat_context[chat_id].append({"role": "user", "text": text})

    # Check if this is a follow-up question
    if _is_followup(text) and len(_chat_context[chat_id]) > 1:
        await _handle_followup(update, text, chat_id)
        return

    # Send typing indicator
    await update.message.chat.send_action("typing")

    try:
        result = await _run_analysis(text)

        # Store result in context
        _chat_context[chat_id].append({
            "role": "bot",
            "verdict": result.verdict.value,
            "fraud_type": result.fraud_type.value,
        })

        response = _format_verdict(result)
        await update.message.reply_text(response, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Bot analysis failed for chat_id={chat_id}: {e}")
        await update.message.reply_text(
            "⚠️ Sorry, something went wrong during analysis. Please try again.",
        )


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice notes — download, transcribe, and analyse."""
    chat_id = update.effective_chat.id
    logger.info(f"Bot voice from chat_id={chat_id}")

    # Send typing indicator
    await update.message.chat.send_action("typing")
    await update.message.reply_text("🎤 Transcribing your voice note...")

    try:
        # Download the voice file
        voice = update.message.voice or update.message.audio
        if not voice:
            await update.message.reply_text("Could not process the audio file.")
            return

        file = await context.bot.get_file(voice.file_id)
        audio_bytes = await file.download_as_bytearray()

        # Determine filename extension
        mime = voice.mime_type or "audio/ogg"
        ext_map = {
            "audio/ogg": "ogg",
            "audio/mpeg": "mp3",
            "audio/mp4": "m4a",
            "audio/wav": "wav",
            "audio/x-wav": "wav",
        }
        ext = ext_map.get(mime, "ogg")
        filename = f"voice.{ext}"

        # Transcribe
        transcribed_text = transcription_service.transcribe(
            audio_file=bytes(audio_bytes),
            filename=filename,
            language="hi",  # Default to Hindi
        )

        if not transcribed_text.strip():
            await update.message.reply_text(
                "🎤 Could not detect any speech in the audio. Please try a clearer recording."
            )
            return

        await update.message.reply_text(
            f"🎤 *Transcription:*\n_{transcribed_text}_\n\n🔍 Analysing...",
            parse_mode="Markdown",
        )

        # Analyse the transcribed text
        result = await _run_analysis(transcribed_text)

        # Store in context
        _chat_context[chat_id].append({"role": "user", "text": f"[Voice] {transcribed_text}"})
        _chat_context[chat_id].append({
            "role": "bot",
            "verdict": result.verdict.value,
            "fraud_type": result.fraud_type.value,
        })

        response = _format_verdict(result, input_type="voice")
        await update.message.reply_text(response, parse_mode="Markdown")

    except ValueError as e:
        await update.message.reply_text(
            "⚠️ Voice transcription service is not configured. Please set GROQ_API_KEY."
        )
    except Exception as e:
        logger.error(f"Bot voice analysis failed for chat_id={chat_id}: {e}")
        await update.message.reply_text(
            "⚠️ Could not process the voice note. Please try sending it as text instead."
        )


def _is_followup(text: str) -> bool:
    """Check if the message is a follow-up question rather than a new scam to analyse."""
    followup_indicators = [
        "how do i report",
        "how to report",
        "what should i do",
        "is this common",
        "is this type",
        "tell me more",
        "what is",
        "explain",
        "how can i",
        "where to report",
        "rbi",
        "cyber crime",
        "police",
        "?",  # Questions are likely follow-ups
    ]
    text_lower = text.lower()
    # Short messages with question marks are likely follow-ups
    if "?" in text and len(text) < 100:
        return True
    return any(indicator in text_lower for indicator in followup_indicators[:10])


async def _handle_followup(update: Update, text: str, chat_id: int):
    """Handle follow-up questions using chat context."""
    await update.message.chat.send_action("typing")

    # Get previous context
    prev_messages = list(_chat_context[chat_id])
    last_verdict = None
    for msg in reversed(prev_messages):
        if msg.get("role") == "bot" and "verdict" in msg:
            last_verdict = msg
            break

    # Build a contextual response
    text_lower = text.lower()

    if any(w in text_lower for w in ["report", "rbi", "cyber", "police", "complain"]):
        response = (
            "📋 *How to Report Financial Fraud in India:*\n\n"
            "1️⃣ *National Cyber Crime Portal:* cybercrime.gov.in or call 1930\n"
            "2️⃣ *RBI Sachet Portal:* sachet.rbi.org.in\n"
            "3️⃣ *Your Bank:* Call your bank's official helpline immediately\n"
            "4️⃣ *NPCI (for UPI fraud):* npci.org.in/fraud-reporting\n"
            "5️⃣ *Local Police:* File an FIR at your nearest police station\n\n"
            "⏰ *Important:* Report within 24 hours for best chance of recovery!"
        )
    elif any(w in text_lower for w in ["common", "type", "how many", "statistics"]):
        fraud_type = last_verdict.get("fraud_type", "unknown") if last_verdict else "unknown"
        response = (
            f"📊 *About {fraud_type} scams:*\n\n"
            "These scams are extremely common in India. "
            "According to RBI data, UPI fraud cases crossed 95,000+ in FY2024. "
            "Fake KYC and phishing messages account for over 60% of all reported financial frauds.\n\n"
            "Always remember: No bank or government agency will ask for your OTP, PIN, or card details."
        )
    elif any(w in text_lower for w in ["safe", "sure", "trust", "legitimate", "real"]):
        if last_verdict and last_verdict.get("verdict") == "suspicious":
            response = (
                "🚨 *No, this message is NOT safe.*\n\n"
                "Our AI detected multiple red flags. Do NOT:\n"
                "• Click any links in the message\n"
                "• Share OTP, PIN, or card details\n"
                "• Transfer any money\n"
                "• Call numbers mentioned in the message\n\n"
                "Instead, contact your bank directly using the number on your card or their official website."
            )
        else:
            response = (
                "✅ Based on our analysis, this message appears legitimate. "
                "However, always exercise caution — verify through official channels if unsure."
            )
    else:
        response = (
            "I can help you with:\n"
            "• 📋 *Reporting fraud:* Ask 'How do I report this?'\n"
            "• 📊 *Scam statistics:* Ask 'Is this type of scam common?'\n"
            "• 🔍 *New analysis:* Send me another suspicious message\n\n"
            "Or just forward/paste the next suspicious message you want me to check!"
        )

    await update.message.reply_text(response, parse_mode="Markdown")


# ─── Bot Setup ─────────────────────────────────────────────────

def create_bot_application() -> Optional[Application]:
    """Create and configure the Telegram bot application."""
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not set — Telegram bot disabled")
        return None

    app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()

    # Register handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("Telegram bot application created with handlers registered")
    return app
