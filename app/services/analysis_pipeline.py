"""
VerifPay — Shared Analysis Pipeline

Single source of truth for the fraud detection pipeline.
Used by both the /analyse endpoint and the Telegram bot.

Pipeline:
    1. URL Extraction + Parallel URL checking
    2. ML Ensemble Classifier
    3. RAG Retriever
    4. Groq Llama 3 Explainer
    5. Build final response
"""

import logging

from app.models.schemas import (
    AnalyseResponse,
    VerdictLabel,
    FraudType,
    InputType,
)
from app.services.ml_classifier import ml_classifier
from app.services.rag_retriever import rag_retriever
from app.services.fraud_explainer import fraud_explainer
from app.services.url_checker import extract_urls, check_urls

logger = logging.getLogger(__name__)


async def run_analysis(text: str, explicit_url: str = None) -> AnalyseResponse:
    """
    Run the full 4-stage fraud detection pipeline.

    Args:
        text: Suspicious message text to analyse
        explicit_url: Optional URL to check in addition to extracted URLs

    Returns:
        AnalyseResponse with verdict, explanation, red flags, and action
    """
    # ── Step 1: URL Extraction + Checking ──────────────────────
    url_results = []
    try:
        urls = extract_urls(text)
        if explicit_url and explicit_url not in urls:
            urls.append(explicit_url)

        if urls:
            logger.info(f"Found {len(urls)} URL(s): {urls}")
            url_results = await check_urls(urls)
            logger.info(f"URL check results: {[(r.url, r.is_phishing, r.source) for r in url_results]}")
    except Exception as e:
        logger.error(f"URL checking failed: {e}")

    # ── Step 2: ML Classification ──────────────────────────────
    try:
        ml_result = ml_classifier.classify(text)
        logger.info(f"ML verdict: {ml_result.label.value} ({ml_result.confidence:.2%})")
    except Exception as e:
        logger.error(f"ML classification failed: {e}")
        ml_result = None

    # ── Step 3: RAG Retrieval ──────────────────────────────────
    try:
        retrieved_patterns = rag_retriever.retrieve_fraud_patterns(text, top_k=5)
        logger.info(f"RAG retrieved: {len(retrieved_patterns)} patterns")
    except Exception as e:
        logger.error(f"RAG retrieval failed: {e}")
        retrieved_patterns = []

    # ── Step 4: LLM Explanation (Groq Llama 3) ─────────────────
    try:
        ml_verdict = ml_result.label.value if ml_result else "unknown"
        ml_confidence = ml_result.confidence if ml_result else 0.0

        url_results_dicts = [
            {
                "url": r.url,
                "is_phishing": r.is_phishing,
                "source": r.source,
                "threat_type": r.threat_type,
            }
            for r in url_results
        ] if url_results else None

        explanation = await fraud_explainer.explain(
            text=text,
            ml_verdict=ml_verdict,
            ml_confidence=ml_confidence,
            retrieved_patterns=retrieved_patterns,
            url_results=url_results_dicts,
        )
        logger.info(f"LLM explanation: {explanation.fraud_type.value}")
    except Exception as e:
        logger.error(f"LLM explanation failed: {e}")
        explanation = None

    # ── Build Response ─────────────────────────────────────────
    response = build_response(ml_result, explanation, url_results)
    logger.info(f"Final verdict: {response.verdict.value} | Type: {response.fraud_type.value} | Confidence: {response.confidence:.2%}")

    return response


def build_response(ml_result, explanation, url_results) -> AnalyseResponse:
    """
    Build the final AnalyseResponse from pipeline results.
    Uses LLM explanation as primary, ML result as fallback.
    URL phishing results can override verdict to suspicious.
    """
    # Check if any URL was flagged as phishing
    any_url_phishing = any(r.is_phishing for r in url_results) if url_results else False

    # Case 1: Both ML and LLM available (ideal)
    if ml_result and explanation:
        verdict = ml_result.label

        # If LLM says it's a specific fraud type but ML says safe, trust LLM
        if explanation.fraud_type != FraudType.SAFE and verdict == VerdictLabel.SAFE:
            verdict = VerdictLabel.SUSPICIOUS

        # If URL checker found phishing, override to suspicious
        if any_url_phishing and verdict == VerdictLabel.SAFE:
            verdict = VerdictLabel.SUSPICIOUS

        return AnalyseResponse(
            verdict=verdict,
            confidence=ml_result.confidence,
            fraud_type=explanation.fraud_type,
            explanation=explanation.explanation,
            red_flags=explanation.red_flags,
            recommended_action=explanation.recommended_action,
            confidence_reason=explanation.confidence_reason,
            url_checks=url_results or [],
            ml_scores=ml_result.individual_scores,
            input_type=InputType.TEXT,
        )

    # Case 2: Only ML available (LLM failed)
    if ml_result:
        fraud_type = FraudType.PHISHING if ml_result.label == VerdictLabel.SUSPICIOUS else FraudType.SAFE

        # URL override
        verdict = ml_result.label
        if any_url_phishing and verdict == VerdictLabel.SAFE:
            verdict = VerdictLabel.SUSPICIOUS
            fraud_type = FraudType.PHISHING

        return AnalyseResponse(
            verdict=verdict,
            confidence=ml_result.confidence,
            fraud_type=fraud_type,
            explanation="ML models classified this message. AI explanation temporarily unavailable.",
            red_flags=["Automated detection flagged this message"] if verdict == VerdictLabel.SUSPICIOUS else [],
            recommended_action="Exercise caution. Do not click links or share personal details." if verdict == VerdictLabel.SUSPICIOUS else "Message appears safe.",
            confidence_reason="Based on ML classification only.",
            url_checks=url_results or [],
            ml_scores=ml_result.individual_scores,
            input_type=InputType.TEXT,
        )

    # Case 3: Only LLM available (ML failed)
    if explanation:
        verdict = VerdictLabel.SUSPICIOUS if explanation.fraud_type != FraudType.SAFE else VerdictLabel.SAFE
        if any_url_phishing:
            verdict = VerdictLabel.SUSPICIOUS

        return AnalyseResponse(
            verdict=verdict,
            confidence=0.7 if verdict == VerdictLabel.SUSPICIOUS else 0.6,
            fraud_type=explanation.fraud_type,
            explanation=explanation.explanation,
            red_flags=explanation.red_flags,
            recommended_action=explanation.recommended_action,
            confidence_reason=explanation.confidence_reason,
            url_checks=url_results or [],
            ml_scores={},
            input_type=InputType.TEXT,
        )

    # Case 4: Both failed — check URLs as last resort
    if any_url_phishing:
        return AnalyseResponse(
            verdict=VerdictLabel.SUSPICIOUS,
            confidence=0.8,
            fraud_type=FraudType.PHISHING,
            explanation="A phishing URL was detected in this message. Do not click the link.",
            red_flags=["Contains known phishing URL"],
            recommended_action="Do not click any links. Report the message to your bank.",
            confidence_reason="URL flagged by phishing database.",
            url_checks=url_results or [],
            ml_scores={},
            input_type=InputType.TEXT,
        )

    # Absolute fallback
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
