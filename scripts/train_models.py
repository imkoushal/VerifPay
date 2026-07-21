"""
VerifPay — 5-Model Ensemble Training Script

Trains a scikit-learn ensemble of 5 models on a CSV dataset with columns:
    - text: str (message content)
    - label: int (0=safe, 1=fraud)

Models trained:
    1. Random Forest
    2. Support Vector Machine (SVM)
    3. Gradient Boosting
    4. Logistic Regression
    5. Naive Bayes (Multinomial)

Each model is saved as a .pkl file in app/data/trained_models/.
Also saves the TF-IDF vectorizer used for feature extraction.
"""

import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score, classification_report
import joblib


# ─── Configuration ──────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent.parent  # project root (verifpay/)
DATA_DIR = BASE_DIR / "app" / "data"
TRAINED_MODELS_DIR = DATA_DIR / "trained_models"
FRAUD_DATASETS_DIR = DATA_DIR / "fraud_datasets"

# TF-IDF parameters
MAX_FEATURES = 10000
NGRAM_RANGE = (1, 2)  # unigrams + bigrams for better fraud pattern capture

# Train/test split
TEST_SIZE = 0.2
RANDOM_STATE = 42


# ─── Model Definitions ────────────────────────────────────────

MODELS = {
    "random_forest": RandomForestClassifier(
        n_estimators=200,
        max_depth=50,
        min_samples_split=5,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=RANDOM_STATE,
        n_jobs=-1,
    ),
    "svm": SVC(
        kernel="linear",
        C=1.0,
        class_weight="balanced",
        probability=True,
        random_state=RANDOM_STATE,
    ),
    "gradient_boosting": GradientBoostingClassifier(
        n_estimators=200,
        learning_rate=0.1,
        max_depth=5,
        min_samples_split=5,
        random_state=RANDOM_STATE,
    ),
    "logistic_regression": LogisticRegression(
        C=1.0,
        class_weight="balanced",
        max_iter=1000,
        random_state=RANDOM_STATE,
    ),
    "naive_bayes": MultinomialNB(
        alpha=0.1,
    ),
}


def load_dataset(csv_path: str) -> pd.DataFrame:
    """Load and validate the training dataset."""
    print(f"\n📂 Loading dataset from: {csv_path}")

    df = pd.read_csv(csv_path)

    # Validate required columns
    required_cols = {"text", "label"}
    if not required_cols.issubset(df.columns):
        raise ValueError(f"Dataset must have columns: {required_cols}. Found: {set(df.columns)}")

    # Clean data
    df = df.dropna(subset=["text", "label"])
    df["text"] = df["text"].astype(str).str.strip()
    df["label"] = df["label"].astype(int)
    df = df[df["text"].str.len() > 0]

    print(f"   Total samples: {len(df)}")
    print(f"   Safe (0):      {len(df[df['label'] == 0])}")
    print(f"   Fraud (1):     {len(df[df['label'] == 1])}")
    print(f"   Fraud ratio:   {df['label'].mean():.1%}")

    return df


def build_features(texts: pd.Series, vectorizer: TfidfVectorizer = None, fit: bool = True):
    """Build TF-IDF feature matrix."""
    if fit:
        vectorizer = TfidfVectorizer(
            max_features=MAX_FEATURES,
            ngram_range=NGRAM_RANGE,
            stop_words="english",
            sublinear_tf=True,
            strip_accents="unicode",
        )
        X = vectorizer.fit_transform(texts)
        print(f"\n🔤 TF-IDF features: {X.shape[1]} features from {X.shape[0]} samples")
    else:
        X = vectorizer.transform(texts)

    return X, vectorizer


def train_all_models(X_train, y_train, X_test, y_test):
    """Train all 5 models and evaluate them."""
    results = {}

    for name, model in MODELS.items():
        print(f"\n{'─' * 50}")
        print(f"🤖 Training: {name}")
        print(f"{'─' * 50}")

        # Train
        model.fit(X_train, y_train)

        # Predict
        y_pred = model.predict(X_test)
        y_prob = model.predict_proba(X_test)[:, 1] if hasattr(model, "predict_proba") else y_pred.astype(float)

        # Metrics
        acc = accuracy_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred, average="weighted")
        try:
            auc = roc_auc_score(y_test, y_prob)
        except ValueError:
            auc = 0.0

        results[name] = {
            "model": model,
            "accuracy": acc,
            "f1_score": f1,
            "auc_roc": auc,
        }

        print(f"   Accuracy:  {acc:.4f}")
        print(f"   F1 Score:  {f1:.4f}")
        print(f"   AUC-ROC:   {auc:.4f}")

    return results


def save_models(results: dict, vectorizer: TfidfVectorizer):
    """Save all trained models and the vectorizer as .pkl files."""
    TRAINED_MODELS_DIR.mkdir(parents=True, exist_ok=True)

    # Save vectorizer
    vectorizer_path = TRAINED_MODELS_DIR / "tfidf_vectorizer.pkl"
    joblib.dump(vectorizer, vectorizer_path)
    print(f"\n💾 Saved vectorizer: {vectorizer_path}")

    # Save each model
    for name, data in results.items():
        model_path = TRAINED_MODELS_DIR / f"{name}.pkl"
        joblib.dump(data["model"], model_path)
        print(f"💾 Saved model:      {model_path}")

    print(f"\n✅ All {len(results)} models + vectorizer saved to {TRAINED_MODELS_DIR}")


def main():
    """Main training pipeline."""
    print("=" * 60)
    print("  VerifPay — 5-Model Ensemble Training")
    print("=" * 60)

    # Determine dataset path
    if len(sys.argv) > 1:
        csv_path = sys.argv[1]
    else:
        csv_path = str(FRAUD_DATASETS_DIR / "training_data.csv")

    # Load data
    df = load_dataset(csv_path)

    # Build features
    X, vectorizer = build_features(df["text"])
    y = df["label"].values

    # Split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y
    )
    print(f"\n📊 Train: {X_train.shape[0]} | Test: {X_test.shape[0]}")

    # Train all models
    results = train_all_models(X_train, y_train, X_test, y_test)

    # Summary table
    print(f"\n{'=' * 60}")
    print(f"  {'Model':<25} {'Accuracy':>10} {'F1':>10} {'AUC':>10}")
    print(f"{'─' * 60}")
    for name, data in results.items():
        print(f"  {name:<25} {data['accuracy']:>10.4f} {data['f1_score']:>10.4f} {data['auc_roc']:>10.4f}")
    print(f"{'=' * 60}")

    # Best model
    best = max(results.items(), key=lambda x: x[1]["f1_score"])
    print(f"\n🏆 Best model: {best[0]} (F1: {best[1]['f1_score']:.4f})")

    # Save
    save_models(results, vectorizer)
    print("\n🎉 Training complete! Models ready for inference.")


if __name__ == "__main__":
    main()
