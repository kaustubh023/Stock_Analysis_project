import numpy as np
import pandas as pd


def arima_forecast(close: pd.Series, steps: int, order=(5, 1, 0)) -> tuple[float, list[float]]:
    steps = int(max(1, steps))
    y = close.astype(float)
    try:
        from statsmodels.tsa.arima.model import ARIMA  # type: ignore
        model = ARIMA(y, order=order, enforce_stationarity=False, enforce_invertibility=False)
        fit = model.fit()
        forecast = fit.forecast(steps=steps)
        current_price = float(y.iloc[-1])
        preds = [float(x) for x in forecast.tolist()]
        return current_price, preds
    except Exception:
        x = np.arange(len(y), dtype=np.float64).reshape(-1, 1)
        coef = np.polyfit(x.ravel(), y.values.astype(np.float64), 1)
        slope, intercept = coef[0], coef[1]
        current_price = float(y.iloc[-1])
        future_x = np.arange(len(y), len(y) + steps, dtype=np.float64)
        preds = (slope * future_x + intercept).tolist()
        return current_price, [float(max(p, 0.01)) for p in preds]
