"""
VerifPay — AI-Powered Financial Fraud & Scam Detection
FastAPI entry point.

Architecture:
    - ML Ensemble (5 models) for binary classification
    - RAG Pipeline (Chroma + MiniLM) for fraud pattern matching
    - Groq Llama 3 for plain-language fraud explanations
    - Groq Whisper for voice transcription
    - PhishTank + Google Safe Browsing for URL checking
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.routers import health, analyse, voice, telegram_webhook


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown events."""
    # Startup
    print("=" * 60)
    print("  VerifPay — AI Financial Fraud Detection")
    print(f"  LLM Provider: Groq ({settings.GROQ_LLM_MODEL})")
    print(f"  Whisper Model: {settings.GROQ_WHISPER_MODEL}")
    print("=" * 60)
    yield
    # Shutdown
    print("VerifPay shutting down...")


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
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    }
