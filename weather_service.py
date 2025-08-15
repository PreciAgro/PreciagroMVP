import os
from datetime import datetime, timezone
from typing import List, Optional

import httpx
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()
OWM_API_KEY = os.getenv("OWM_API_KEY", "")
DEFAULT_LAT = float(os.getenv("DEFAULT_LAT", "-17.8252"))
DEFAULT_LON = float(os.getenv("DEFAULT_LON", "31.0335"))

if not OWM_API_KEY:
    raise RuntimeError("Set OWM_API_KEY in your .env file")

ONE_CALL_URL = "https://api.openweathermap.org/data/3.0/onecall"

# --------- Models ----------
class ForecastPoint(BaseModel):
    datetime: datetime
    temperature_C: float
    humidity_pct: int
    rain_mm: float
    description: str

class AlertInfo(BaseModel):
    event: str
    start: datetime
    end: datetime
    description: str

class ForecastResponse(BaseModel):
    lat: float
    lon: float
    current: ForecastPoint
    daily: List[ForecastPoint]
    hourly: Optional[List[ForecastPoint]] = None
    alerts: Optional[List[AlertInfo]] = None

class AdviceResponse(BaseModel):
    planting: str
    irrigation: str
    threats: List[str]
    temp_stress: List[str]
    disease_risk: str
    alerts: Optional[List[str]] = None

# --------- OpenWeather Client ----------
class OpenWeatherClient:
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def get_onecall_forecast(self, lat: float, lon: float) -> ForecastResponse:
        params = {"lat": lat, "lon": lon, "appid": self.api_key, "units": "metric"}
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.get(ONE_CALL_URL, params=params)
            if r.status_code != 200:
                raise Exception(f"OWM error: {r.text}")
            data = r.json()

        current = ForecastPoint(
            datetime=datetime.fromtimestamp(data["current"]["dt"], tz=timezone.utc),
            temperature_C=data["current"]["temp"],
            humidity_pct=data["current"]["humidity"],
            rain_mm=data["current"].get("rain", {}).get("1h", 0.0),
            description=data["current"]["weather"][0]["description"],
        )

        daily = [
            ForecastPoint(
                datetime=datetime.fromtimestamp(d["dt"], tz=timezone.utc),
                temperature_C=d["temp"]["day"],
                humidity_pct=d["humidity"],
                rain_mm=d.get("rain", 0.0),
                description=d["weather"][0]["description"],
            )
            for d in data.get("daily", [])
        ]

        hourly = [
            ForecastPoint(
                datetime=datetime.fromtimestamp(h["dt"], tz=timezone.utc),
                temperature_C=h["temp"],
                humidity_pct=h["humidity"],
                rain_mm=h.get("rain", {}).get("1h", 0.0),
                description=h["weather"][0]["description"],
            )
            for h in data.get("hourly", [])[:48]
        ]

        alerts = [
            AlertInfo(
                event=a.get("event", "Weather Alert"),
                start=datetime.fromtimestamp(a["start"], tz=timezone.utc),
                end=datetime.fromtimestamp(a["end"], tz=timezone.utc),
                description=a.get("description", "No details provided."),
            )
            for a in data.get("alerts", [])
        ]

        return ForecastResponse(lat=lat, lon=lon, current=current, daily=daily, hourly=hourly, alerts=alerts or None)

# --------- Advice Engine ----------
class AdviceEngine:
    def __init__(self):
        self.planting_rain_threshold_mm = 5.0
        self.planting_temp_min = 18.0
        self.planting_temp_max = 35.0
        self.irrigation_rain_threshold_mm = 3.0
        self.heavy_rain_threshold_mm = 10.0
        self.cold_stress_temp_c = 15.0
        self.frost_temp_c = 12.0
        self.heat_stress_temp_c = 33.0
        self.disease_humidity_threshold_pct = 85
        self.disease_temp_threshold_c = 22.0

    def generate(self, forecast: ForecastResponse) -> AdviceResponse:
        next_days = forecast.daily[:3]
        rain_sum = sum(p.rain_mm for p in next_days)
        temps = [p.temperature_C for p in next_days]

        planting_msg = (
            "🌱 Great planting window! Good rainfall and temperatures expected."
            if rain_sum >= self.planting_rain_threshold_mm and all(self.planting_temp_min <= t <= self.planting_temp_max for t in temps)
            else "⛔ Hold off planting. Conditions are not ideal."
        )

        irrigation_msg = (
            "🌧 Rain expected today — no irrigation needed."
            if forecast.daily and forecast.daily[0].rain_mm > self.irrigation_rain_threshold_mm
            else "💧 No significant rain today — irrigate if soil is dry."
        )

        threats = [
            f"⚠️ Heavy rain: {p.rain_mm:.1f}mm on {p.datetime.strftime('%Y-%m-%d')}."
            for p in forecast.daily if p.rain_mm > self.heavy_rain_threshold_mm
        ] or ["✅ No severe rain/frost threats."]

        disease_risk_msg = "✅ No major fungal disease risk."
        for p in forecast.daily:
            if p.humidity_pct > self.disease_humidity_threshold_pct and p.temperature_C > self.disease_temp_threshold_c:
                disease_risk_msg = "⚠️ High humidity + warm temps — fungal disease risk."
                break

        alert_msgs = [
            f"🚨 {a.event}: {a.description.strip()} (From {a.start.strftime('%Y-%m-%d %H:%M')} to {a.end.strftime('%Y-%m-%d %H:%M')})"
            for a in forecast.alerts or []
        ]

        return AdviceResponse(
            planting=planting_msg,
            irrigation=irrigation_msg,
            threats=threats,
            temp_stress=["✅ Temperatures look stable."],
            disease_risk=disease_risk_msg,
            alerts=alert_msgs or None
        )

    def answer_question(self, q: str, forecast: ForecastResponse) -> str:
        q = q.lower()
        advice = self.generate(forecast)

        if "plant" in q: return advice.planting
        if "irrigat" in q: return advice.irrigation
        if "alert" in q: return "\n".join(advice.alerts or ["✅ No alerts"])
        if "rain" in q: return f"🌧 Today: {forecast.daily[0].rain_mm} mm"
        return f"Summary:\n- {advice.planting}\n- {advice.irrigation}"

# Initialize shared instances
owm_client = OpenWeatherClient(api_key=OWM_API_KEY)
advice_engine = AdviceEngine()

