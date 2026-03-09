from __future__ import annotations

import json
import time
import math
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
    # Batch quote endpoint to reduce expensive per-symbol info pulls.
    if not symbols or _is_yahoo_temporarily_blocked():
        return {}
    try:
        symbol_list = ",".join(symbols)
        url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={quote_plus(symbol_list)}"
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=4) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        rows = (((payload or {}).get("quoteResponse") or {}).get("result")) or []
        out = {}
        for row in rows:
            sym = (row.get("symbol") or "").strip().upper()
            if sym:
                out[sym] = row
        return out
    except Exception as exc:
        if _is_network_block_error(exc):
            _mark_yahoo_temporarily_blocked()
        return {}


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
        if cached and cached_price > 0:
            return cached_payload
        raise ValueError("Unable to fetch stock data right now (Yahoo rate-limit or network issue). Please retry in a few seconds.")

    info = {}
    if ticker is not None:
        try:
            info = ticker.info or {}
        except Exception as exc:
            if _is_network_block_error(exc):
                _mark_yahoo_temporarily_blocked()
            info = {}
    quote_map = _fetch_quote_map([symbol])
    quote_row = quote_map.get(symbol, {})

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
        info.get("trailingPE")
        or info.get("forwardPE")
        or quote_row.get("trailingPE")
        or quote_row.get("forwardPE"),
        default=np.nan,
    )
    eps = _safe_float(info.get("trailingEps") or quote_row.get("epsTrailingTwelveMonths"), default=np.nan)
    market_cap = _safe_float(info.get("marketCap") or quote_row.get("marketCap"), default=np.nan)

    if np.isnan(pe_ratio) or pe_ratio <= 0:
        pe_ratio = _safe_float(current_price / eps, default=15.0) if eps > 0 else 15.0

    # Ensure EPS is usable even when fundamentals are unavailable/rate-limited.
    if np.isnan(eps) or eps <= 0:
        eps = _safe_float(current_price / pe_ratio, default=0.0) if pe_ratio > 0 else 0.0
    if eps <= 0:
        eps = _safe_float(current_price / 15.0, default=0.01)

    intrinsic = max(eps * 18, 0.01)
    discount_pct = ((intrinsic - current_price) / intrinsic) * 100

    if discount_pct >= 25:
        opportunity = "High"
    elif discount_pct >= 10:
        opportunity = "Medium"
    else:
        opportunity = "Low"

    history["pe"] = history["Close"].apply(lambda px: (px / eps) if eps > 0 else np.nan)
    history["discount"] = ((intrinsic - history["Close"]) / intrinsic) * 100
    history["opportunity"] = intrinsic - history["Close"]

    metrics = {
        "symbol": symbol,
        "company": info.get("longName") or info.get("shortName") or quote_row.get("longName") or quote_row.get("shortName") or symbol,
        "pe_ratio": round(pe_ratio, 2),
        "min_price": round(min_price, 2),
        "max_price": round(max_price, 2),
        "current_price": round(current_price, 2),
        "eps": round(eps, 2),
        "market_cap": int(market_cap) if not np.isnan(market_cap) else None,
        "intrinsic": round(intrinsic, 2),
        "discount_pct": round(discount_pct, 2),
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
    output = []
    if not symbols:
        return output
    symbols = [str(s).strip().upper() for s in symbols if str(s).strip()]
    cache_key = ",".join(sorted(symbols))
    now = time.time()
    cached = _PE_CACHE.get(cache_key)
    if cached and (now - cached[0]) <= _PE_CACHE_TTL_SECONDS:
        return cached[1]

    latest_close = {}
    hist = _fetch_history(" ".join(symbols), period="7d", interval="1d")
    if hist is not None and not hist.empty:
        try:
            if isinstance(hist.columns, pd.MultiIndex):
                lvl0 = list(hist.columns.get_level_values(0))
                lvl1 = list(hist.columns.get_level_values(1))
                for symbol in symbols:
                    sub = None
                    if symbol in lvl1:
                        sub = hist.xs(symbol, axis=1, level=1)
                    elif symbol in lvl0:
                        sub = hist.xs(symbol, axis=1, level=0)
                    if sub is not None and "Close" in sub.columns:
                        close = sub["Close"].dropna()
                        if not close.empty:
                            latest_close[symbol] = _safe_float(close.iloc[-1], default=np.nan)
            elif "Close" in hist.columns and len(symbols) == 1:
                close = hist["Close"].dropna()
                if not close.empty:
                    latest_close[symbols[0]] = _safe_float(close.iloc[-1], default=np.nan)
        except Exception:
            latest_close = {}

    quote_map = _fetch_quote_map(symbols)

    for symbol in symbols:
        pe = np.nan
        eps = np.nan
        close_px = latest_close.get(symbol, np.nan)
        qrow = quote_map.get(symbol, {})
        pe = _safe_float(qrow.get("trailingPE") or qrow.get("forwardPE"), default=np.nan)
        eps = _safe_float(qrow.get("epsTrailingTwelveMonths"), default=np.nan)
        if np.isnan(close_px):
            close_px = _safe_float(
                qrow.get("regularMarketPrice") or qrow.get("regularMarketPreviousClose"),
                default=np.nan,
            )
        try:
            if _is_yahoo_temporarily_blocked():
                raise RuntimeError("yahoo temporarily blocked")
            ticker = yf.Ticker(symbol)
            info = ticker.info or {}
            fast = {}
            try:
                fast = dict(ticker.fast_info or {})
            except Exception as exc:
                if _is_network_block_error(exc):
                    _mark_yahoo_temporarily_blocked()
                fast = {}

            if np.isnan(pe):
                pe = _safe_float(
                    info.get("trailingPE")
                    or info.get("forwardPE")
                    or fast.get("trailingPE")
                    or fast.get("forwardPE"),
                    default=np.nan,
                )
            if np.isnan(eps):
                eps = _safe_float(info.get("trailingEps") or fast.get("epsTrailingTwelveMonths"), default=np.nan)
            if np.isnan(close_px):
                close_px = _safe_float(
                    fast.get("lastPrice")
                    or fast.get("regularMarketPrice")
                    or fast.get("previousClose"),
                    default=np.nan,
                )
            if np.isnan(pe) and eps > 0 and not np.isnan(close_px):
                pe = _safe_float(close_px / eps, default=np.nan)
        except Exception as exc:
            if _is_network_block_error(exc):
                _mark_yahoo_temporarily_blocked()
            pass

        output.append(
            {
                "symbol": symbol,
                "pe_ratio": round(float(pe), 2) if not np.isnan(pe) and pe > 0 else None,
            }
        )
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
