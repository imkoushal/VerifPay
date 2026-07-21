"""
Health check endpoint for VerifPay.
"""

from fastapi import APIRouter
from app.models.schemas import HealthResponse

router = APIRouter(tags=["System"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.
    Returns service status, version, and LLM provider info.
    """
    return HealthResponse()
