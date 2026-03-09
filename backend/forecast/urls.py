from django.urls import path
from .views import ForecastAPIView, BTCUSDHourlyForecastAPIView

urlpatterns = [
    path("forecast/", ForecastAPIView.as_view(), name="arima-forecast"),
    path("crypto/btcusd-hourly/", BTCUSDHourlyForecastAPIView.as_view(), name="btc-usd-hourly-forecast"),
]
