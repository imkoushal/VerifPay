"""
VerifPay — ML Ensemble Classifier Service

Loads all 5 trained scikit-learn models and the TF-IDF vectorizer.
Runs majority vote ensemble classification on input text.
Returns structured result with label, confidence, and individual scores.
"""

import logging
import threading
from pathlib import Path
from collections import Counter
from typing import Optional

import numpy as np
import joblib

from app.config import settings
from app.models.schemas import MLClassificationResult, VerdictLabel

logger = logging.getLogger(__name__)

# Model names matching the training script output
MODEL_NAMES = [
    "random_forest",
    "svm",
    "gradient_boosting",
    "logistic_regression",
    "naive_bayes",
]


class MLClassifier:
    """5-model ensemble classifier with majority vote."""

    def __init__(self):
        self.models: dict = {}
        self.vectorizer = None
        self._loaded = False
        self._lock = threading.Lock()

    def load(self) -> bool:
        """Load all trained models and the TF-IDF vectorizer (thread-safe)."""
        with self._lock:
            if self._loaded:
                return True

            models_dir = settings.TRAINED_MODELS_DIR

            # Load vectorizer
            vectorizer_path = models_dir / "tfidf_vectorizer.pkl"
            if not vectorizer_path.exists():
                logger.error(f"Vectorizer not found at {vectorizer_path}")
                return False

            self.vectorizer = joblib.load(vectorizer_path)
            logger.info(f"Loaded TF-IDF vectorizer from {vectorizer_path}")

            # Load each model
            for name in MODEL_NAMES:
                model_path = models_dir / f"{name}.pkl"
                if model_path.exists():
                    self.models[name] = joblib.load(model_path)
                    logger.info(f"Loaded model: {name}")
                else:
                    logger.warning(f"Model not found: {model_path}")

            if not self.models:
                logger.error("No models loaded!")
                return False

            self._loaded = True
            logger.info(f"ML Classifier ready: {len(self.models)} models loaded")
            return True

    def classify(self, text: str) -> MLClassificationResult:
        """
        Classify text using the ensemble of 5 models.

        Returns majority vote label, average confidence, and individual scores.
        """
        if not self._loaded:
            self.load()

        if not self._loaded:
            # Fallback if models failed to load
            logger.error("Models not loaded — returning safe fallback")
            return MLClassificationResult(
                label=VerdictLabel.SAFE,
                confidence=0.0,
                individual_scores={"error": "models_not_loaded"},
            )

        # Transform text to TF-IDF features
        X = self.vectorizer.transform([text])

        # Get predictions from each model
        predictions = {}
        probabilities = {}

        for name, model in self.models.items():
            try:
                pred = model.predict(X)[0]
                predictions[name] = int(pred)

                # Get probability if available
                if hasattr(model, "predict_proba"):
                    prob = model.predict_proba(X)[0]
                    # prob[1] = probability of fraud (label 1)
                    probabilities[name] = float(prob[1])
                else:
                    probabilities[name] = float(pred)

            except Exception as e:
                logger.error(f"Model {name} prediction failed: {e}")
                predictions[name] = 0
                probabilities[name] = 0.0

        # Majority vote
        votes = list(predictions.values())
        vote_counts = Counter(votes)
        majority_label = vote_counts.most_common(1)[0][0]

        # Calculate ensemble confidence using average fraud probability
        avg_fraud_prob = np.mean(list(probabilities.values()))

        # Determine verdict and confidence
        if majority_label == 1:
            verdict = VerdictLabel.SUSPICIOUS
            # Confidence = how confident we are it's fraud
            confidence = max(avg_fraud_prob, 0.5)
        else:
            verdict = VerdictLabel.SAFE
            # Confidence = how confident we are it's safe (inverse of fraud prob)
            confidence = max(1.0 - avg_fraud_prob, 0.5)

        # Build individual scores dict
        individual_scores = {
            name: {
                "prediction": "suspicious" if predictions[name] == 1 else "safe",
                "probability": round(probabilities[name], 4),
            }
            for name in self.models
        }

        result = MLClassificationResult(
            label=verdict,
            confidence=round(confidence, 4),
            individual_scores=individual_scores,
        )

        logger.info(f"Classification: {verdict.value} ({confidence:.2%}) — votes: {dict(vote_counts)}")
        return result


# Global singleton — loaded once and reused across requests
ml_classifier = MLClassifier()

