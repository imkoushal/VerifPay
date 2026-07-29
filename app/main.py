"""
VerifPay — AI-Powered Financial Fraud & Scam Detection
FastAPI entry point.

Architecture:
    - ML Ensemble (5 models) for binary classification
    - RAG Pipeline (Chroma + MiniLM) for fraud pattern matching
    - Groq Llama 3 for plain-language fraud explanations
    - Groq Whisper for voice transcription
    - PhishTank + Google Safe Browsing for URL checking
    - Telegram Bot for zero-friction user access
"""

import asyncio
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.routers import health, analyse, voice, telegram_webhook
from app.middleware import APIKeyMiddleware, limiter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown events."""
    # ── Startup ────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("  VerifPay — AI Financial Fraud Detection")
    logger.info(f"  LLM Provider: Groq ({settings.GROQ_LLM_MODEL})")
    logger.info(f"  Whisper Model: {settings.GROQ_WHISPER_MODEL}")
    logger.info("=" * 60)

    # Initialize Telegram bot if token is set
    bot_app = None
    polling_task = None
    if settings.TELEGRAM_BOT_TOKEN:
        try:
            from app.services.telegram_bot import create_bot_application
            bot_app = create_bot_application()
            if bot_app:
                # Initialize the bot application
                await bot_app.initialize()

                # Set bot reference in webhook router
                telegram_webhook.set_bot_app(bot_app)

                # Start polling in background (development mode)
                # In production, use webhook mode instead
                await bot_app.start()
                polling_task = asyncio.create_task(
                    bot_app.updater.start_polling(drop_pending_updates=True)
                )
                logger.info("Telegram bot started in polling mode")
        except Exception as e:
            logger.error(f"Failed to start Telegram bot: {e}")
    else:
        logger.info("Telegram bot disabled (TELEGRAM_BOT_TOKEN not set)")

    yield

    # ── Shutdown ───────────────────────────────────────────────
    # Close shared aiohttp session
    from app.services.url_checker import close_session
    await close_session()

    if bot_app:
        try:
            if polling_task:
                await bot_app.updater.stop()
                polling_task.cancel()
            await bot_app.stop()
            await bot_app.shutdown()
            logger.info("Telegram bot stopped")
        except Exception as e:
            logger.error(f"Error stopping Telegram bot: {e}")

    logger.info("VerifPay shutting down...")


app = FastAPI(
    title="VerifPay",
    description="AI-Powered Financial Fraud & Scam Detection for Indian Consumers",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow frontend to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],
)

# API key authentication (disabled if VERIFPAY_API_KEY is empty)
app.add_middleware(APIKeyMiddleware)

# Rate limiting
app.state.limiter = limiter

# Include routers
app.include_router(health.router)
app.include_router(analyse.router)
app.include_router(voice.router)
app.include_router(telegram_webhook.router)


@app.get("/", tags=["System"])
async def root():
    """Root endpoint — redirect info."""
    return {
        "service": "VerifPay",
        "version": "1.0.0",
        "description": "AI-Powered Financial Fraud & Scam Detection",
        "docs": "/docs",
        "health": "/health",
        "telegram_bot": "active" if settings.TELEGRAM_BOT_TOKEN else "disabled",
    }
