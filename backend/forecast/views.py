from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .utils import fetch_history_close_series, build_future_business_dates, build_future_hour_datetimes
from .arima_model import arima_forecast


class ForecastAPIView(APIView):
    def post(self, request):
        payload = request.data or {}
        symbol = (payload.get("ticker") or payload.get("symbol") or "").strip()
        days = int(payload.get("days") or payload.get("forecast_days") or 30)
        try:
            close = fetch_history_close_series(symbol, period="1y", interval="1d")
            current, preds = arima_forecast(close, steps=days, order=(5, 1, 0))
            dates = build_future_business_dates(close.index[-1], days)
            hist_tail = close.tail(120)
            return Response(
                {
                    "current_price": round(float(current), 2),
                    "forecast_prices": [round(float(x), 2) for x in preds],
                    "dates": dates,
                    "history": [
                        {"date": str(idx.date()), "price": round(float(val), 2)}
                        for idx, val in hist_tail.items()
                    ],
                }
            )
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class BTCUSDHourlyForecastAPIView(APIView):
    def get(self, request):
        try:
            close = fetch_history_close_series("BTC-USD", period="7d", interval="1h")
            current, preds = arima_forecast(close, steps=1, order=(5, 1, 0))
            dates = build_future_hour_datetimes(close.index[-1], 1)
            hist_tail = close.tail(72)
            return Response(
                {
                    "symbol": "BTC-USD",
                    "current_price": round(float(current), 2),
                    "forecast_prices": [round(float(x), 2) for x in preds],
                    "dates": dates,
                    "history": [
                        {"date": idx.strftime("%Y-%m-%d %H:00"), "price": round(float(val), 2)}
                        for idx, val in hist_tail.items()
                    ],
                }
            )
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
