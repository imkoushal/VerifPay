"""
POST /analyse — Core Fraud Detection Endpoint

Chains the analysis pipeline:
    1. ML Ensemble Classifier → binary classification + confidence
    2. RAG Retriever → similar known fraud patterns from ChromaDB
    3. Groq Llama 3 Explainer → plain-language fraud explanation

Returns complete verdict with explanation, red flags, and recommended action.
Handles errors gracefully — if any service fails, returns a safe fallback.
"""

import logging
from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    AnalyseRequest,
    AnalyseResponse,
    VerdictLabel,
    FraudType,
    InputType,
)
from app.services.ml_classifier import ml_classifier
from app.services.rag_retriever import rag_retriever
from app.services.fraud_explainer import fraud_explainer

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Analysis"])


@router.post("/analyse", response_model=AnalyseResponse)
async def analyse_text(request: AnalyseRequest):
    """
    Analyse suspicious text for financial fraud.

    Pipeline:
        1. ML ensemble classifies text as safe/suspicious
        2. RAG retrieves similar known fraud patterns
        3. Groq Llama 3 generates explanation with context

    Returns complete verdict with confidence, fraud type,
    explanation, red flags, and recommended action.
    """
    text = request.text.strip()
    logger.info(f"Analyse request: {text[:100]}...")

    # ── Step 1: ML Classification ──────────────────────────────
    try:
        ml_result = ml_classifier.classify(text)
        logger.info(f"ML verdict: {ml_result.label.value} ({ml_result.confidence:.2%})")
    except Exception as e:
        logger.error(f"ML classification failed: {e}")
        ml_result = None

    # ── Step 2: RAG Retrieval ──────────────────────────────────
    try:
        retrieved_patterns = rag_retriever.retrieve_fraud_patterns(text, top_k=5)
        logger.info(f"RAG retrieved: {len(retrieved_patterns)} patterns")
    except Exception as e:
        logger.error(f"RAG retrieval failed: {e}")
        retrieved_patterns = []

    # ── Step 3: LLM Explanation (Groq Llama 3) ─────────────────
    try:
        ml_verdict = ml_result.label.value if ml_result else "unknown"
        ml_confidence = ml_result.confidence if ml_result else 0.0

        explanation = fraud_explainer.explain(
            text=text,
            ml_verdict=ml_verdict,
            ml_confidence=ml_confidence,
            retrieved_patterns=retrieved_patterns,
            url_results=None,  # Phase 3: URL checking
        )
        logger.info(f"LLM explanation: {explanation.fraud_type.value}")
    except Exception as e:
        logger.error(f"LLM explanation failed: {e}")
        explanation = None

    # ── Build Response ─────────────────────────────────────────
    response = _build_response(ml_result, explanation, retrieved_patterns)
    logger.info(f"Final verdict: {response.verdict.value} | Type: {response.fraud_type.value} | Confidence: {response.confidence:.2%}")

    return response


def _build_response(ml_result, explanation, retrieved_patterns) -> AnalyseResponse:
    """
    Build the final AnalyseResponse from pipeline results.
    Uses LLM explanation as primary, ML result as fallback.
    """
    # Case 1: Both ML and LLM available (ideal)
    if ml_result and explanation:
        # Trust LLM for fraud_type and explanation
        # Trust ML for confidence score
        verdict = ml_result.label
        # If LLM says it's a specific fraud type (not SAFE) but ML says safe,
        # lean towards suspicious (LLM has more context)
        if explanation.fraud_type != FraudType.SAFE and verdict == VerdictLabel.SAFE:
            verdict = VerdictLabel.SUSPICIOUS

        return AnalyseResponse(
            verdict=verdict,
            confidence=ml_result.confidence,
            fraud_type=explanation.fraud_type,
            explanation=explanation.explanation,
            red_flags=explanation.red_flags,
            recommended_action=explanation.recommended_action,
            confidence_reason=explanation.confidence_reason,
            url_checks=[],
            ml_scores=ml_result.individual_scores,
            input_type=InputType.TEXT,
        )

    # Case 2: Only ML available (LLM failed)
    if ml_result:
        fraud_type = FraudType.PHISHING if ml_result.label == VerdictLabel.SUSPICIOUS else FraudType.SAFE
        return AnalyseResponse(
            verdict=ml_result.label,
            confidence=ml_result.confidence,
            fraud_type=fraud_type,
            explanation="ML models classified this message. AI explanation temporarily unavailable.",
            red_flags=["Automated detection flagged this message"] if ml_result.label == VerdictLabel.SUSPICIOUS else [],
            recommended_action="Exercise caution. Do not click links or share personal details." if ml_result.label == VerdictLabel.SUSPICIOUS else "Message appears safe.",
            confidence_reason="Based on ML classification only.",
            url_checks=[],
            ml_scores=ml_result.individual_scores,
            input_type=InputType.TEXT,
        )

    # Case 3: Only LLM available (ML failed)
    if explanation:
        verdict = VerdictLabel.SUSPICIOUS if explanation.fraud_type != FraudType.SAFE else VerdictLabel.SAFE
        return AnalyseResponse(
            verdict=verdict,
            confidence=0.7 if verdict == VerdictLabel.SUSPICIOUS else 0.6,
            fraud_type=explanation.fraud_type,
            explanation=explanation.explanation,
            red_flags=explanation.red_flags,
            recommended_action=explanation.recommended_action,
            confidence_reason=explanation.confidence_reason,
            url_checks=[],
            ml_scores={},
            input_type=InputType.TEXT,
        )

    # Case 4: Both failed — safe fallback
    return AnalyseResponse(
        verdict=VerdictLabel.SAFE,
        confidence=0.5,
        fraud_type=FraudType.SAFE,
        explanation="Unable to analyse this message at the moment. Please try again.",
        red_flags=[],
        recommended_action="Exercise caution with any financial message. Contact your bank directly if unsure.",
        confidence_reason="Analysis services temporarily unavailable.",
        url_checks=[],
        ml_scores={},
        input_type=InputType.TEXT,
    )
