import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import StockSearch from "../components/StockSearch";
import ForecastInput from "../components/ForecastInput";
import ForecastGraph from "../components/ForecastGraph";
import ForecastResult from "../components/ForecastResult";

function StockForecastFeaturePage() {
  const navigate = useNavigate();
  const [symbol, setSymbol] = useState("");
  const [forecastDays, setForecastDays] = useState(30);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [portfolioPred, setPortfolioPred] = useState({ items: [] });
  const [loadingPortfolio, setLoadingPortfolio] = useState(false);
  const [arimaResult, setArimaResult] = useState(null);

  const submit = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await api.post("/forecast/", {
        ticker: symbol.trim().toUpperCase(),
        days: Number(forecastDays),
      });
      setArimaResult(res.data);
    } catch (err) {
      setError(err?.response?.data?.detail || "Forecast failed.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const load = async () => {
      setLoadingPortfolio(true);
      try {
        const res = await api.get("/stock/portfolio-forecast-next-day/");
        setPortfolioPred(res.data || { items: [] });
      } catch (err) {
        // Silent; keep section optional
      } finally {
        setLoadingPortfolio(false);
      }
    };
    load();
  }, []);

  const chartRows = useMemo(() => {
    const items = portfolioPred?.items || [];
    // Build entries like: { symbol, Current: X, Next: Y }
    return items.map((it) => ({
      symbol: it.symbol,
      Current: it.current_price,
      Next: it.predicted_next_price,
    }));
  }, [portfolioPred]);

  return (
    <div className="stock-details-page">
      <header className="stock-nav">
        <div className="stock-brand"><span className="pulse-dot" /><strong>Stock Forecasting</strong></div>
        <button className="stock-back-btn" onClick={() => navigate("/other-features")}>Back</button>
      </header>
      <section className="stock-card">
        <div className="inline">
          <div style={{ flex: 2 }}>
            <StockSearch value={symbol} onSelect={(sym) => setSymbol(sym)} />
          </div>
          <div style={{ flex: 1 }}>
            <ForecastInput value={forecastDays} onChange={setForecastDays} />
          </div>
          <button onClick={submit} disabled={loading || !symbol.trim()}>
            {loading ? "Forecasting..." : "Run Forecast"}
          </button>
        </div>
        {error && <p className="error">{error}</p>}
        {arimaResult && (
          <>
            <ForecastResult
              symbol={symbol}
              days={forecastDays}
              current={arimaResult.current_price}
              predicted={arimaResult.forecast_prices?.[arimaResult.forecast_prices.length - 1]}
            />
            <div className="graph-card" style={{ marginTop: 12 }}>
              <h4>Stock Price Forecast</h4>
              <ForecastGraph
                history={(arimaResult.history || [])}
                future={(arimaResult.dates || []).map((d, i) => ({ date: d, price: arimaResult.forecast_prices?.[i] }))}
              />
            </div>
          </>
        )}
      </section>
      <section className="stock-card">
        <h3>Next-Day Predictions (Your Portfolio)</h3>
        {loadingPortfolio && <p>Loading portfolio predictions...</p>}
        {!loadingPortfolio && (portfolioPred?.items || []).length === 0 && (
          <p className="note">No portfolio predictions available.</p>
        )}
        {(portfolioPred?.items || []).length > 0 && (
          <>
            <div className="metrics-grid" style={{ marginBottom: 10 }}>
              {(portfolioPred.items || []).map((it) => (
                <div key={it.symbol} className="detail-metric neutral">
                  <span className="detail-label mono">{it.company_name} ({it.symbol})</span>
                  <strong className="mono">Current: ₹{it.current_price}</strong>
                  <small>Next Day: ₹{it.predicted_next_price}</small>
                </div>
              ))}
            </div>
            <div className="graph-card">
              <h4>Current vs Next-Day (Bar)</h4>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={chartRows}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="symbol" />
                  <YAxis />
                  <Tooltip contentStyle={{ background: "#0f1528", border: "1px solid #2f3b63", borderRadius: "8px" }} labelStyle={{ color: "#7f8db0", fontFamily: "DM Mono" }} itemStyle={{ color: "#dfe8ff", fontWeight: 700 }} />
                  <Bar dataKey="Current" fill="#22d3ee" stroke="#67e8f9" radius={[6, 6, 0, 0]} />
                  <Bar dataKey="Next" fill="#a78bfa" stroke="#c4b5fd" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </>
        )}
      </section>
    </div>
  );
}

export default StockForecastFeaturePage;
