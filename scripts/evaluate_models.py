"""
VerifPay — Model Evaluation Script

Loads all 5 trained models from app/data/trained_models/ and evaluates
them on a test dataset. Prints accuracy, F1, AUC, and classification
report for each model. Also simulates ensemble majority vote.
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
from collections import Counter

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    roc_auc_score,
    classification_report,
    confusion_matrix,
)
import joblib


# ─── Configuration ──────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent.parent  # project root (verifpay/)
DATA_DIR = BASE_DIR / "app" / "data"
TRAINED_MODELS_DIR = DATA_DIR / "trained_models"
FRAUD_DATASETS_DIR = DATA_DIR / "fraud_datasets"

MODEL_NAMES = [
    "random_forest",
    "svm",
    "gradient_boosting",
    "logistic_regression",
    "naive_bayes",
]

TEST_SIZE = 0.2
RANDOM_STATE = 42


def load_models():
    """Load all trained models and vectorizer."""
    models = {}
    vectorizer_path = TRAINED_MODELS_DIR / "tfidf_vectorizer.pkl"

    if not vectorizer_path.exists():
        raise FileNotFoundError(f"Vectorizer not found at {vectorizer_path}. Run train_models.py first.")

    vectorizer = joblib.load(vectorizer_path)
    print(f"✅ Loaded vectorizer from {vectorizer_path}")

    for name in MODEL_NAMES:
        model_path = TRAINED_MODELS_DIR / f"{name}.pkl"
        if model_path.exists():
            models[name] = joblib.load(model_path)
            print(f"✅ Loaded model: {name}")
        else:
            print(f"⚠️  Model not found: {model_path}")

    return models, vectorizer


def evaluate_models(models: dict, X_test, y_test):
    """Evaluate each model and the ensemble."""
    print(f"\n{'=' * 70}")
    print(f"  {'Model':<25} {'Accuracy':>10} {'F1':>10} {'AUC':>10} {'Precision':>10} {'Recall':>10}")
    print(f"{'─' * 70}")

    all_predictions = []

    for name, model in models.items():
        y_pred = model.predict(X_test)
        y_prob = model.predict_proba(X_test)[:, 1] if hasattr(model, "predict_proba") else y_pred.astype(float)

        acc = accuracy_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred, average="weighted")
        try:
            auc = roc_auc_score(y_test, y_prob)
        except ValueError:
            auc = 0.0

        report = classification_report(y_test, y_pred, output_dict=True)
        precision = report["weighted avg"]["precision"]
        recall = report["weighted avg"]["recall"]

        print(f"  {name:<25} {acc:>10.4f} {f1:>10.4f} {auc:>10.4f} {precision:>10.4f} {recall:>10.4f}")

        all_predictions.append(y_pred)

    # Ensemble (majority vote)
    print(f"{'─' * 70}")
    ensemble_preds = []
    for i in range(len(y_test)):
        votes = [preds[i] for preds in all_predictions]
        majority = Counter(votes).most_common(1)[0][0]
        ensemble_preds.append(majority)
    ensemble_preds = np.array(ensemble_preds)

    acc = accuracy_score(y_test, ensemble_preds)
    f1 = f1_score(y_test, ensemble_preds, average="weighted")
    report = classification_report(y_test, ensemble_preds, output_dict=True)
    precision = report["weighted avg"]["precision"]
    recall = report["weighted avg"]["recall"]

    print(f"  {'ENSEMBLE (majority)':25} {acc:>10.4f} {f1:>10.4f} {'   N/A':>10} {precision:>10.4f} {recall:>10.4f}")
    print(f"{'=' * 70}")

    # Detailed ensemble report
    print(f"\n📊 Ensemble Classification Report:")
    print(classification_report(y_test, ensemble_preds, target_names=["Safe", "Fraud"]))

    # Confusion matrix
    cm = confusion_matrix(y_test, ensemble_preds)
    print(f"📊 Confusion Matrix:")
    print(f"   {'':>15} Predicted Safe  Predicted Fraud")
    print(f"   {'Actual Safe':>15}  {cm[0][0]:>10}  {cm[0][1]:>10}")
    print(f"   {'Actual Fraud':>15}  {cm[1][0]:>10}  {cm[1][1]:>10}")


def main():
    """Main evaluation pipeline."""
    print("=" * 60)
    print("  VerifPay — Model Evaluation")
    print("=" * 60)

    # Load models
    models, vectorizer = load_models()

    if not models:
        print("❌ No models found. Run train_models.py first.")
        sys.exit(1)

    # Load dataset
    if len(sys.argv) > 1:
        csv_path = sys.argv[1]
    else:
        csv_path = str(FRAUD_DATASETS_DIR / "training_data.csv")

    print(f"\n📂 Loading test data from: {csv_path}")
    df = pd.read_csv(csv_path)
    df = df.dropna(subset=["text", "label"])
    df["text"] = df["text"].astype(str).str.strip()
    df["label"] = df["label"].astype(int)

    # Use same split as training to get the test set
    _, X_test_text, _, y_test = train_test_split(
        df["text"], df["label"].values,
        test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=df["label"]
    )

    # Transform text to TF-IDF features
    X_test = vectorizer.transform(X_test_text)
    print(f"   Test samples: {X_test.shape[0]}")

    # Evaluate
    evaluate_models(models, X_test, y_test)

    print("\n✅ Evaluation complete!")


if __name__ == "__main__":
    main()
