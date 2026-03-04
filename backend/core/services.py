from __future__ import annotations

import time
import numpy as np
import pandas as pd
import yfinance as yf

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
    should_query_yf = len(q) >= 2
    if should_query_yf:
        try:
            search = yf.Search(query=query, max_results=20)
            candidates.extend(search.quotes or [])
        except Exception:
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
        except Exception:
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
    now = time.time()
    cached = _ANALYTICS_CACHE.get(symbol)
    if cached and (now - cached[0]) <= _ANALYTICS_CACHE_TTL_SECONDS:
        cached_payload = cached[1]
        cached_price = _safe_float(cached_payload.get("metrics", {}).get("current_price"), default=0.0)
        # Don't keep serving stale empty-fallback payloads.
        if cached_price > 0:
            return cached_payload

    ticker = yf.Ticker(symbol)
    try:
        history = ticker.history(period="1y", interval="1d", auto_adjust=False)
    except Exception:
        if cached:
            return cached[1]
        # Final fallback payload so API never hard-fails on rate limit.
        return _empty_stock_payload(symbol)

    info = {}
    try:
        info = ticker.info or {}
    except Exception:
        info = {}

    if history.empty:
        if cached:
            return cached[1]
        fallback = _empty_stock_payload(symbol, info.get("longName") or info.get("shortName"))
        return fallback

    history = history.dropna(subset=["Close"]).copy()
    history["date"] = history.index.strftime("%Y-%m-%d")

    close = history["Close"]
    current_price = _safe_float(close.iloc[-1])
    min_price = _safe_float(close.min())
    max_price = _safe_float(close.max())

    pe_ratio = _safe_float(info.get("trailingPE") or info.get("forwardPE"), default=np.nan)
    eps = _safe_float(info.get("trailingEps"), default=np.nan)
    market_cap = _safe_float(info.get("marketCap"), default=np.nan)

    if np.isnan(eps) or eps <= 0:
        eps = _safe_float(current_price / pe_ratio, default=0.0) if not np.isnan(pe_ratio) and pe_ratio > 0 else 0.0

    if np.isnan(pe_ratio) or pe_ratio <= 0:
        pe_ratio = _safe_float(current_price / eps, default=15.0) if eps > 0 else 15.0

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
        "company": info.get("longName") or info.get("shortName") or symbol,
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
    for symbol in symbols:
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info or {}
            pe = _safe_float(info.get("trailingPE") or info.get("forwardPE"), default=np.nan)
            if np.isnan(pe):
                hist = ticker.history(period="5d")
                if not hist.empty:
                    close = _safe_float(hist["Close"].iloc[-1])
                    eps = _safe_float(info.get("trailingEps"), default=np.nan)
                    pe = _safe_float(close / eps, default=15.0) if eps > 0 else 15.0
            output.append(
                {
                    "symbol": symbol,
                    "pe_ratio": round(pe if not np.isnan(pe) else 15.0, 2),
                }
            )
        except Exception:
            output.append({"symbol": symbol, "pe_ratio": 15.0})
    return output


def compare_two_stocks(symbol_a: str, symbol_b: str):
    def calc(symbol):
        hist = yf.Ticker(symbol).history(period="1y", interval="1d")
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
    gold = yf.Ticker("GC=F").history(period="5y", interval="1d")
    silver = yf.Ticker("SI=F").history(period="5y", interval="1d")

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
