import numpy as np
import pandas as pd

from core.services import _fetch_history


def fetch_history_close_series(symbol: str, period: str = "1y", interval: str = "1d") -> pd.Series:
    symbol = (symbol or "").strip().upper()
    if not symbol:
        raise ValueError("Ticker symbol is required")

    history = _fetch_history(symbol, period=period, interval=interval)
    if history is None or history.empty or "Close" not in history.columns:
        raise ValueError("No valid closing prices found")

    close = pd.to_numeric(history["Close"], errors="coerce").astype(float)
    close = close.replace([np.inf, -np.inf], np.nan).dropna()
    if close.empty:
        raise ValueError("No valid closing prices found")

    close.index = pd.to_datetime(close.index)
    close = close.sort_index()
    return close


def build_future_business_dates(last_date: pd.Timestamp, steps: int) -> list[str]:
    steps = int(max(1, steps))
    future = pd.bdate_range(last_date + pd.Timedelta(days=1), periods=steps)
    return [str(d.date()) for d in future]


def build_future_hour_datetimes(last_ts: pd.Timestamp, steps: int) -> list[str]:
    steps = int(max(1, steps))
    future = pd.date_range(last_ts + pd.Timedelta(hours=1), periods=steps, freq="H")
    return [d.strftime("%Y-%m-%d %H:00") for d in future]
