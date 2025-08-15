import requests

BASE_URL = "http://127.0.0.1:8000"

def test_today():
    res = requests.get(f"{BASE_URL}/weather/today")
    print("Today's Weather:", res.json())

def test_ask():
    question = "Will it rain today?"
    res = requests.get(f"{BASE_URL}/weather/ask", params={"question": question})
    print(f"Q: {question}\nA:", res.json()["answer"])

def test_health():
    print("🔹 Testing /health ...")
    response = requests.get(f"{BASE_URL}/health")
    print("Status Code:", response.status_code)
    print("Response:", response.json())
    print()

def test_weather_advice(lat=-17.8252, lon=31.0335):
    print("🔹 Testing /weather/advice ...")
    response = requests.get(f"{BASE_URL}/weather/advice", params={"lat": lat, "lon": lon})
    print("Status Code:", response.status_code)
    try:
        data = response.json()
        for k, v in data.items():
            print(f"{k}: {v}")
    except Exception as e:
        print("Error parsing response:", e)
        print("Raw Response:", response.text)
    print()

def test_whatsapp_summary(lat=-17.8252, lon=31.0335):
    print("🔹 Testing /whatsapp/weather-summary ...")
    response = requests.get(f"{BASE_URL}/whatsapp/weather-summary", params={"lat": lat, "lon": lon})
    print("Status Code:", response.status_code)
    try:
        print("WhatsApp Message:\n", response.json()["message"])
    except Exception as e:
        print("Error parsing response:", e)
        print("Raw Response:", response.text)
    print()

if __name__ == "__main__":
    test_health()
    test_weather_advice()
    test_whatsapp_summary()
    test_today()
    test_ask()

   
