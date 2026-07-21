"""Phase 4 Validation — Tests bot endpoints and existing pipeline still works."""
import sys
sys.stdout.reconfigure(encoding="utf-8")

import httpx
import json

BASE = "http://127.0.0.1:8000"

print("=" * 70)
print("  VerifPay Phase 4 — Telegram Bot Validation")
print("=" * 70)

passed = 0
total = 0

# ── Test 1: Health check ─────────────────────────────────────
total += 1
print("\n── Test 1: Health check ──")
r = httpx.get(f"{BASE}/health")
d = r.json()
print(f"   {r.status_code} | {d}")
if r.status_code == 200 and d["status"] == "ok":
    print("   ✅ PASS")
    passed += 1
else:
    print("   ❌ FAIL")

# ── Test 2: Root endpoint shows bot status ───────────────────
total += 1
print("\n── Test 2: Root endpoint shows telegram_bot status ──")
r = httpx.get(f"{BASE}/")
d = r.json()
print(f"   {r.status_code} | telegram_bot={d.get('telegram_bot')}")
if r.status_code == 200 and "telegram_bot" in d:
    print("   ✅ PASS")
    passed += 1
else:
    print("   ❌ FAIL")

# ── Test 3: Webhook status endpoint ──────────────────────────
total += 1
print("\n── Test 3: Webhook status endpoint ──")
r = httpx.get(f"{BASE}/webhook/telegram/status")
d = r.json()
print(f"   {r.status_code} | {d}")
if r.status_code == 200 and "status" in d:
    print("   ✅ PASS")
    passed += 1
else:
    print("   ❌ FAIL")

# ── Test 4: Webhook POST without bot returns 503 ────────────
total += 1
print("\n── Test 4: Webhook POST (bot not active) ──")
r = httpx.post(f"{BASE}/webhook/telegram", json={"update_id": 123})
print(f"   {r.status_code}")
if r.status_code == 503:
    print("   ✅ PASS — correctly returns 503 when bot not initialized")
    passed += 1
elif r.status_code == 200:
    print("   ✅ PASS — bot is initialized")
    passed += 1
else:
    print(f"   ❌ FAIL — unexpected {r.status_code}")

# ── Test 5: /analyse still works with URL checking ──────────
total += 1
print("\n── Test 5: /analyse still works (regression) ──")
r = httpx.post(f"{BASE}/analyse", json={
    "text": "TRAI has decided to disconnect your number in 2 hours. Press 1 to speak to officer.",
}, timeout=60)
d = r.json()
print(f"   {r.status_code} | Verdict: {d['verdict']} | Type: {d['fraud_type']}")
if r.status_code == 200 and d["verdict"] == "suspicious":
    print("   ✅ PASS")
    passed += 1
else:
    print("   ❌ FAIL")

# ── Test 6: /voice endpoint still validates ──────────────────
total += 1
print("\n── Test 6: /voice endpoint (validation check) ──")
r = httpx.post(f"{BASE}/voice", timeout=10)
print(f"   {r.status_code}")
if r.status_code == 422:
    print("   ✅ PASS — endpoint exists and validates")
    passed += 1
else:
    print(f"   ❌ FAIL")

# ── Test 7: Docs endpoint accessible ─────────────────────────
total += 1
print("\n── Test 7: API docs accessible ──")
r = httpx.get(f"{BASE}/docs")
print(f"   {r.status_code}")
if r.status_code == 200:
    print("   ✅ PASS")
    passed += 1
else:
    print("   ❌ FAIL")

# ── Summary ──────────────────────────────────────────────────
print(f"\n{'=' * 70}")
print(f"  Results: {passed}/{total} passed")
print(f"{'=' * 70}")
if passed == total:
    print("\n  PHASE 4 VALIDATION: ALL TESTS PASSED ✅")
else:
    print(f"\n  PHASE 4 VALIDATION: {total - passed} test(s) need attention")
