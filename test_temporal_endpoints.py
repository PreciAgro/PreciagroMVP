"""Test script for temporal logic engine endpoints."""
import json
import requests
from datetime import datetime, timezone
import os

# Configuration
BASE_URL = "http://127.0.0.1:8000"
TEMPORAL_BASE = f"{BASE_URL}/temporal"

# Test data
TEST_EVENT = {
    "topic": "weather.forecast",
    "id": "test_event_001",
    "ts_utc": datetime.now(timezone.utc).isoformat(),
    "farm_id": "farm_123",
    "farmer_tz": "America/New_York",
    "payload": {
        "temperature": 35,
        "humidity": 85,
        "crop_type": "tomato",
        "forecast": "high_humidity"
    }
}

TEST_OUTCOME = {
    "outcome": "done",
    "note": "Sprayed tomatoes as recommended",
    "evidence_url": "https://example.com/photo.jpg"
}


def test_health():
    """Test the health endpoint."""
    print("🏥 Testing Health Endpoint...")
    try:
        response = requests.get(f"{TEMPORAL_BASE}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False


def test_intents():
    """Test the intents endpoint."""
    print("\n🎯 Testing Intents Endpoint...")
    try:
        response = requests.get(f"{TEMPORAL_BASE}/intents")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Intents test failed: {e}")
        return False


def test_ingest_event():
    """Test event ingestion."""
    print("\n📥 Testing Event Ingestion...")
    try:
        response = requests.post(
            f"{TEMPORAL_BASE}/events",
            json=TEST_EVENT,
            headers={"Content-Type": "application/json"}
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
            return data.get("tasks_created", 0) >= 0
        else:
            print(f"Error response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Event ingestion failed: {e}")
        return False


def test_get_schedule():
    """Test getting user schedule."""
    print("\n📅 Testing Get Schedule...")
    user_id = "user_123"
    try:
        response = requests.get(f"{TEMPORAL_BASE}/schedule/{user_id}")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
            return True
        else:
            print(f"Error response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Get schedule failed: {e}")
        return False


def test_record_outcome():
    """Test recording task outcome."""
    print("\n✅ Testing Record Outcome...")
    try:
        # First we need a task_id - in real usage this would come from a scheduled task
        test_outcome = {
            **TEST_OUTCOME,
            "task_id": "test_task_001",
            "user_id": "user_123"
        }

        response = requests.post(
            f"{TEMPORAL_BASE}/outcomes",
            json=test_outcome,
            headers={"Content-Type": "application/json"}
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
            return data.get("status") == "recorded"
        else:
            print(f"Error response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Record outcome failed: {e}")
        return False


def main():
    """Run all endpoint tests."""
    print("🚀 Testing Temporal Logic Engine Endpoints")
    print("=" * 50)

    # Check if server is running
    try:
        requests.get(f"{BASE_URL}/healthz", timeout=5)
        print("✅ Server is running")
    except:
        print("❌ Server not running. Start it with:")
        print("uvicorn preciagro.apps.api_gateway.main:app --port 8000")
        return

    tests = [
        ("Health Check", test_health),
        ("Get Intents", test_intents),
        ("Ingest Event", test_ingest_event),
        ("Get Schedule", test_get_schedule),
        ("Record Outcome", test_record_outcome)
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        try:
            if test_func():
                print(f"✅ {test_name} PASSED")
                passed += 1
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} ERROR: {e}")

    print("\n" + "=" * 50)
    print(f"Results: {passed}/{total} tests passed")

    if passed < total:
        print("\n💡 Common issues:")
        print("1. Make sure temporal routes are included in main app")
        print("2. Check DATABASE_URL environment variable")
        print("3. Ensure authentication is properly configured")
        print("4. Verify all dependencies are installed")


if __name__ == "__main__":
    main()
