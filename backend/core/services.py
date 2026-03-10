from __future__ import annotations

import json
import time
import math
import os
from urllib.parse import quote_plus
from urllib.request import Request, urlopen
import numpy as np
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import plotly.io as pio
from django.core.cache import cache
from sklearn.linear_model import LinearRegression

FALLBACK_INDIAN_STOCKS = [
    {"symbol": "RELIANCE.NS", "name": "Reliance Industries", "exchange": "NSE"},
    {"symbol": "TCS.NS", "name": "Tata Consultancy Services", "exchange": "NSE"},
    {"symbol": "INFY.NS", "name": "Infosys", "exchange": "NSE"},
    {"symbol": "HDFCBANK.NS", "name": "HDFC Bank", "exchange": "NSE"},
    {"symbol": "ICICIBANK.NS", "name": "ICICI Bank", "exchange": "NSE"},
    {"symbol": "WIPRO.NS", "name": "Wipro", "exchange": "NSE"},
    {"symbol": "SBIN.NS", "name": "State Bank of India", "exchange": "NSE"},
    {"symbol": "AXISBANK.NS", "name": "Axis Bank", "exchange": "NSE"},
    {"symbol": "KOTAKBANK.NS", "name": "Kotak Mahindra Bank", "exchange": "NSE"},
    {"symbol": "LT.NS", "name": "Larsen & Toubro", "exchange": "NSE"},
    {"symbol": "ITC.NS", "name": "ITC", "exchange": "NSE"},
    {"symbol": "HINDUNILVR.NS", "name": "Hindustan Unilever", "exchange": "NSE"},
    {"symbol": "BHARTIARTL.NS", "name": "Bharti Airtel", "exchange": "NSE"},
    {"symbol": "MARUTI.NS", "name": "Maruti Suzuki India", "exchange": "NSE"},
    {"symbol": "BAJFINANCE.NS", "name": "Bajaj Finance", "exchange": "NSE"},
    {"symbol": "HCLTECH.NS", "name": "HCL Technologies", "exchange": "NSE"},
    {"symbol": "SUNPHARMA.NS", "name": "Sun Pharmaceutical", "exchange": "NSE"},
    {"symbol": "TATAMOTORS.NS", "name": "Tata Motors", "exchange": "NSE"},
    {"symbol": "TITAN.NS", "name": "Titan Company", "exchange": "NSE"},
    {"symbol": "ULTRACEMCO.NS", "name": "UltraTech Cement", "exchange": "NSE"},
    {"symbol": "ASIANPAINT.NS", "name": "Asian Paints", "exchange": "NSE"},
    {"symbol": "TATASTEEL.NS", "name": "Tata Steel", "exchange": "NSE"},
    {"symbol": "TECHM.NS", "name": "Tech Mahindra", "exchange": "NSE"},
    {"symbol": "TATAPOWER.NS", "name": "Tata Power", "exchange": "NSE"},
    {"symbol": "TATACONSUM.NS", "name": "Tata Consumer Products", "exchange": "NSE"},
    {"symbol": "TRENT.NS", "name": "Trent", "exchange": "NSE"},
    {"symbol": "TVSMOTOR.NS", "name": "TVS Motor Company", "exchange": "NSE"},
    {"symbol": "TORNTPHARM.NS", "name": "Torrent Pharmaceuticals", "exchange": "NSE"},
    {"symbol": "TATACHEM.NS", "name": "Tata Chemicals", "exchange": "NSE"},
    {"symbol": "TATACOMM.NS", "name": "Tata Communications", "exchange": "NSE"},
    {"symbol": "TATAELXSI.NS", "name": "Tata Elxsi", "exchange": "NSE"},
]

_SEARCH_CACHE: dict[str, tuple[float, list[dict]]] = {}
_SEARCH_CACHE_TTL_SECONDS = 300
_ANALYTICS_CACHE: dict[str, tuple[float, dict]] = {}
_ANALYTICS_CACHE_TTL_SECONDS = 900
_CLUSTER_CACHE: dict[str, tuple[float, dict]] = {}
_CLUSTER_CACHE_TTL_SECONDS = 900
_CLUSTER_FAIL_CACHE_TTL_SECONDS = 60
_PE_CACHE: dict[str, tuple[float, list[dict]]] = {}
_PE_CACHE_TTL_SECONDS = 120
_PE_CACHE_VERSION = 2
_RISK_CACHE: dict[str, tuple[float, dict]] = {}
_RISK_CACHE_TTL_SECONDS = 120
_TREND_CACHE_TTL_SECONDS = 600
_YAHOO_DOWN_UNTIL_TS = 0.0
_YAHOO_DOWN_BACKOFF_SECONDS = 90


def _is_network_block_error(exc: Exception) -> bool:
    message = str(exc).lower()
    markers = [
        "winerror 10013",
        "failed to establish a new connection",
        "max retries exceeded",
        "connectionerror",
        "temporarily unavailable",
        "name or service not known",
        "network is unreachable",
        "timed out",
    ]
    return any(marker in message for marker in markers)

def _env(key: str) -> str:
    try:
        return os.environ.get(key) or ""
    except Exception:
        return ""

def _split_symbol_exchange(symbol: str):
    s = (symbol or "").strip().upper()
    if "." in s:
        base, ext = s.split(".", 1)
        exch = "NSE" if ext == "NS" else ("BSE" if ext == "BO" else ext)
        return base, exch
    return s, None

def _to_twelve_symbol(symbol: str):
    base, exch = _split_symbol_exchange(symbol)
    if exch in {"NSE", "BSE"}:
        return f"{base}:{exch}"
    return base

def _twelve_interval(interval: str) -> str:
    mapping = {"1d": "1day", "1wk": "1week", "1mo": "1month", "60m": "1h", "30m": "30min", "15m": "15min"}
    return mapping.get((interval or "").strip(), "1day")

def _period_to_outputsize(period: str) -> int:
    p = (period or "").strip()
    return {
        "1mo": 22,
        "3mo": 66,
        "6mo": 132,
        "1y": 264,
        "2y": 528,
        "5y": 1320,
    }.get(p, 264)

def _fetch_history_twelve(symbol: str, period: str = "1y", interval: str = "1d"):
    apikey = _env("TWELVE_API_KEY")
    if not apikey:
        return pd.DataFrame()
    try:
        sym = quote_plus(_to_twelve_symbol(symbol))
        intv = _twelve_interval(interval)
        osize = _period_to_outputsize(period)
        url = f"https://api.twelvedata.com/time_series?symbol={sym}&interval={intv}&outputsize={osize}&format=JSON&timezone=UTC&apikey={quote_plus(apikey)}"
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=5) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        values = (payload or {}).get("values") or []
        if not values:
            return pd.DataFrame()
        dates = []
        closes = []
        volumes = []
        for row in values:
            try:
                dates.append(pd.to_datetime(row.get("datetime")))
                closes.append(float(row.get("close")))
                volumes.append(float(row.get("volume")) if row.get("volume") is not None else np.nan)
            except Exception:
                continue
        if not dates or not closes:
            return pd.DataFrame()
        df = pd.DataFrame({"Close": closes, "Volume": volumes}, index=pd.DatetimeIndex(dates))
        df = df.sort_index()
        return _normalize_history_df(df, symbol=symbol)
    except Exception:
        return pd.DataFrame()

def _fetch_finnhub_quote(symbol: str) -> dict:
    token = _env("FINNHUB_API_KEY")
    if not token:
        return {}
    try:
        s = quote_plus(symbol)
        url = f"https://finnhub.io/api/v1/quote?symbol={s}&token={quote_plus(token)}"
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=4) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        if not isinstance(payload, dict):
            return {}
        out = {}
        c = _safe_float(payload.get("c"), default=np.nan)
        pc = _safe_float(payload.get("pc"), default=np.nan)
        if not np.isnan(c) and c > 0:
            out["regularMarketPrice"] = float(c)
        if not np.isnan(pc) and pc > 0:
            out["regularMarketPreviousClose"] = float(pc)
        return out
    except Exception:
        return {}

def _fetch_finnhub_metrics(symbol: str) -> dict:
    token = _env("FINNHUB_API_KEY")
    if not token:
        return {}
    try:
        s = quote_plus(symbol)
        url = f"https://finnhub.io/api/v1/stock/metric?symbol={s}&metric=all&token={quote_plus(token)}"
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=5) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        metric = (payload or {}).get("metric") or {}
        out = {}
        pe = _safe_float(metric.get("peNormalizedAnnual") or metric.get("peTTM") or metric.get("peExclExtraTTM"), default=np.nan)
        eps_ttm = _safe_float(metric.get("epsTTM"), default=np.nan)
        mcap = _safe_float(metric.get("marketCapitalization"), default=np.nan)
        if not np.isnan(pe) and pe > 0:
            out["trailingPE"] = float(pe)
        if not np.isnan(eps_ttm) and eps_ttm > 0:
            out["epsTrailingTwelveMonths"] = float(eps_ttm)
        if not np.isnan(mcap) and mcap > 0:
            out["marketCap"] = float(mcap)
        return out
    except Exception:
        return {}


def _to_alpha_symbol(symbol: str) -> str:
    base, exch = _split_symbol_exchange(symbol)
    if exch == "NSE":
        return f"{base}.NSE"
    if exch == "BSE":
        return f"{base}.BSE"
    return base


def _trim_history_by_period(df: pd.DataFrame, period: str) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    mapping = {
        "1mo": 31,
        "3mo": 92,
        "6mo": 184,
        "1y": 366,
        "2y": 732,
        "5y": 1830,
    }
    days = mapping.get((period or "").strip())
    if not days:
        return df
    cutoff = pd.Timestamp.utcnow().tz_localize(None) - pd.Timedelta(days=days)
    return df[df.index >= cutoff].copy()


def _fetch_history_alpha_vantage(symbol: str, period: str = "1y", interval: str = "1d"):
    apikey = _env("ALPHAVANTAGE_API_KEY")
    if not apikey:
        return pd.DataFrame()

    normalized_symbol = quote_plus(_to_alpha_symbol(symbol))
    interval = (interval or "1d").strip().lower()
    try:
        if interval in {"1d", "1wk", "1mo"}:
            if interval == "1d":
                function = "TIME_SERIES_DAILY_ADJUSTED"
                series_key = "Time Series (Daily)"
            elif interval == "1wk":
                function = "TIME_SERIES_WEEKLY_ADJUSTED"
                series_key = "Weekly Adjusted Time Series"
            else:
                function = "TIME_SERIES_MONTHLY_ADJUSTED"
                series_key = "Monthly Adjusted Time Series"
            url = (
                f"https://www.alphavantage.co/query?function={function}&symbol={normalized_symbol}"
                f"&outputsize=full&apikey={quote_plus(apikey)}"
            )
        elif interval in {"15m", "30m", "60m"}:
            url = (
                f"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={normalized_symbol}"
                f"&interval={quote_plus(interval)}&outputsize=full&apikey={quote_plus(apikey)}"
            )
            series_key = f"Time Series ({interval})"
        else:
            return pd.DataFrame()

        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=6) as resp:
            payload = json.loads(resp.read().decode("utf-8"))

        rows = (payload or {}).get(series_key) or {}
        if not isinstance(rows, dict) or not rows:
            return pd.DataFrame()

        dates = []
        closes = []
        volumes = []
        for dt, row in rows.items():
            try:
                dates.append(pd.to_datetime(dt))
                closes.append(float(row.get("4. close") or row.get("5. adjusted close")))
                volumes.append(float(row.get("6. volume") or row.get("5. volume") or np.nan))
            except Exception:
                continue

        if not dates or not closes:
            return pd.DataFrame()

        df = pd.DataFrame({"Close": closes, "Volume": volumes}, index=pd.DatetimeIndex(dates))
        df = df.sort_index()
        df = _trim_history_by_period(df, period)
        return _normalize_history_df(df, symbol=symbol)
    except Exception:
        return pd.DataFrame()


def _fetch_alpha_quote(symbol: str) -> dict:
    apikey = _env("ALPHAVANTAGE_API_KEY")
    if not apikey:
        return {}
    try:
        normalized_symbol = quote_plus(_to_alpha_symbol(symbol))
        url = (
            f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={normalized_symbol}"
            f"&apikey={quote_plus(apikey)}"
        )
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=5) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        quote = (payload or {}).get("Global Quote") or {}
        if not quote:
            return {}

        out = {}
        price = _safe_float(quote.get("05. price"), default=np.nan)
        prev_close = _safe_float(quote.get("08. previous close"), default=np.nan)
        if not np.isnan(price) and price > 0:
            out["regularMarketPrice"] = float(price)
        if not np.isnan(prev_close) and prev_close > 0:
            out["regularMarketPreviousClose"] = float(prev_close)
        return out
    except Exception:
        return {}


def _fetch_alpha_metrics(symbol: str) -> dict:
    apikey = _env("ALPHAVANTAGE_API_KEY")
    if not apikey:
        return {}
    try:
        normalized_symbol = quote_plus(_to_alpha_symbol(symbol))
        url = (
            f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={normalized_symbol}"
            f"&apikey={quote_plus(apikey)}"
        )
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=5) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        if not isinstance(payload, dict) or not payload:
            return {}

        out = {}
        pe = _safe_float(payload.get("PERatio"), default=np.nan)
        eps = _safe_float(payload.get("EPS"), default=np.nan)
        market_cap = _safe_float(payload.get("MarketCapitalization"), default=np.nan)
        if not np.isnan(pe) and pe > 0:
            out["trailingPE"] = float(pe)
        if not np.isnan(eps) and eps > 0:
            out["epsTrailingTwelveMonths"] = float(eps)
        if not np.isnan(market_cap) and market_cap > 0:
            out["marketCap"] = float(market_cap)
        return out
    except Exception:
        return {}


def _is_yahoo_temporarily_blocked() -> bool:
    return time.time() < _YAHOO_DOWN_UNTIL_TS


def _mark_yahoo_temporarily_blocked() -> None:
    global _YAHOO_DOWN_UNTIL_TS
    _YAHOO_DOWN_UNTIL_TS = time.time() + _YAHOO_DOWN_BACKOFF_SECONDS

def _empty_stock_payload(symbol: str, company: str | None = None):
    return {
        "metrics": {
            "symbol": symbol,
            "company": company or symbol,
            "pe_ratio": 0.0,
            "min_price": 0.0,
            "max_price": 0.0,
            "current_price": 0.0,
            "eps": 0.0,
            "market_cap": None,
            "intrinsic": 0.0,
            "discount_pct": 0.0,
            "opportunity": "Low",
        },
        "graphs": {
            "pe": [],
            "discount": [],
            "opportunity": [],
        },
    }


def _safe_float(value, default=0.0):
    try:
        if value is None:
            return default
        if pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_history_df(df: pd.DataFrame | None, symbol: str | None = None):
    if df is None or len(df) == 0:
        return pd.DataFrame()

    sub = df
    try:
        if isinstance(df.columns, pd.MultiIndex):
            lvl0 = [str(x) for x in df.columns.get_level_values(0)]
            lvl1 = [str(x) for x in df.columns.get_level_values(1)]
            sym = (symbol or "").strip().upper()
            if sym and sym in lvl0:
                sub = df.xs(sym, axis=1, level=0)
            elif sym and sym in lvl1:
                sub = df.xs(sym, axis=1, level=1)
            else:
                sub = df.copy()
                sub.columns = [f"{a}_{b}" for a, b in sub.columns]
    except Exception:
        sub = df

    close_col = None
    volume_col = None
    for col in list(sub.columns):
        cname = str(col).strip().lower()
        if close_col is None and (cname == "close" or cname.endswith("_close") or cname.startswith("close_")):
            close_col = col
        if volume_col is None and (cname == "volume" or cname.endswith("_volume") or cname.startswith("volume_")):
            volume_col = col

    if close_col is None:
        return pd.DataFrame()

    out = pd.DataFrame(index=sub.index)
    out["Close"] = pd.to_numeric(sub[close_col], errors="coerce")
    if volume_col is not None:
        out["Volume"] = pd.to_numeric(sub[volume_col], errors="coerce")
    return out.dropna(subset=["Close"]).copy()


def _fetch_history(symbol: str, period: str = "1y", interval: str = "1d"):
    # Prefer external provider if configured
    hist = _fetch_history_twelve(symbol, period=period, interval=interval)
    if hist is not None and not hist.empty:
        return hist
    hist = _fetch_history_alpha_vantage(symbol, period=period, interval=interval)
    if hist is not None and not hist.empty:
        return hist
    if _is_yahoo_temporarily_blocked():
        return pd.DataFrame()

    # Prefer batched download path first; it is usually less rate-limit-prone than per-ticker history/info calls.
    attempts = [
        lambda: yf.download(
            symbol,
            period=period,
            interval=interval,
            auto_adjust=False,
            progress=False,
            threads=False,
        ),
        lambda: yf.Ticker(symbol).history(period=period, interval=interval, auto_adjust=False),
    ]

    for attempt in attempts:
        try:
            hist = attempt()
            hist = _normalize_history_df(hist, symbol=symbol)
            if hist is not None and not hist.empty:
                return hist
        except Exception as exc:
            if _is_network_block_error(exc):
                _mark_yahoo_temporarily_blocked()
                break
            time.sleep(0.1)
            continue

    if _is_yahoo_temporarily_blocked():
        return pd.DataFrame()

    # Last fallback: direct Yahoo chart API (often works even if yfinance wrappers are rate-limited).
    try:
        rng = period if period in {"1mo", "3mo", "6mo", "1y", "2y", "5y"} else "1y"
        intv = interval if interval in {"1d", "1wk", "1mo"} else "1d"
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{quote_plus(symbol)}?range={rng}&interval={intv}"
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=4) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        result = (((payload or {}).get("chart") or {}).get("result") or [None])[0]
        if not result:
            return pd.DataFrame()
        timestamps = result.get("timestamp") or []
        quote = ((result.get("indicators") or {}).get("quote") or [None])[0] or {}
        closes = quote.get("close") or []
        volumes = quote.get("volume") or []
        if not timestamps or not closes:
            return pd.DataFrame()
        dt_index = pd.to_datetime(timestamps, unit="s")
        df = pd.DataFrame(
            {
                "Close": pd.to_numeric(closes, errors="coerce"),
                "Volume": pd.to_numeric(volumes, errors="coerce"),
            },
            index=dt_index,
        ).dropna(subset=["Close"])
        return _normalize_history_df(df, symbol=symbol)
    except Exception as exc:
        if _is_network_block_error(exc):
            _mark_yahoo_temporarily_blocked()
        return pd.DataFrame()


def _fetch_quote_map(symbols: list[str]):
    # Try external provider first if available.
    if not symbols or _is_yahoo_temporarily_blocked():
        return {}
    symbols = [str(s).strip().upper() for s in symbols if str(s).strip()]
    out: dict[str, dict] = {}
    token = _env("FINNHUB_API_KEY")
    if token:
        for s in symbols:
            try:
                q = _fetch_finnhub_quote(s)
                m = _fetch_finnhub_metrics(s)
                if q or m:
                    row = {}
                    row.update(q)
                    row.update(m)
                    out[s] = row
            except Exception:
                continue
        missing_after_ext = [s for s in symbols if s not in out]
        symbols = missing_after_ext or []
        if not symbols:
            return out
    alpha_key = _env("ALPHAVANTAGE_API_KEY")
    if alpha_key and symbols:
        for s in list(symbols):
            try:
                q = _fetch_alpha_quote(s)
                m = _fetch_alpha_metrics(s)
                if q or m:
                    row = {}
                    row.update(q)
                    row.update(m)
                    out[s] = row
            except Exception:
                continue
        symbols = [s for s in symbols if s not in out]
        if not symbols:
            return out
    try:
        symbol_list = ",".join(symbols)
        url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={quote_plus(symbol_list)}"
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=4) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        rows = (((payload or {}).get("quoteResponse") or {}).get("result")) or []
        for row in rows:
            sym = (row.get("symbol") or "").strip().upper()
            if sym and sym not in out:
                out[sym] = row
    except Exception as exc:
        if _is_network_block_error(exc):
            _mark_yahoo_temporarily_blocked()
    # Fallback: fetch any missing symbols individually with short timeouts
    missing = [s for s in symbols if s not in out]
    for s in missing:
        try:
            url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={quote_plus(s)}"
            req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urlopen(req, timeout=3) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            rows = (((payload or {}).get("quoteResponse") or {}).get("result")) or []
            for row in rows:
                sym = (row.get("symbol") or "").strip().upper()
                if sym:
                    out[sym] = row
        except Exception as exc:
            if _is_network_block_error(exc):
                _mark_yahoo_temporarily_blocked()
            continue
    return out

def _compute_pe_yf(symbol: str) -> float | None:
    try:
        if _is_yahoo_temporarily_blocked():
            raise RuntimeError("yahoo temporarily blocked")
        tkr = yf.Ticker(symbol)
        fast = {}
        info = {}
        try:
            fast = dict(tkr.fast_info or {})
        except Exception as exc:
            if _is_network_block_error(exc):
                _mark_yahoo_temporarily_blocked()
        try:
            info = tkr.info or {}
        except Exception as exc:
            if _is_network_block_error(exc):
                _mark_yahoo_temporarily_blocked()
        pe = _safe_float(
            fast.get("trailingPE")
            or fast.get("forwardPE")
            or info.get("trailingPE")
            or info.get("forwardPE"),
            default=np.nan,
        )
        if not np.isnan(pe) and pe > 0:
            return float(pe)
        eps = _safe_float(
            info.get("trailingEps")
            or fast.get("epsTrailingTwelveMonths"),
            default=np.nan,
        )
        price = _safe_float(
            fast.get("lastPrice")
            or fast.get("regularMarketPrice")
            or info.get("currentPrice")
            or info.get("regularMarketPrice"),
            default=np.nan,
        )
        if eps > 0 and not np.isnan(price):
            return float(price / eps)
    except Exception as exc:
        if _is_network_block_error(exc):
            _mark_yahoo_temporarily_blocked()
    return None

def _compute_eps_from_income_shares(symbol: str) -> float | None:
    try:
        if _is_yahoo_temporarily_blocked():
            raise RuntimeError("yahoo temporarily blocked")
        tkr = yf.Ticker(symbol)
        info = {}
        try:
            info = tkr.info or {}
        except Exception as exc:
            if _is_network_block_error(exc):
                _mark_yahoo_temporarily_blocked()
            info = {}
        shares = _safe_float(info.get("sharesOutstanding"), default=np.nan)
        if np.isnan(shares) or shares <= 0:
            try:
                gf = tkr.get_shares_full()
                if gf is not None and len(gf) > 0:
                    shares = _safe_float(gf.dropna().iloc[-1], default=np.nan)
            except Exception:
                pass
        qdf = None
        try:
            qdf = tkr.get_income_stmt(freq="quarterly")
        except Exception:
            qdf = None
        if qdf is None or len(qdf) == 0:
            try:
                qdf = tkr.quarterly_financials
            except Exception:
                qdf = None
        net_income_ttm = np.nan
        if qdf is not None and len(qdf) > 0:
            idx = [str(x).lower() for x in list(qdf.index)]
            candidates = ["net income", "netincome", "net income applicable to common shares", "net income common stockholders"]
            ni_row = None
            for i, name in enumerate(idx):
                for c in candidates:
                    if c in name:
                        ni_row = qdf.iloc[i]
                        break
                if ni_row is not None:
                    break
            if ni_row is None and "Net Income" in qdf.index:
                ni_row = qdf.loc["Net Income"]
            if ni_row is not None is not None:
                vals = pd.to_numeric(ni_row, errors="coerce").dropna()
                if len(vals) >= 1:
                    s = float(vals.iloc[:4].sum()) if len(vals) >= 4 else float(vals.sum())
                    net_income_ttm = s
        if (not np.isnan(net_income_ttm)) and shares and shares > 0:
            eps = net_income_ttm / shares
            if eps > 0:
                return float(eps)
    except Exception as exc:
        if _is_network_block_error(exc):
            _mark_yahoo_temporarily_blocked()
    return None

def _normalize_symbol_for_trend(symbol: str):
    base_symbol = (symbol or "").strip().upper()
    if not base_symbol:
        return ""
    if "." in base_symbol:
        return base_symbol
    return f"{base_symbol}.NS"


def _prepare_regression_data(close_series: pd.Series):
    y = close_series.astype(float).to_numpy()
    X = np.arange(len(y), dtype=np.float64).reshape(-1, 1)
    return X, y


def fetch_stock_trend_data(symbol: str):
    normalized_symbol = _normalize_symbol_for_trend(symbol)
    if not normalized_symbol:
        raise ValueError("Invalid ticker symbol.")

    cache_key = f"trend_data:{normalized_symbol}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    # Try provided symbol first, then NSE fallback for bare tickers.
    candidate_symbols = [normalized_symbol]
    raw_symbol = (symbol or "").strip().upper()
    if raw_symbol and raw_symbol != normalized_symbol:
        candidate_symbols.insert(0, raw_symbol)

    history = pd.DataFrame()
    selected_symbol = normalized_symbol
    for candidate in candidate_symbols:
        history = _fetch_history(candidate, period="1y", interval="1d")
        if history is not None and not history.empty:
            selected_symbol = candidate
            break

    if history is None or history.empty:
        raise ValueError(f"No data available for ticker '{symbol}'.")

    history = history.dropna(subset=["Close"]).sort_index().copy()
    if len(history) < 2:
        raise ValueError(f"Insufficient data for ticker '{symbol}' to build a trend.")

    X, y = _prepare_regression_data(history["Close"])
    model = LinearRegression()
    model.fit(X, y)
    predicted_prices = model.predict(X)

    quote_map = _fetch_quote_map([selected_symbol])
    quote = quote_map.get(selected_symbol, {})
    company_name = (
        quote.get("longName")
        or quote.get("shortName")
        or selected_symbol
    )

    result = {
        "symbol": selected_symbol,
        "company_name": company_name,
        "dates": history.index.strftime("%Y-%m-%d").tolist(),
        "actual_prices": [round(float(v), 2) for v in y.tolist()],
        "predicted_prices": [round(float(v), 2) for v in predicted_prices.tolist()],
        "current_price": round(float(y[-1]), 2),
        "slope": round(float(model.coef_[0]), 6),
        "intercept": round(float(model.intercept_), 4),
    }
    cache.set(cache_key, result, timeout=_TREND_CACHE_TTL_SECONDS)
    return result


def build_stock_trend_chart(trend_data: dict):
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=trend_data["dates"],
            y=trend_data["actual_prices"],
            mode="lines",
            name="Actual Close",
            line={"color": "#0d6efd", "width": 2},
        )
    )
    fig.add_trace(
        go.Scatter(
            x=trend_data["dates"],
            y=trend_data["predicted_prices"],
            mode="lines",
            name="Linear Regression Trend",
            line={"color": "#dc3545", "width": 2},
        )
    )
    fig.update_layout(
        title=f"{trend_data['symbol']} - 1Y Linear Regression Trend",
        xaxis_title="Date",
        yaxis_title="Price",
        template="plotly_white",
        margin={"l": 40, "r": 20, "t": 50, "b": 40},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.01, "xanchor": "left", "x": 0},
        height=420,
    )
    return pio.to_html(fig, include_plotlyjs=False, full_html=False)


def build_portfolio_trend_analysis(stocks: list[dict]):
    if not stocks:
        return []

    items = []
    seen = set()
    for stock in stocks:
        original_symbol = (stock.get("symbol") or "").strip().upper()
        if not original_symbol or original_symbol in seen:
            continue
        seen.add(original_symbol)

        company_name = (stock.get("company_name") or original_symbol).strip()
        try:
            trend_data = fetch_stock_trend_data(original_symbol)
            chart_html = build_stock_trend_chart(trend_data)
            items.append(
                {
                    "symbol": trend_data["symbol"],
                    "company_name": company_name if company_name else trend_data["company_name"],
                    "current_price": trend_data["current_price"],
                    "chart_html": chart_html,
                    "error": None,
                }
            )
        except ValueError as exc:
            items.append(
                {
                    "symbol": original_symbol,
                    "company_name": company_name,
                    "current_price": None,
                    "chart_html": None,
                    "error": str(exc),
                }
            )
        except Exception:
            items.append(
                {
                    "symbol": original_symbol,
                    "company_name": company_name,
                    "current_price": None,
                    "chart_html": None,
                    "error": "Stock data is temporarily unavailable due to API/network issues.",
                }
            )
    return items


def search_indian_stocks(query: str):
    q = (query or "").strip().lower()
    if not q:
        return []

    now = time.time()
    cached = _SEARCH_CACHE.get(q)
    if cached and (now - cached[0]) <= _SEARCH_CACHE_TTL_SECONDS:
        return cached[1]

    # Always rank and return fast local matches first.
    candidates = list(FALLBACK_INDIAN_STOCKS)
    # 1-letter lookups stay local-only for instant responses.
    should_query_yf = len(q) >= 2 and not _is_yahoo_temporarily_blocked()
    if should_query_yf:
        try:
            search = yf.Search(query=query, max_results=20)
            candidates.extend(search.quotes or [])
        except Exception as exc:
            if _is_network_block_error(exc):
                _mark_yahoo_temporarily_blocked()
            pass

    ticker_matches = []
    name_matches = []
    seen = set()

    for item in candidates:
        symbol = (item.get("symbol") or "").strip()
        exchange = (item.get("exchDisp") or item.get("exchange") or "").strip().upper()
        name = (item.get("shortname") or item.get("longname") or item.get("name") or symbol).strip()
        ticker_base = symbol.split(".")[0].lower()
        symbol_l = symbol.lower()
        name_l = name.lower()

        is_indian = symbol.endswith(".NS") or symbol.endswith(".BO") or exchange in {"NSE", "BSE"}
        if not is_indian:
            continue
        ticker_hit = symbol_l.startswith(q) or ticker_base.startswith(q)
        name_hit = name_l.startswith(q)
        if not (ticker_hit or name_hit):
            continue
        if symbol in seen:
            continue

        seen.add(symbol)
        entry = {
            "symbol": symbol,
            "name": name,
            "exchange": exchange or "NSE",
        }

        if ticker_hit:
            ticker_matches.append(entry)
        else:
            name_matches.append(entry)

        if len(ticker_matches) + len(name_matches) >= 10:
            break

    result = (ticker_matches + name_matches)[:10]
    # If local + single yfinance pass couldn't fill enough rows, try one NSE-focused pass.
    if len(result) < 10 and should_query_yf:
        try:
            search_nse = yf.Search(query=f"{query} nse", max_results=20)
            extra_candidates = search_nse.quotes or []
        except Exception as exc:
            if _is_network_block_error(exc):
                _mark_yahoo_temporarily_blocked()
            extra_candidates = []

        for item in extra_candidates:
            symbol = (item.get("symbol") or "").strip()
            exchange = (item.get("exchDisp") or item.get("exchange") or "").strip().upper()
            name = (item.get("shortname") or item.get("longname") or item.get("name") or symbol).strip()
            ticker_base = symbol.split(".")[0].lower()
            symbol_l = symbol.lower()
            name_l = name.lower()

            is_indian = symbol.endswith(".NS") or symbol.endswith(".BO") or exchange in {"NSE", "BSE"}
            ticker_hit = symbol_l.startswith(q) or ticker_base.startswith(q)
            name_hit = name_l.startswith(q)
            if (not is_indian) or (not (ticker_hit or name_hit)) or symbol in seen:
                continue
            seen.add(symbol)
            entry = {"symbol": symbol, "name": name, "exchange": exchange or "NSE"}
            if ticker_hit:
                ticker_matches.append(entry)
            else:
                name_matches.append(entry)

        result = (ticker_matches + name_matches)[:10]
    _SEARCH_CACHE[q] = (now, result)
    return result


def fetch_stock_metrics(symbol: str):
    symbol = (symbol or "").strip().upper()
    now = time.time()
    cached = _ANALYTICS_CACHE.get(symbol)
    cached_payload = cached[1] if cached else None
    cached_price = _safe_float((cached_payload or {}).get("metrics", {}).get("current_price"), default=0.0)
    if cached and (now - cached[0]) <= _ANALYTICS_CACHE_TTL_SECONDS and cached_price > 0:
        return cached_payload
    # Purge stale/invalid cache entries so they cannot mask live fetch failures.
    if cached and cached_price <= 0:
        _ANALYTICS_CACHE.pop(symbol, None)

    ticker = yf.Ticker(symbol) if not _is_yahoo_temporarily_blocked() else None
    history = _fetch_history(symbol, period="1y", interval="1d")
    if history.empty:
        # Extra fallback: use the robust close-series fetcher from forecast.utils
        try:
            from forecast.utils import fetch_history_close_series  # type: ignore
            series = fetch_history_close_series(symbol, period="1y", interval="1d")
            if series is not None and not series.empty:
                history = pd.DataFrame({"Close": series, "Volume": np.nan})
        except Exception:
            pass
    if history.empty:
        if cached and cached_price > 0:
            return cached_payload
        # As a final, non-blocking fallback, synthesize a short flat history from quote price
        try:
            quote_map = _fetch_quote_map([symbol])
            qr = quote_map.get(symbol, {}) or {}
            px = _safe_float(qr.get("regularMarketPrice") or qr.get("regularMarketPreviousClose"), default=np.nan)
            if not np.isnan(px) and px > 0:
                dates = pd.bdate_range(end=pd.Timestamp.utcnow().normalize(), periods=60)
                history = pd.DataFrame({"Close": float(px), "Volume": np.nan}, index=dates)
        except Exception:
            pass
    if history.empty:
        raise ValueError("Unable to fetch stock data right now (Yahoo rate-limit or network issue). Please retry in a few seconds.")

    info = {}
    fast = {}
    ext_metrics = _fetch_finnhub_metrics(symbol) if _env("FINNHUB_API_KEY") else {}
    ext_quote = _fetch_finnhub_quote(symbol) if _env("FINNHUB_API_KEY") else {}
    if ticker is not None:
        try:
            info = ticker.info or {}
        except Exception as exc:
            if _is_network_block_error(exc):
                _mark_yahoo_temporarily_blocked()
            info = {}
        try:
            fast = dict(ticker.fast_info or {})
        except Exception as exc:
            if _is_network_block_error(exc):
                _mark_yahoo_temporarily_blocked()
            fast = {}
    quote_map = _fetch_quote_map([symbol])
    quote_row = quote_map.get(symbol, {})
    # Merge external provider fields (if any) with quote row as highest priority
    if ext_metrics:
        quote_row = {**quote_row, **ext_metrics}
    if ext_quote:
        quote_row = {**quote_row, **ext_quote}

    history = history.dropna(subset=["Close"]).copy()
    if history.empty:
        if cached and cached_price > 0:
            return cached_payload
        raise ValueError("No price history available for this symbol.")
    history["date"] = history.index.strftime("%Y-%m-%d")

    close = history["Close"]
    current_price = _safe_float(close.iloc[-1])
    min_price = _safe_float(close.min())
    max_price = _safe_float(close.max())
    if current_price <= 0:
        current_price = _safe_float(
            quote_row.get("regularMarketPrice") or quote_row.get("regularMarketPreviousClose"),
            default=current_price,
        )

    pe_ratio = _safe_float(
        quote_row.get("trailingPE")
        or quote_row.get("forwardPE")
        or info.get("trailingPE")
        or info.get("forwardPE")
        or fast.get("trailingPE")
        or fast.get("forwardPE"),
        default=np.nan,
    )
    eps = _safe_float(
        quote_row.get("epsTrailingTwelveMonths")
        or info.get("trailingEps")
        or fast.get("epsTrailingTwelveMonths"),
        default=np.nan,
    )
    market_cap = _safe_float(quote_row.get("marketCap") or info.get("marketCap"), default=np.nan)

    if (np.isnan(pe_ratio) or pe_ratio <= 0) and eps > 0:
        pe_ratio = _safe_float(current_price / eps, default=np.nan)
    if (np.isnan(eps) or eps <= 0) and pe_ratio and not np.isnan(pe_ratio) and pe_ratio > 0:
        eps = _safe_float(current_price / pe_ratio, default=np.nan)

    # Ensure EPS is usable even when fundamentals are unavailable/rate-limited.
    if (np.isnan(eps) or eps <= 0) and pe_ratio and not np.isnan(pe_ratio) and pe_ratio > 0:
        eps = _safe_float(current_price / pe_ratio, default=np.nan)
    # Extra fallback: try direct yfinance PE fetch if still missing
    if (np.isnan(pe_ratio) or pe_ratio <= 0):
        try:
            alt = _compute_pe_yf(symbol)
            if alt is not None and alt > 0:
                pe_ratio = float(alt)
                if (np.isnan(eps) or eps <= 0) and current_price > 0:
                    eps = _safe_float(current_price / pe_ratio, default=np.nan)
        except Exception:
            pass
    if (np.isnan(pe_ratio) or pe_ratio <= 0):
        try:
            eps_est = _compute_eps_from_income_shares(symbol)
            if eps_est is not None and eps_est > 0 and current_price > 0:
                eps = _safe_float(eps, default=np.nan)
                if np.isnan(eps) or eps <= 0:
                    eps = float(eps_est)
                pe_ratio = _safe_float(current_price / eps, default=np.nan)
        except Exception:
            pass

    intrinsic = (eps * 18.0) if (not np.isnan(eps) and eps > 0) else (
        current_price * (18.0 / pe_ratio) if (pe_ratio and not np.isnan(pe_ratio) and pe_ratio > 0) else current_price
    )
    intrinsic = max(_safe_float(intrinsic, default=current_price), 0.01)
    discount_pct = ((intrinsic - current_price) / intrinsic) * 100 if intrinsic > 0 else 0.0

    if (not np.isnan(eps)) and eps > 0 and discount_pct >= 25:
        opportunity = "High"
    elif (not np.isnan(eps)) and eps > 0 and discount_pct >= 10:
        opportunity = "Medium"
    else:
        opportunity = "Low"

    history["pe"] = history["Close"].apply(lambda px: (px / eps) if (not np.isnan(eps) and eps > 0) else np.nan)
    history["discount"] = ((intrinsic - history["Close"]) / intrinsic) * 100
    history["opportunity"] = intrinsic - history["Close"]

    pe_out = _safe_float(pe_ratio, default=np.nan)
    pe_out = None if (np.isnan(pe_out) or pe_out <= 0) else round(float(pe_out), 2)
    eps_out = _safe_float(eps, default=np.nan)
    eps_out = None if (np.isnan(eps_out) or eps_out <= 0) else round(float(eps_out), 2)
    metrics = {
        "symbol": symbol,
        "company": info.get("longName") or info.get("shortName") or quote_row.get("longName") or quote_row.get("shortName") or symbol,
        "pe_ratio": pe_out,
        "min_price": round(min_price, 2),
        "max_price": round(max_price, 2),
        "current_price": round(current_price, 2),
        "eps": eps_out,
        "market_cap": int(market_cap) if not np.isnan(market_cap) else None,
        "intrinsic": round(intrinsic, 2),
        "discount_pct": round(_safe_float(discount_pct, default=0.0), 2),
        "opportunity": opportunity,
    }

    pe_graph = [{"date": row.date, "value": round(_safe_float(row.pe), 2)} for row in history.itertuples()]
    discount_graph = [{"date": row.date, "value": round(_safe_float(row.discount), 2)} for row in history.itertuples()]
    opportunity_graph = [{"date": row.date, "value": round(_safe_float(row.opportunity), 2)} for row in history.itertuples()]

    result = {
        "metrics": metrics,
        "graphs": {
            "pe": pe_graph,
            "discount": discount_graph,
            "opportunity": opportunity_graph,
        },
    }
    _ANALYTICS_CACHE[symbol] = (now, result)
    return result


def portfolio_pe_comparison(symbols: list[str]):
    output: list[dict] = []
    if not symbols:
        return output
    symbols = [str(s).strip().upper() for s in symbols if str(s).strip()]
    cache_key = f"v{_PE_CACHE_VERSION}|" + ",".join(sorted(symbols))
    now = time.time()
    cached = _PE_CACHE.get(cache_key)
    if cached and (now - cached[0]) <= _PE_CACHE_TTL_SECONDS:
        return cached[1]

    latest_close: dict[str, float] = {}

    quote_map = _fetch_quote_map(symbols)

    for symbol in symbols:
        pe = np.nan
        eps = np.nan
        disc = None
        qrow = quote_map.get(symbol, {}) or {}
        # Prefer quote endpoint values first (fast and symbol-specific)
        close_px = _safe_float(
            qrow.get("regularMarketPrice") or qrow.get("regularMarketPreviousClose"),
            default=np.nan,
        )
        eps = _safe_float(
            qrow.get("epsTrailingTwelveMonths") or qrow.get("trailingEps"),
            default=np.nan,
        )
        pe = _safe_float(
            (qrow.get("trailingPE") if qrow.get("trailingPE") is not None else qrow.get("forwardPE")),
            default=np.nan,
        )
        if np.isnan(pe) and eps > 0 and not np.isnan(close_px):
            pe = _safe_float(close_px / eps, default=np.nan)
        try:
            if _is_yahoo_temporarily_blocked():
                raise RuntimeError("yahoo temporarily blocked")
            ticker = yf.Ticker(symbol)
            tkr = yf.Ticker(symbol)
            fast = {}
            info = {}
            try:
                fast = dict(tkr.fast_info or {})
            except Exception as exc:
                if _is_network_block_error(exc):
                    _mark_yahoo_temporarily_blocked()
            try:
                info = tkr.info or {}
            except Exception as exc:
                if _is_network_block_error(exc):
                    _mark_yahoo_temporarily_blocked()
            yf_pe = _safe_float(
                fast.get("trailingPE")
                or fast.get("forwardPE")
                or info.get("trailingPE")
                or info.get("forwardPE"),
                default=np.nan,
            )
            if np.isnan(yf_pe):
                yf_eps = _safe_float(
                    info.get("trailingEps")
                    or fast.get("epsTrailingTwelveMonths"),
                    default=np.nan,
                )
                yf_price = _safe_float(
                    fast.get("lastPrice")
                    or fast.get("regularMarketPrice")
                    or info.get("currentPrice")
                    or info.get("regularMarketPrice"),
                    default=np.nan,
                )
                if yf_eps > 0 and not np.isnan(yf_price):
                    yf_pe = _safe_float(yf_price / yf_eps, default=np.nan)
            # Prefer yfinance-derived value when available
            if not np.isnan(yf_pe) and yf_pe > 0:
                pe = yf_pe
            else:
                # Otherwise, fill remaining missing inputs from yfinance
                if np.isnan(eps):
                    eps = _safe_float(
                        info.get("trailingEps")
                        or fast.get("epsTrailingTwelveMonths"),
                        default=np.nan,
                    )
                if np.isnan(close_px):
                    close_px = _safe_float(
                        fast.get("lastPrice")
                        or fast.get("regularMarketPrice")
                        or info.get("currentPrice")
                        or info.get("regularMarketPrice"),
                        default=np.nan,
                    )
                if np.isnan(pe) and eps > 0 and not np.isnan(close_px):
                    pe = _safe_float(close_px / eps, default=np.nan)
            # Final strict per-symbol check (ensures unique PEs if batch data was stale)
            best = _compute_pe_yf(symbol)
            if best is not None and best > 0:
                pe = float(best)
        except Exception as exc:
            if _is_network_block_error(exc):
                _mark_yahoo_temporarily_blocked()
            pass
        # Final defensive fallback: use analytics to compute PE and discount% when still unavailable
        if np.isnan(pe) or pe <= 0:
            try:
                metrics = fetch_stock_metrics(symbol).get("metrics", {})
                m_pe = _safe_float(metrics.get("pe_ratio"), default=np.nan)
                if not np.isnan(m_pe) and m_pe > 0:
                    pe = m_pe
                dval = _safe_float(metrics.get("discount_pct"), default=np.nan)
                if not np.isnan(dval):
                    disc = round(float(dval), 2)
            except Exception:
                pass
        # Ensure discount is available even if PE came from quotes
        if disc is None:
            try:
                metrics = fetch_stock_metrics(symbol).get("metrics", {})
                dval = _safe_float(metrics.get("discount_pct"), default=np.nan)
                if not np.isnan(dval):
                    disc = round(float(dval), 2)
            except Exception:
                pass

        output.append(
            {
                "symbol": symbol,
                "pe_ratio": round(float(pe), 2) if not np.isnan(pe) and pe > 0 else None,
                "discount_pct": disc,
            }
        )
    # Detect pathological case: identical non-null PE for all symbols; recompute with per-symbol quotes
    unique_values = set([row["pe_ratio"] for row in output])
    if len(unique_values) == 1 and (list(unique_values)[0] is not None) and len(symbols) > 1:
        strict_quote_map = {}
        for s in symbols:
            strict_quote_map.update(_fetch_quote_map([s]))
        strict_output = []
        for s in symbols:
            qrow = strict_quote_map.get(s, {}) or {}
            pe = _safe_float(qrow.get("trailingPE") or qrow.get("forwardPE"), default=np.nan)
            if np.isnan(pe):
                close_px = _safe_float(qrow.get("regularMarketPrice") or qrow.get("regularMarketPreviousClose"), default=np.nan)
                eps = _safe_float(qrow.get("epsTrailingTwelveMonths") or qrow.get("trailingEps"), default=np.nan)
                if eps > 0 and not np.isnan(close_px):
                    pe = _safe_float(close_px / eps, default=np.nan)
            # We do not compute discount here; keep behavior focused on PE for the chart
            strict_output.append({"symbol": s, "pe_ratio": round(float(pe), 2) if not np.isnan(pe) and pe > 0 else None})
        output = strict_output
    # If all PE values are still unavailable, make a final pass using analytics for each symbol
    if all((row.get("pe_ratio") is None) for row in output) and symbols:
        recovered = []
        for s in symbols:
            pe_val = None
            disc_val = None
            try:
                metrics = fetch_stock_metrics(s).get("metrics", {})
                m_pe = _safe_float(metrics.get("pe_ratio"), default=np.nan)
                if not np.isnan(m_pe) and m_pe > 0:
                    pe_val = round(float(m_pe), 2)
                dval = _safe_float(metrics.get("discount_pct"), default=np.nan)
                if not np.isnan(dval):
                    disc_val = round(float(dval), 2)
            except Exception:
                pass
            recovered.append({"symbol": s, "pe_ratio": pe_val, "discount_pct": disc_val})
        output = recovered
    _PE_CACHE[cache_key] = (now, output)
    return output


def compare_two_stocks(symbol_a: str, symbol_b: str):
    def calc(symbol):
        hist = _fetch_history(symbol, period="1y", interval="1d")
        if hist.empty:
            raise ValueError(f"No data for {symbol}")

        close = hist["Close"].dropna()
        returns = close.pct_change().dropna()

        one_year_return = ((close.iloc[-1] / close.iloc[0]) - 1) * 100
        volatility = returns.std() * np.sqrt(252) * 100
        sharpe = (returns.mean() / returns.std()) * np.sqrt(252) if returns.std() != 0 else 0

        return {
            "symbol": symbol,
            "one_year_return_pct": round(_safe_float(one_year_return), 2),
            "volatility_pct": round(_safe_float(volatility), 2),
            "sharpe": round(_safe_float(sharpe), 2),
        }

    a = calc(symbol_a)
    b = calc(symbol_b)
    winner = a["symbol"] if a["one_year_return_pct"] >= b["one_year_return_pct"] else b["symbol"]

    return {
        "stock_a": a,
        "stock_b": b,
        "more_profitable": winner,
    }


def gold_silver_correlation():
    gold = _fetch_history("GC=F", period="5y", interval="1d")
    silver = _fetch_history("SI=F", period="5y", interval="1d")

    if gold.empty or silver.empty:
        raise ValueError("Unable to fetch gold/silver data.")

    gold_close = gold[["Close"]].rename(columns={"Close": "gold"})
    silver_close = silver[["Close"]].rename(columns={"Close": "silver"})
    merged = gold_close.join(silver_close, how="inner").dropna()

    corr = merged["gold"].corr(merged["silver"])

    line_data = [
        {
            "date": idx.strftime("%Y-%m-%d"),
            "gold": round(_safe_float(row.gold), 2),
            "silver": round(_safe_float(row.silver), 2),
        }
        for idx, row in merged.iterrows()
    ]

    sample = merged.sample(min(300, len(merged)), random_state=42)
    scatter = [{"x": round(_safe_float(row.gold), 2), "y": round(_safe_float(row.silver), 2)} for row in sample.itertuples()]

    x = merged["gold"].values
    y = merged["silver"].values
    slope, intercept = np.polyfit(x, y, 1)
    x_line = np.linspace(float(merged["gold"].min()), float(merged["gold"].max()), 100)
    y_line = slope * x_line + intercept
    regression = [{"x": round(float(xv), 2), "y": round(float(yv), 2)} for xv, yv in zip(x_line, y_line)]

    return {
        "correlation": round(_safe_float(corr), 4),
        "line_graph": line_data,
        "scatter_graph": scatter,
        "linear_graph": regression,
    }


def _kmeans_numpy(X: np.ndarray, k: int, max_iter: int = 100, random_state: int = 42):
    rng = np.random.default_rng(random_state)
    n = X.shape[0]
    if k > n:
        k = n
    if k <= 1:
        return np.zeros(n, dtype=int), X[[0]].copy() if n else np.empty((0, X.shape[1]))

    idx = rng.choice(n, size=k, replace=False)
    centroids = X[idx].copy()

    for _ in range(max_iter):
        dists = ((X[:, None, :] - centroids[None, :, :]) ** 2).sum(axis=2)
        labels = dists.argmin(axis=1)
        new_centroids = centroids.copy()
        for c in range(k):
            members = X[labels == c]
            if len(members) == 0:
                new_centroids[c] = X[rng.integers(0, n)]
            else:
                new_centroids[c] = members.mean(axis=0)
        if np.allclose(new_centroids, centroids, atol=1e-7):
            break
        centroids = new_centroids
    return labels, centroids


def _pca_2d(X: np.ndarray):
    Xc = X - X.mean(axis=0, keepdims=True)
    U, S, _ = np.linalg.svd(Xc, full_matrices=False)
    if X.shape[1] == 1:
        coords = np.column_stack([U[:, 0] * S[0], np.zeros(X.shape[0])])
    else:
        coords = U[:, :2] * S[:2]
    return coords


def _umap_or_pca_2d(X: np.ndarray, method: str):
    method = (method or "pca").lower()
    if method != "umap":
        return _pca_2d(X), "pca"
    try:
        import umap  # type: ignore

        reducer = umap.UMAP(n_components=2, n_neighbors=min(10, max(2, X.shape[0] - 1)), min_dist=0.2, random_state=42)
        coords = reducer.fit_transform(X)
        return coords, "umap"
    except Exception:
        return _pca_2d(X), "pca"


def portfolio_kmeans_projection(stocks: list[dict], k: int = 3, method: str = "pca"):
    cache_key = f"{method.lower()}|{int(k)}|" + ",".join(sorted([s.get("symbol", "") for s in stocks]))
    now = time.time()
    cached = _CLUSTER_CACHE.get(cache_key)
    if cached:
        cached_result = cached[1]
        ttl = _CLUSTER_CACHE_TTL_SECONDS if (cached_result.get("items") or []) else _CLUSTER_FAIL_CACHE_TTL_SECONDS
        if (now - cached[0]) <= ttl:
            return cached_result

    rows = []
    skipped = 0
    symbol_map = {s["symbol"]: s for s in stocks if s.get("symbol")}
    symbols = list(symbol_map.keys())

    def _extract_hist(df, symbol):
        if df is None or len(df) == 0:
            return None
        try:
            # MultiIndex columns when multiple tickers are downloaded.
            if isinstance(df.columns, pd.MultiIndex):
                lvl0 = list(df.columns.get_level_values(0))
                lvl1 = list(df.columns.get_level_values(1))
                if symbol in lvl1:
                    sub = df.xs(symbol, axis=1, level=1)
                elif symbol in lvl0:
                    sub = df.xs(symbol, axis=1, level=0)
                else:
                    return None
            else:
                sub = df
            close_col = "Close" if "Close" in sub.columns else None
            if close_col is None:
                return None
            return sub.dropna(subset=[close_col]).copy()
        except Exception:
            return None

    batch_df = None
    if symbols and (not _is_yahoo_temporarily_blocked()):
        try:
            batch_df = yf.download(
                " ".join(symbols),
                period="1y",
                interval="1d",
                auto_adjust=False,
                progress=False,
                threads=False,
                group_by="ticker",
            )
        except Exception as exc:
            if _is_network_block_error(exc):
                _mark_yahoo_temporarily_blocked()
            batch_df = None

    for symbol in symbols:
        stock = symbol_map[symbol]
        hist = _extract_hist(batch_df, symbol)
        if hist is None or hist.empty:
            # Last-resort single-symbol fallback.
            try:
                hist = _fetch_history(symbol, period="1y", interval="1d")
                if hist is None or hist.empty:
                    skipped += 1
                    continue
                hist = hist.dropna(subset=["Close"]).copy()
            except Exception:
                skipped += 1
                continue

        close = hist["Close"]
        rets = close.pct_change().dropna()
        if rets.empty:
            skipped += 1
            continue

        drawdown = (close / close.cummax() - 1.0).min()
        momentum_3m = (close.iloc[-1] / close.iloc[max(0, len(close) - 63)] - 1) if len(close) > 63 else (close.iloc[-1] / close.iloc[0] - 1)
        downside = rets[rets < 0]
        avg_volume = float(hist["Volume"].tail(120).mean()) if "Volume" in hist.columns else 0.0

        rows.append(
            {
                "symbol": symbol,
                "company_name": stock.get("company_name", symbol),
                "sector": stock.get("sector", ""),
                "annual_return": float((close.iloc[-1] / close.iloc[0]) - 1),
                "volatility": float(rets.std() * np.sqrt(252)),
                "downside_volatility": float((downside.std() if len(downside) else 0.0) * np.sqrt(252)),
                "max_drawdown": float(drawdown),
                "momentum_3m": float(momentum_3m),
                "avg_volume_log": float(math.log1p(max(avg_volume, 0.0))),
                "current_price": float(close.iloc[-1]),
            }
        )

    if len(rows) < 2:
        # Do not cache failure responses aggressively. They are often transient
        # yfinance rate-limit/network issues and should recover quickly on retry.
        failure_result = {
            "items": [],
            "method_used": "pca",
            "k": max(1, min(k, len(rows))),
            "detail": f"Need at least 2 portfolio stocks with valid history for clustering. Valid: {len(rows)}, skipped: {skipped}. Some symbols may be temporarily rate-limited.",
            "skipped": skipped,
        }
        _CLUSTER_CACHE[cache_key] = (now, failure_result)
        return failure_result

    feature_cols = ["annual_return", "volatility", "downside_volatility", "max_drawdown", "momentum_3m", "avg_volume_log"]
    X = np.array([[r[c] for c in feature_cols] for r in rows], dtype=float)

    mu = X.mean(axis=0, keepdims=True)
    sigma = X.std(axis=0, keepdims=True)
    sigma[sigma == 0] = 1.0
    Xs = (X - mu) / sigma

    k = int(max(2, min(k, len(rows))))
    labels, _ = _kmeans_numpy(Xs, k=k, max_iter=100, random_state=42)
    coords, method_used = _umap_or_pca_2d(Xs, method=method)

    items = []
    for i, row in enumerate(rows):
        items.append(
            {
                "symbol": row["symbol"],
                "company_name": row["company_name"],
                "sector": row["sector"],
                "cluster": int(labels[i]),
                "x": float(coords[i, 0]),
                "y": float(coords[i, 1]),
                "annual_return_pct": round(row["annual_return"] * 100, 2),
                "volatility_pct": round(row["volatility"] * 100, 2),
                "max_drawdown_pct": round(row["max_drawdown"] * 100, 2),
                "momentum_3m_pct": round(row["momentum_3m"] * 100, 2),
                "current_price": round(row["current_price"], 2),
            }
        )

    cluster_summary = []
    for c in range(k):
        citems = [it for it in items if it["cluster"] == c]
        if not citems:
            continue
        cluster_summary.append(
            {
                "cluster": c,
                "count": len(citems),
                "avg_return_pct": round(float(np.mean([it["annual_return_pct"] for it in citems])), 2),
                "avg_volatility_pct": round(float(np.mean([it["volatility_pct"] for it in citems])), 2),
            }
        )

    result = {
        "items": items,
        "cluster_summary": cluster_summary,
        "method_used": method_used,
        "k": k,
        "detail": f"Computed from {len(rows)} stocks. Skipped {skipped} symbols due to unavailable/rate-limited data." if skipped else "",
        "skipped": skipped,
    }
    _CLUSTER_CACHE[cache_key] = (now, result)
    return result


def categorize_portfolio_risk(stocks: list[dict]):
    symbol_meta = {}
    for s in stocks:
        sym = (s.get("symbol") or "").strip().upper()
        if not sym:
            continue
        if sym not in symbol_meta:
            symbol_meta[sym] = {
                "company_name": s.get("company_name") or sym,
                "sector": s.get("sector") or "",
            }

    symbols_for_key = sorted(symbol_meta.keys())
    cache_key = ",".join(symbols_for_key)
    now = time.time()
    cached = _RISK_CACHE.get(cache_key)
    if cached and (now - cached[0]) <= _RISK_CACHE_TTL_SECONDS:
        return cached[1]

    if not symbols_for_key:
        result = {"items": [], "summary": {"Low": 0, "Medium": 0, "High": 0}}
        _RISK_CACHE[cache_key] = (now, result)
        return result

    def _extract_hist(df, symbol):
        if df is None or len(df) == 0:
            return None
        try:
            if isinstance(df.columns, pd.MultiIndex):
                lvl0 = list(df.columns.get_level_values(0))
                lvl1 = list(df.columns.get_level_values(1))
                if symbol in lvl1:
                    sub = df.xs(symbol, axis=1, level=1)
                elif symbol in lvl0:
                    sub = df.xs(symbol, axis=1, level=0)
                else:
                    return None
            else:
                sub = df
            close_col = "Close" if "Close" in sub.columns else None
            if close_col is None:
                return None
            return sub.dropna(subset=[close_col]).copy()
        except Exception:
            return None

    batch_df = None
    if symbols_for_key and (not _is_yahoo_temporarily_blocked()):
        try:
            batch_df = yf.download(
                " ".join(symbols_for_key),
                period="1y",
                interval="1d",
                auto_adjust=False,
                progress=False,
                threads=False,
                group_by="ticker",
            )
        except Exception as exc:
            if _is_network_block_error(exc):
                _mark_yahoo_temporarily_blocked()
            batch_df = None

    items = []
    for symbol in symbols_for_key:
        try:
            history = _extract_hist(batch_df, symbol)
            if history is None or history.empty:
                history = _fetch_history(symbol, period="1y", interval="1d")
            if history is None or history.empty:
                continue
            close = history["Close"].dropna()
            rets = close.pct_change().dropna()
            if rets.empty:
                continue

            annual_return_pct = float(((close.iloc[-1] / close.iloc[0]) - 1) * 100.0)
            # Risk score is daily return standard deviation in percent.
            volatility_pct = float(rets.std() * 100.0)

            if volatility_pct < 1.5:
                risk = "Low"
            elif volatility_pct < 3.0:
                risk = "Medium"
            else:
                risk = "High"

            items.append(
                {
                    "symbol": symbol,
                    "company_name": symbol_meta[symbol]["company_name"],
                    "sector": symbol_meta[symbol]["sector"],
                    "annual_return_pct": round(annual_return_pct, 2),
                    "volatility_pct": round(volatility_pct, 2),
                    "risk_category": risk,
                }
            )
        except Exception:
            continue

    summary = {"Low": 0, "Medium": 0, "High": 0}
    for item in items:
        summary[item["risk_category"]] = summary.get(item["risk_category"], 0) + 1

    result = {
        "items": items,
        "summary": summary,
    }
    _RISK_CACHE[cache_key] = (now, result)
    return result


def forecast_stock_prices(symbol: str, forecast_days: int = 30):
    normalized_symbol = (symbol or "").strip().upper()
    if not normalized_symbol:
        raise ValueError("Ticker symbol is required.")

    forecast_days = int(max(5, min(int(forecast_days or 30), 180)))
    history = _fetch_history(normalized_symbol, period="1y", interval="1d")
    if history is None or history.empty:
        raise ValueError("Unable to fetch historical prices for forecasting.")

    close = history["Close"].dropna().copy()
    if len(close) < 20:
        raise ValueError("Need at least 20 data points for forecasting.")

    x_train = np.arange(len(close), dtype=np.float64).reshape(-1, 1)
    y_train = close.values.astype(np.float64)

    model = LinearRegression()
    model.fit(x_train, y_train)

    x_future = np.arange(len(close), len(close) + forecast_days, dtype=np.float64).reshape(-1, 1)
    y_future = model.predict(x_future)

    last_date = pd.Timestamp(close.index[-1])
    future_dates = pd.bdate_range(last_date + pd.Timedelta(days=1), periods=forecast_days)

    history_points = [
        {"date": str(idx.date()), "price": round(float(val), 2)}
        for idx, val in close.tail(120).items()
    ]
    forecast_points = [
        {"date": str(idx.date()), "price": round(float(max(v, 0.01)), 2)}
        for idx, v in zip(future_dates, y_future)
    ]

    return {
        "symbol": normalized_symbol,
        "model": "linear_regression",
        "forecast_days": forecast_days,
        "current_price": round(float(close.iloc[-1]), 2),
        "predicted_price_end": round(float(max(y_future[-1], 0.01)), 2),
        "slope": round(float(model.coef_[0]), 6),
        "history": history_points,
        "forecast": forecast_points,
    }


def portfolio_next_day_predictions(stocks: list[dict]):
    symbol_meta = {}
    for s in stocks:
        sym = (s.get("symbol") or "").strip().upper()
        if not sym:
            continue
        if sym not in symbol_meta:
            symbol_meta[sym] = {
                "company_name": s.get("company_name") or sym,
                "sector": s.get("sector") or "",
            }

    symbols = sorted(symbol_meta.keys())
    items = []
    for symbol in symbols:
        try:
            history = _fetch_history(symbol, period="1y", interval="1d")
            if history is None or history.empty:
                continue
            close = history["Close"].dropna()
            if len(close) < 20:
                continue
            x_train = np.arange(len(close), dtype=np.float64).reshape(-1, 1)
            y_train = close.values.astype(np.float64)
            model = LinearRegression()
            model.fit(x_train, y_train)
            x_next = np.array([[len(close)]], dtype=np.float64)
            next_price = float(model.predict(x_next)[0])
            current_price = float(close.iloc[-1])
            items.append(
                {
                    "symbol": symbol,
                    "company_name": symbol_meta[symbol]["company_name"],
                    "sector": symbol_meta[symbol]["sector"],
                    "current_price": round(max(current_price, 0.01), 2),
                    "predicted_next_price": round(max(next_price, 0.01), 2),
                }
            )
        except Exception:
            continue
    return {"items": items}
