"""
VerifPay Pydantic Schemas
Request/response models for all API endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


# ─── Enums ───────────────────────────────────────────────────────

class VerdictLabel(str, Enum):
    """Classification verdict."""
    SAFE = "safe"
    SUSPICIOUS = "suspicious"


class FraudType(str, Enum):
    """Types of financial fraud detected."""
    PHISHING = "PHISHING"
    FAKE_KYC = "FAKE_KYC"
    UPI_MANIPULATION = "UPI_MANIPULATION"
    CARD_SCAM = "CARD_SCAM"
    OTP_FRAUD = "OTP_FRAUD"
    INVESTMENT_SCAM = "INVESTMENT_SCAM"
    SAFE = "SAFE"


class InputType(str, Enum):
    """Type of input analysed."""
    TEXT = "text"
    URL = "url"
    VOICE = "voice"


# ─── Request Models ─────────────────────────────────────────────

class AnalyseRequest(BaseModel):
    """Request body for POST /analyse."""
    text: str = Field(..., min_length=1, max_length=5000, description="Suspicious message text to analyse")
    url: Optional[str] = Field(None, description="Optional URL to check against phishing databases")



# ─── Response Models ────────────────────────────────────────────

class MLClassificationResult(BaseModel):
    """Result from the ML ensemble classifier."""
    label: VerdictLabel
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0-1")
    individual_scores: dict = Field(default_factory=dict, description="Scores from each model in the ensemble")


class URLCheckResult(BaseModel):
    """Result from URL phishing check."""
    url: str
    is_phishing: bool
    source: str = Field("unknown", description="Which service flagged it (phishtank/google_safe_browsing)")
    threat_type: str = Field("none", description="Type of threat detected")


class FraudExplanation(BaseModel):
    """LLM-generated fraud explanation."""
    fraud_type: FraudType
    explanation: str = Field(..., description="2-3 sentence plain-language explanation")
    red_flags: list[str] = Field(default_factory=list, description="List of specific red flags found")
    recommended_action: str = Field(..., description="Single clear action for the user")
    confidence_reason: str = Field("", description="Why the model is confident in this classification")


class AnalyseResponse(BaseModel):
    """Complete response from POST /analyse."""
    verdict: VerdictLabel
    confidence: float = Field(..., ge=0.0, le=1.0)
    fraud_type: FraudType
    explanation: str
    red_flags: list[str] = Field(default_factory=list)
    recommended_action: str
    confidence_reason: str = ""
    url_checks: list[URLCheckResult] = Field(default_factory=list)
    ml_scores: dict = Field(default_factory=dict, description="Individual model scores from ensemble")
    input_type: InputType = InputType.TEXT


class VoiceAnalyseResponse(BaseModel):
    """Response from POST /voice — includes transcription + analysis."""
    transcribed_text: str
    analysis: AnalyseResponse


class HealthResponse(BaseModel):
    """Response from GET /health."""
    status: str = "ok"
    service: str = "verifpay"
    version: str = "1.0.0"
    llm_provider: str = "groq"
    llm_model: str = "llama-3.3-70b-versatile"


class StatsResponse(BaseModel):
    """Response from GET /stats."""
    total_analyses: int
    suspicious_percentage: float
    top_fraud_types: list[dict]
