"""
VerifPay — Fraud Explainer Service (Groq Llama 3)

Calls Groq API with llama-3.3-70b-versatile to generate plain-language
fraud explanations. Receives ML verdict + RAG patterns + original text
and returns structured JSON with fraud type, explanation, red flags,
and recommended action.
"""

import asyncio
import json
import logging
from typing import Optional

from groq import Groq

from app.config import settings
from app.models.schemas import FraudExplanation, FraudType

logger = logging.getLogger(__name__)

# ─── System Prompt ─────────────────────────────────────────────

SYSTEM_PROMPT = """
You are VerifPay, an AI fraud detection expert specializing in
Indian financial scams, UPI fraud, and digital payment deception.

Your job is to analyze suspicious messages and explain clearly
why they are fraudulent or safe. Always respond in simple,
clear English that any Indian consumer can understand.

When analyzing a message:
1. Identify the exact fraud type if suspicious
2. List specific red flags in the message
3. Explain in 2-3 simple sentences why it is suspicious
4. Give one clear recommended action

Fraud types to classify:
- PHISHING: Fake links designed to steal credentials
- FAKE_KYC: Fake KYC expiry threats from fake banks/TRAI
- UPI_MANIPULATION: Fake UPI payment requests or collect requests
- CARD_SCAM: Fake credit/debit card offers or threat messages
- OTP_FRAUD: Messages trying to extract OTP
- INVESTMENT_SCAM: Fake investment or lottery schemes
- SAFE: Message appears legitimate

Always respond in this exact JSON format:
{
  "fraud_type": "FRAUD_TYPE_HERE",
  "explanation": "2-3 sentence explanation here",
  "red_flags": ["flag 1", "flag 2", "flag 3"],
  "recommended_action": "Single clear action for the user",
  "confidence_reason": "One sentence why you are confident"
}

Never invent information. Only use what is in the message.
If unsure, classify as SAFE and explain your uncertainty.
"""


class FraudExplainer:
    """Groq Llama 3 powered fraud explanation generator."""

    def __init__(self):
        self._client: Optional[Groq] = None

    def _get_client(self) -> Groq:
        """Lazy-initialize the Groq client."""
        if self._client is None:
            if not settings.GROQ_API_KEY:
                raise ValueError("GROQ_API_KEY not set in environment variables")
            self._client = Groq(api_key=settings.GROQ_API_KEY)
        return self._client

    async def explain(
        self,
        text: str,
        ml_verdict: str = "unknown",
        ml_confidence: float = 0.0,
        retrieved_patterns: list[dict] = None,
        url_results: list[dict] = None,
    ) -> FraudExplanation:
        """
        Generate a fraud explanation using Groq Llama 3.
        Runs the synchronous Groq SDK call in a thread to avoid blocking the event loop.

        Args:
            text: Original suspicious message text
            ml_verdict: ML classifier verdict (safe/suspicious)
            ml_confidence: ML classifier confidence score
            retrieved_patterns: RAG-retrieved similar fraud patterns
            url_results: URL checking results (if any URLs found)

        Returns:
            FraudExplanation with fraud type, explanation, red flags, and action
        """
        return await asyncio.to_thread(
            self._explain_sync, text, ml_verdict, ml_confidence,
            retrieved_patterns, url_results,
        )

    def _explain_sync(
        self,
        text: str,
        ml_verdict: str = "unknown",
        ml_confidence: float = 0.0,
        retrieved_patterns: list[dict] = None,
        url_results: list[dict] = None,
    ) -> FraudExplanation:
        """
        Generate a fraud explanation using Groq Llama 3.

        Args:
            text: Original suspicious message text
            ml_verdict: ML classifier verdict (safe/suspicious)
            ml_confidence: ML classifier confidence score
            retrieved_patterns: RAG-retrieved similar fraud patterns
            url_results: URL checking results (if any URLs found)

        Returns:
            FraudExplanation with fraud type, explanation, red flags, and action
        """
        # Build the user prompt with all available context
        user_prompt = self._build_prompt(
            text, ml_verdict, ml_confidence, retrieved_patterns, url_results
        )

        try:
            client = self._get_client()

            response = client.chat.completions.create(
                model=settings.GROQ_LLM_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,  # Low temperature for consistent, factual output
                max_tokens=settings.GROQ_MAX_TOKENS,
                response_format={"type": "json_object"},
            )

            # Parse the JSON response
            content = response.choices[0].message.content
            result = json.loads(content)

            # Validate and map fraud type
            fraud_type = self._parse_fraud_type(result.get("fraud_type", "SAFE"))

            explanation = FraudExplanation(
                fraud_type=fraud_type,
                explanation=result.get("explanation", "Unable to determine fraud status."),
                red_flags=result.get("red_flags", []),
                recommended_action=result.get("recommended_action", "Exercise caution with this message."),
                confidence_reason=result.get("confidence_reason", ""),
            )

            logger.info(f"LLM explanation: {fraud_type.value} — {explanation.explanation[:80]}...")
            return explanation

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {e}")
            return self._fallback_explanation(text, ml_verdict)

        except Exception as e:
            logger.error(f"Groq API call failed: {e}")
            return self._fallback_explanation(text, ml_verdict)

    def _build_prompt(
        self,
        text: str,
        ml_verdict: str,
        ml_confidence: float,
        retrieved_patterns: list[dict] = None,
        url_results: list[dict] = None,
    ) -> str:
        """Build the user prompt with all context for the LLM."""
        prompt_parts = [
            f"Analyze this message for financial fraud:\n\n\"{text}\"",
            f"\nML Classification Result: {ml_verdict.upper()} (confidence: {ml_confidence:.1%})",
        ]

        # Add RAG context if available
        if retrieved_patterns:
            patterns_text = "\n".join([
                f"- [{p['fraud_type']}] {p['content'][:200]}"
                for p in retrieved_patterns[:3]  # Top 3 most relevant
            ])
            prompt_parts.append(f"\nSimilar known fraud patterns from database:\n{patterns_text}")

        # Add URL check results if available
        if url_results:
            url_text = "\n".join([
                f"- URL: {u.get('url', 'unknown')} — {'PHISHING DETECTED' if u.get('is_phishing') else 'Clean'} (source: {u.get('source', 'unknown')})"
                for u in url_results
            ])
            prompt_parts.append(f"\nURL Check Results:\n{url_text}")

        prompt_parts.append("\nProvide your analysis in the required JSON format.")

        return "\n".join(prompt_parts)

    def _parse_fraud_type(self, fraud_type_str: str) -> FraudType:
        """Parse fraud type string to enum, handling edge cases."""
        fraud_type_str = fraud_type_str.upper().strip()

        # Direct mapping
        type_map = {
            "PHISHING": FraudType.PHISHING,
            "FAKE_KYC": FraudType.FAKE_KYC,
            "UPI_MANIPULATION": FraudType.UPI_MANIPULATION,
            "CARD_SCAM": FraudType.CARD_SCAM,
            "OTP_FRAUD": FraudType.OTP_FRAUD,
            "INVESTMENT_SCAM": FraudType.INVESTMENT_SCAM,
            "SAFE": FraudType.SAFE,
        }

        if fraud_type_str in type_map:
            return type_map[fraud_type_str]

        # Fuzzy matching for common LLM variations
        if "PHISH" in fraud_type_str:
            return FraudType.PHISHING
        if "KYC" in fraud_type_str:
            return FraudType.FAKE_KYC
        if "UPI" in fraud_type_str:
            return FraudType.UPI_MANIPULATION
        if "CARD" in fraud_type_str:
            return FraudType.CARD_SCAM
        if "OTP" in fraud_type_str:
            return FraudType.OTP_FRAUD
        if "INVEST" in fraud_type_str or "LOTTERY" in fraud_type_str or "PONZI" in fraud_type_str:
            return FraudType.INVESTMENT_SCAM

        return FraudType.SAFE

    def _fallback_explanation(self, text: str, ml_verdict: str) -> FraudExplanation:
        """Generate a fallback explanation when LLM fails."""
        if ml_verdict.lower() == "suspicious":
            return FraudExplanation(
                fraud_type=FraudType.PHISHING,
                explanation="Our ML models flagged this message as suspicious. The AI explanation service is temporarily unavailable, but please exercise caution.",
                red_flags=["Message flagged by automated fraud detection system"],
                recommended_action="Do not click any links or share personal information. Contact your bank directly using their official helpline.",
                confidence_reason="Based on ML classification only — LLM explanation unavailable.",
            )
        else:
            return FraudExplanation(
                fraud_type=FraudType.SAFE,
                explanation="Our ML models indicate this message appears safe. However, always exercise caution with financial messages.",
                red_flags=[],
                recommended_action="Message appears legitimate, but verify through official channels if unsure.",
                confidence_reason="Based on ML classification only — LLM explanation unavailable.",
            )


# Global singleton
fraud_explainer = FraudExplainer()
