import json
import numpy as np
import pandas as pd
import yfinance as yf


def fetch_history_close_series(symbol: str, period: str = "1y", interval: str = "1d") -> pd.Series:
    symbol = (symbol or "").strip().upper()
    if not symbol:
        raise ValueError("Ticker symbol is required")
    df = yf.download(symbol, period=period, interval=interval, auto_adjust=False, progress=False, threads=False)

    def pick_close_column(frame: pd.DataFrame) -> pd.Series | None:
        cols = list(frame.columns)
        norm = [str(c).strip().lower() for c in cols]
        if "close" in norm:
            return frame.iloc[:, norm.index("close")]
        if "adj close" in norm:
            return frame.iloc[:, norm.index("adj close")]
        for i, n in enumerate(norm):
            if "close" in n:
                return frame.iloc[:, i]
        return None

    close = None
    if isinstance(df.columns, pd.MultiIndex):
        try:
            lvl0 = [str(x) for x in df.columns.get_level_values(0)]
            lvl1 = [str(x) for x in df.columns.get_level_values(1)]
            if symbol in lvl0:
                sub = df.xs(symbol, axis=1, level=0)
            elif symbol in lvl1:
                sub = df.xs(symbol, axis=1, level=1)
            else:
                sub = df.copy()
                sub.columns = [f"{a}_{b}" for a, b in df.columns]
            close = pick_close_column(sub)
            if close is None and "Close" in df.columns.get_level_values(1):
                close = df.xs("Close", axis=1, level=1).iloc[:, 0]
        except Exception:
            flat = df.copy()
            flat.columns = [f"{a}_{b}" for a, b in df.columns]
            close = pick_close_column(flat)
    if close is None:
        close = pick_close_column(df) if isinstance(df, pd.DataFrame) else None

    if close is None:
        try:
            import urllib.request
            from urllib.parse import quote_plus
            rng = period if period in {"1d", "5d", "7d", "1mo", "3mo", "6mo", "1y", "2y", "5y"} else "1y"
            intv = interval if interval in {"1m", "5m", "15m", "30m", "1h", "1d", "1wk", "1mo"} else "1d"
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{quote_plus(symbol)}?range={rng}&interval={intv}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=4) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            result = (((payload or {}).get("chart") or {}).get("result") or [None])[0]
            if not result:
                raise ValueError("No Close column in history")
            timestamps = result.get("timestamp") or []
            quote = ((result.get("indicators") or {}).get("quote") or [None])[0] or {}
            closes = quote.get("close") or []
            if not closes:
                adj = ((result.get("indicators") or {}).get("adjclose") or [None])[0] or {}
                closes = adj.get("adjclose") or []
            if not timestamps or not closes:
                raise ValueError("No Close column in history")
            dt_index = pd.to_datetime(timestamps, unit="s")
            close = pd.Series(pd.to_numeric(closes, errors="coerce"), index=dt_index, name="Close")
        except Exception:
            raise ValueError("No Close column in history")

    close = pd.to_numeric(close, errors="coerce").astype(float)
    close = close.replace([np.inf, -np.inf], np.nan).dropna()
    if close.empty:
        try:
            tkr = yf.Ticker(symbol)
            h2 = tkr.history(period=period, interval=interval, auto_adjust=False)
            s2 = pick_close_column(h2) if isinstance(h2, pd.DataFrame) else None
            if s2 is not None:
                s2 = pd.to_numeric(s2, errors="coerce").astype(float).replace([np.inf, -np.inf], np.nan).dropna()
                if not s2.empty:
                    close = s2
        except Exception:
            pass
    if close.empty:
        for p in ["1y", "6mo", "3mo"]:
            try:
                df2 = yf.download(symbol, period=p, interval=interval, auto_adjust=False, progress=False, threads=False)
                s2 = None
                if isinstance(df2.columns, pd.MultiIndex):
                    flat = df2.copy()
                    flat.columns = [f"{a}_{b}" for a, b in df2.columns]
                    s2 = pick_close_column(flat)
                else:
                    s2 = pick_close_column(df2)
                if s2 is not None:
                    s2 = pd.to_numeric(s2, errors="coerce").astype(float).replace([np.inf, -np.inf], np.nan).dropna()
                    if not s2.empty:
                        close = s2
                        break
            except Exception:
                continue
    if close.empty:
        # Final attempt: Yahoo chart API with different intervals
        try:
            import urllib.request
            from urllib.parse import quote_plus
            for rng in ["7d", "1mo", "6mo", "1y", "3mo"]:
                for intv in ["1h", "1d", "1wk", "1mo"]:
                    try:
                        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{quote_plus(symbol)}?range={rng}&interval={intv}"
                        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                        with urllib.request.urlopen(req, timeout=5) as resp:
                            payload = json.loads(resp.read().decode("utf-8"))
                        result = (((payload or {}).get("chart") or {}).get("result") or [None])[0]
                        if not result:
                            continue
                        timestamps = result.get("timestamp") or []
                        inds = (result.get("indicators") or {})
                        quote = (inds.get("quote") or [None])[0] or {}
                        closes = quote.get("close") or []
                        if not closes:
                            adj = (inds.get("adjclose") or [None])[0] or {}
                            closes = adj.get("adjclose") or []
                        if not timestamps or not closes:
                            continue
                        dt_index = pd.to_datetime(timestamps, unit="s")
                        s = pd.Series(pd.to_numeric(closes, errors="coerce"), index=dt_index, name="Close")
                        s = s.replace([np.inf, -np.inf], np.nan).dropna()
                        if not s.empty:
                            close = s
                            raise StopIteration  # break out of both loops
                    except StopIteration:
                        raise
                    except Exception:
                        continue
        except StopIteration:
            pass
        except Exception:
            pass
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
