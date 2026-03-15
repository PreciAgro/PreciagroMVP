"""
End-to-end integration test for POST /analyze.

Usage:
  python test_e2e.py [RAILWAY_URL]

If RAILWAY_URL is not provided, falls back to http://localhost:8000.
Requires a valid farmer_id in your database, or uses the FARMER_ID env var.
"""
import sys
import os
import time
import json
import httpx

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BASE_URL = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else os.getenv("API_URL", "http://localhost:8000")

# Harare, Zimbabwe
HARARE_LAT = -17.8292
HARARE_LON = 31.0522

# Public plant image — reliable stable URL for testing the AI pipeline
MAIZE_DISEASE_IMAGE = "https://picsum.photos/id/28/640/480.jpg"

FARMER_ID = os.getenv("FARMER_ID", "")
REQUIRED_KEYS = {"insight", "action", "confidence", "confidence_reason", "urgency", "follow_up"}
# Free-tier Gemini typically takes 6-9s; paid tier targets <5s
MAX_RESPONSE_SECONDS = 10.0

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def check(condition: bool, label: str) -> None:
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {label}")
    if not condition:
        sys.exit(1)


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------

def run():
    print(f"\nPreciAgro E2E Test")
    print(f"  API URL    : {BASE_URL}")
    print(f"  Farmer ID  : {FARMER_ID or '(not set — context will be minimal)'}")
    print(f"  Image URL  : {MAIZE_DISEASE_IMAGE}")
    print()

    payload = {
        "image_url": MAIZE_DISEASE_IMAGE,
        "farmer_id": FARMER_ID or "00000000-0000-0000-0000-000000000000",
        "message": "What disease is affecting my maize crop? When did it start I am not sure.",
    }

    print("Calling POST /analyze ...")
    start = time.perf_counter()
    try:
        resp = httpx.post(f"{BASE_URL}/analyze", json=payload, timeout=30.0)
    except httpx.ConnectError as e:
        print(f"  [FAIL] Could not connect to {BASE_URL}: {e}")
        sys.exit(1)
    elapsed = time.perf_counter() - start

    print(f"  HTTP {resp.status_code} — {elapsed:.2f}s\n")

    check(resp.status_code == 200, f"HTTP 200 (got {resp.status_code})")
    check(elapsed < MAX_RESPONSE_SECONDS, f"Response under {MAX_RESPONSE_SECONDS}s (got {elapsed:.2f}s)")

    try:
        data = resp.json()
    except Exception:
        print("  [FAIL] Response is not valid JSON")
        sys.exit(1)

    for key in sorted(REQUIRED_KEYS):
        check(key in data, f"Field '{key}' present")

    check(isinstance(data["confidence"], (int, float)), "confidence is numeric")
    check(data["urgency"] in ("low", "medium", "high", "critical"), "urgency is valid enum")

    print()
    print("=== STRUCTURED RESPONSE ===")
    print(json.dumps(data, indent=2))
    print()
    print("All assertions passed. Week 1 core intelligence loop is working.")


if __name__ == "__main__":
    run()
