from fastapi import APIRouter, Query
from weather_service import owm_client, advice_engine

router = APIRouter()

@router.get("/advice")
async def weather_advice(lat: float = Query(-17.8252), lon: float = Query(31.0335)):
    forecast = await owm_client.get_onecall_forecast(lat=lat, lon=lon)
    return advice_engine.generate(forecast)

@router.get("/today")
async def weather_today(lat: float = Query(-17.8252), lon: float = Query(31.0335)):
    forecast = await owm_client.get_onecall_forecast(lat=lat, lon=lon)
    today = forecast.daily[0]
    return {"message": f"🌤 Today: {today.temperature_C}°C, {today.rain_mm}mm rain, {today.description}"}

@router.get("/tomorrow")
async def weather_tomorrow(lat: float = Query(-17.8252), lon: float = Query(31.0335)):
    forecast = await owm_client.get_onecall_forecast(lat=lat, lon=lon)
    tomorrow = forecast.daily[1]
    return {"message": f"🌤 Tomorrow: {tomorrow.temperature_C}°C, {tomorrow.rain_mm}mm rain, {tomorrow.description}"}

@router.get("/hourly")
async def weather_hourly(lat: float = Query(-17.8252), lon: float = Query(31.0335), hours: int = Query(12)):
    forecast = await owm_client.get_onecall_forecast(lat=lat, lon=lon)
    hours = min(hours, 48)
    hourly = [
        f"{p.datetime.strftime('%H:%M')}: {p.temperature_C}°C, {p.rain_mm}mm, {p.description}"
        for p in forecast.hourly[:hours]
    ]
    return {"message": f"🌤 Hourly Forecast (next {hours}h)\n" + "\n".join(hourly)}

@router.get("/week")
async def weather_week(lat: float = Query(-17.8252), lon: float = Query(31.0335)):
    forecast = await owm_client.get_onecall_forecast(lat=lat, lon=lon)
    week = [
        f"{p.datetime.strftime('%a %d %b')}: {p.temperature_C}°C, {p.rain_mm}mm, {p.description}"
        for p in forecast.daily[:7]
    ]
    return {"message": "📅 7-Day Outlook\n" + "\n".join(week)}

@router.get("/summary")
async def weather_summary(lat: float = Query(-17.8252), lon: float = Query(31.0335)):
    forecast = await owm_client.get_onecall_forecast(lat=lat, lon=lon)
    advice = advice_engine.generate(forecast)
    lines = [
        "📩 PreciAgro Weather Summary",
        f"Current: {forecast.current.temperature_C}°C, {forecast.current.description}",
        advice.planting,
        advice.irrigation,
        advice.disease_risk,
    ]
    if advice.alerts:
        lines.append("🚨 Alerts:")
        lines.extend(advice.alerts)
    return {"message": "\n".join(lines)}

@router.get("/ask")
async def weather_ask(question: str = Query(...), lat: float = Query(-17.8252), lon: float = Query(31.0335)):
    forecast = await owm_client.get_onecall_forecast(lat=lat, lon=lon)
    answer = advice_engine.answer_question(question, forecast)
    return {"question": question, "answer": answer}
