"""
VerifPay Configuration
Loads environment variables and provides centralized config access.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


class Settings:
    """Application settings loaded from environment variables."""

    # Groq API - used for both Llama 3 (fraud explanation) and Whisper (voice transcription)
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_LLM_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_WHISPER_MODEL: str = "whisper-large-v3"
    GROQ_MAX_TOKENS: int = 800

    # Telegram Bot
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")

    # URL Checking APIs
    PHISHTANK_API_KEY: str = os.getenv("PHISHTANK_API_KEY", "")
    GOOGLE_SAFE_BROWSING_API_KEY: str = os.getenv("GOOGLE_SAFE_BROWSING_API_KEY", "")

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://verifpay:verifpay@localhost:5432/verifpay")

    # ChromaDB
    CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")

    # Embedding Model
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"

    # Frontend URL for CORS
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")

    # API Security
    VERIFPAY_API_KEY: str = os.getenv("VERIFPAY_API_KEY", "")
    RATE_LIMIT: str = "30/minute"

    # Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATA_DIR: Path = BASE_DIR / "app" / "data"
    TRAINED_MODELS_DIR: Path = DATA_DIR / "trained_models"
    FRAUD_DATASETS_DIR: Path = DATA_DIR / "fraud_datasets"
    RBI_ALERTS_DIR: Path = DATA_DIR / "rbi_alerts"
    INDIA_PATTERNS_DIR: Path = DATA_DIR / "india_patterns"


settings = Settings()
