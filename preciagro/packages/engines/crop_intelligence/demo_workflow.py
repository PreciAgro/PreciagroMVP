# Example: Full CIE Workflow Demo
# This script demonstrates a complete workflow with the Crop Intelligence Engine

import requests
import json
from datetime import datetime, timedelta

# Base URL for the CIE service
BASE_URL = "http://localhost:8082"

def print_section(title):
    """Print a formatted section header."""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60 + "\n")

def pretty_print(data):
    """Pretty print JSON data."""
    print(json.dumps(data, indent=2))

def main():
    print_section("🌱 Crop Intelligence Engine - Demo Workflow")
    
    # 1. Health Check
    print_section("1. Health Check")
    response = requests.get(f"{BASE_URL}/")
    print(f"Status: {response.status_code}")
    pretty_print(response.json())
    
    # 2. Register Field
    print_section("2. Register Field")
    field_data = {
        "field_id": "demo_maize_zw_001",
        "boundary_geojson": {
            "type": "Polygon",
            "coordinates": [[[30.0, -17.5], [30.1, -17.5], [30.1, -17.6], [30.0, -17.6], [30.0, -17.5]]]
        },
        "crop": "maize",
        "variety": "SC627",
        "planting_date": "2025-11-15",
        "irrigation_access": "limited",
        "target_yield_band": "3-5 t/ha",
        "budget_class": "medium"
    }
    
    response = requests.post(f"{BASE_URL}/cie/field/register", json=field_data)
    print(f"Status: {response.status_code}")
    pretty_print(response.json())
    
    # 3. Submit Initial Telemetry
    print_section("3. Submit Telemetry Data")
    
    # Simulate 3 weeks of data
    base_date = datetime(2025, 12, 1)
    vi_data = []
    weather_data = []
    
    for week in range(3):
        date = base_date + timedelta(weeks=week)
        ndvi = 0.25 + (week * 0.10)  # Growing vigor
        
        vi_data.append({
            "date": date.strftime("%Y-%m-%d"),
            "ndvi": round(ndvi, 2),
            "evi": round(ndvi * 1.1, 2),
            "quality": "good"
        })
        
        weather_data.append({
            "ts": date.isoformat(),
            "tmax": 28.0 + (week * 0.5),
            "tmin": 18.0 + (week * 0.3),
            "rain": 5.0 if week == 1 else 2.0,
            "rh": 75.0 + (week * 2),
            "wind": 2.5,
            "rad": 22.0
        })
    
    telemetry = {
        "field_id": "demo_maize_zw_001",
        "weather": weather_data,
        "vi": vi_data,
        "soil": {
            "src": "soilgrids",
            "texture": "sandy_loam",
            "whc_mm": 140,
            "uncertainty": "±15%"
        }
    }
    
    response = requests.post(f"{BASE_URL}/cie/field/telemetry", json=telemetry)
    print(f"Status: {response.status_code}")
    pretty_print(response.json())
    
    # 4. Get Field State
    print_section("4. Get Current Field State")
    response = requests.get(f"{BASE_URL}/cie/field/state", params={"field_id": "demo_maize_zw_001"})
    print(f"Status: {response.status_code}")
    state = response.json()
    pretty_print(state)
    
    print(f"\n📊 Field Analysis:")
    print(f"   Stage: {state.get('stage', 'Unknown')} (confidence: {state.get('stage_confidence', 0):.1%})")
    print(f"   Vigor Trend: {state.get('vigor_trend', 'Unknown')}")
    print(f"   Risk Count: {len(state.get('risks', []))}")
    
    # 5. Get Recommended Actions
    print_section("5. Get Recommended Actions")
    response = requests.get(f"{BASE_URL}/cie/field/actions", params={"field_id": "demo_maize_zw_001"})
    print(f"Status: {response.status_code}")
    actions = response.json()
    pretty_print(actions)
    
    print(f"\n🎯 Action Summary:")
    for idx, action in enumerate(actions.get('items', []), 1):
        print(f"\n   {idx}. {action['action']} (Impact: {action['impact_score']:.1%})")
        print(f"      Uncertainty: {action['uncertainty']}")
        print(f"      Reasoning:")
        for reason in action['why']:
            print(f"        - {reason}")
        if action.get('window_start'):
            print(f"      Timing: {action['window_start']} to {action.get('window_end', 'TBD')}")
    
    # 6. Submit Feedback on First Action
    if actions.get('items'):
        print_section("6. Submit Farmer Feedback")
        first_action = actions['items'][0]
        
        feedback = {
            "field_id": "demo_maize_zw_001",
            "action_id": first_action['action_id'],
            "decision": "accepted",
            "note": "Action taken as recommended. Applied nitrogen top-dress."
        }
        
        response = requests.post(f"{BASE_URL}/cie/feedback", json=feedback)
        print(f"Status: {response.status_code}")
        pretty_print(response.json())
        
        print(f"\n✅ Feedback submitted for action: {first_action['action']}")
    
    print_section("✨ Demo Complete!")
    print("The Crop Intelligence Engine successfully:")
    print("  ✓ Registered a field")
    print("  ✓ Processed telemetry data")
    print("  ✓ Tracked field state")
    print("  ✓ Generated explainable recommendations")
    print("  ✓ Captured farmer feedback")
    print("\nAll data is now available for the Product Insights Engine (PIE) learning loop.")

if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to CIE service.")
        print("Please ensure the service is running:")
        print("   uvicorn preciagro.packages.engines.crop_intelligence.app.main:app --reload --port 8082")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
