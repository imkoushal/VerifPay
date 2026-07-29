"""
POST /analyse — Core Fraud Detection Endpoint

Delegates to the shared analysis pipeline in services/analysis_pipeline.py.
Returns complete verdict with explanation, red flags, and recommended action.
"""

import logging
from fastapi import APIRouter

from app.models.schemas import AnalyseRequest, AnalyseResponse
from app.services.analysis_pipeline import run_analysis

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Analysis"])


@router.post("/analyse", response_model=AnalyseResponse)
async def analyse_text(request: AnalyseRequest):
    """
    Analyse suspicious text for financial fraud.

    Pipeline:
        1. Extract URLs and check against phishing databases
        2. ML ensemble classifies text as safe/suspicious
        3. RAG retrieves similar known fraud patterns
        4. Groq Llama 3 generates explanation with full context

    Returns complete verdict with confidence, fraud type,
    explanation, red flags, and recommended action.
    """
    text = request.text.strip()
    logger.info(f"Analyse request: {text[:100]}...")

    response = await run_analysis(text=text, explicit_url=request.url)
    return response
