"""
Phase 2 Comprehensive Validation — Tests ML + RAG pipeline with 10 real scam messages.
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")

from app.services.ml_classifier import ml_classifier
from app.services.rag_retriever import rag_retriever

# 10 test messages — 5 scam, 5 legitimate
TEST_MESSAGES = [
    # SCAM messages
    ("Your SBI account KYC has expired. Update at http://sbi-kyc.xyz or account blocked in 24hrs.", True, "FAKE_KYC"),
    ("TRAI has decided to disconnect your mobile in 2 hours due to illegal activity. Press 1 to speak to officer.", True, "FAKE_KYC"),
    ("Congratulations! You won Rs 50 lakh in Amazon Lucky Draw. Claim at http://amazon-prize.tk", True, "INVESTMENT_SCAM"),
    ("Your UPI ID selected for Rs 10000 cashback. Send Rs 100 to verify your account.", True, "UPI_MANIPULATION"),
    ("Income Tax refund of Rs 15000 pending. Click http://incometax-refund.in to process instantly.", True, "PHISHING"),
    # SAFE messages
    ("Your OTP for SBI Net Banking is 834521. Do not share this OTP with anyone. Valid for 5 minutes.", False, "SAFE"),
    ("HDFC Bank: Your account XX1234 credited with Rs 25000.00 on 15-Jul. Balance: Rs 1,23,456.78", False, "SAFE"),
    ("Amazon: Your order #123-4567890 shipped. Delivery by Jul 18. Track at amazon.in/orders", False, "SAFE"),
    ("Swiggy: Your order from Dominos is on the way! Estimated delivery in 25 minutes.", False, "SAFE"),
    ("Zerodha: Your equity order for 10 shares of RELIANCE at Rs 2450 has been executed.", False, "SAFE"),
]

print("=" * 70)
print("  VerifPay Phase 2 — Comprehensive Validation (10 messages)")
print("=" * 70)

correct = 0
total = len(TEST_MESSAGES)

for i, (text, is_scam, expected_type) in enumerate(TEST_MESSAGES):
    # ML classification
    ml_result = ml_classifier.classify(text)
    ml_is_scam = ml_result.label.value == "suspicious"

    # RAG retrieval
    patterns = rag_retriever.retrieve_fraud_patterns(text, top_k=3)
    top_type = patterns[0]["fraud_type"] if patterns else "NONE"
    top_rel = patterns[0]["relevance_score"] if patterns else 0.0

    # Check correctness
    is_correct = ml_is_scam == is_scam
    if is_correct:
        correct += 1

    status = "PASS" if is_correct else "FAIL"
    expected = "SCAM" if is_scam else "SAFE"
    got = "SCAM" if ml_is_scam else "SAFE"

    print(f"\n{'─' * 70}")
    print(f"  [{status}] Test {i+1}: {text[:70]}...")
    print(f"  Expected: {expected} | Got: {got} | Confidence: {ml_result.confidence:.1%}")
    print(f"  RAG top match: [{top_type}] relevance={top_rel:.0%}")

print(f"\n{'=' * 70}")
print(f"  Results: {correct}/{total} correct ({correct/total:.0%} accuracy)")
print(f"{'=' * 70}")

if correct == total:
    print("\n  PHASE 2 VALIDATION: ALL TESTS PASSED")
else:
    print(f"\n  PHASE 2 VALIDATION: {total - correct} test(s) failed")
