from typing import Optional
from fastapi import APIRouter
from services.weather_service import get_forecast_by_city

router = APIRouter()

@router.get("/forecast")
def get_forecast(city: str, period: Optional[str] = "next_7_days"):
    return get_forecast_by_city(city, period=period or "next_7_days")
