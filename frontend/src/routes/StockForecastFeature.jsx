import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import api from "../api";
import StockSearch from "../components/StockSearch";
import ForecastInput from "../components/ForecastInput";
import ForecastGraph from "../components/ForecastGraph";
import ForecastResult from "../components/ForecastResult";
import AppShell from "../components/AppShell";

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
      } catch {
        // Keep this section optional if the endpoint is unavailable.
      } finally {
        setLoadingPortfolio(false);
      }
    };
    load();
  }, []);

  const chartRows = useMemo(
    () => (portfolioPred?.items || []).map((it) => ({
      symbol: it.symbol,
      Current: it.current_price,
      Next: it.predicted_next_price,
    })),
    [portfolioPred]
  );

  return (
    <AppShell
      eyebrow="Feature Hub / Forecasting"
      title="Stock forecasting"
      subtitle="Run a forecast for an individual symbol and review the next-day forecast cards for your current portfolio."
      actions={<button className="ghost-button" onClick={() => navigate("/other-features")}>Back to hub</button>}
    >
      <section className="card">
        <div className="inline inline-compact">
          <div style={{ flex: 2 }}>
            <StockSearch value={symbol} onSelect={(sym) => setSymbol(sym)} />
          </div>
          <div style={{ flex: 1 }}>
            <ForecastInput value={forecastDays} onChange={setForecastDays} />
          </div>
          <button onClick={submit} disabled={loading || !symbol.trim()}>
            {loading ? "Forecasting..." : "Run forecast"}
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
            <div className="graph-card">
              <h4>Stock price forecast</h4>
              <ForecastGraph
                history={arimaResult.history || []}
                future={(arimaResult.dates || []).map((date, index) => ({
                  date,
                  price: arimaResult.forecast_prices?.[index],
                }))}
              />
            </div>
          </>
        )}
      </section>

      <section className="card">
        <h3>Next-day predictions (your portfolio)</h3>
        {loadingPortfolio && <p>Loading portfolio predictions...</p>}
        {!loadingPortfolio && (portfolioPred?.items || []).length === 0 && (
          <p className="note">No portfolio predictions available.</p>
        )}
        {(portfolioPred?.items || []).length > 0 && (
          <>
            <div className="metrics-grid">
              {(portfolioPred.items || []).map((it) => (
                <div key={it.symbol} className="detail-metric neutral">
                  <span className="detail-label mono">{it.company_name} ({it.symbol})</span>
                  <strong className="mono">Current: Rs {it.current_price}</strong>
                  <small>Next day: Rs {it.predicted_next_price}</small>
                </div>
              ))}
            </div>
            <div className="graph-card">
              <h4>Current vs next-day</h4>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={chartRows}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#253351" />
                  <XAxis dataKey="symbol" tick={{ fill: "#97aacd" }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: "#97aacd" }} axisLine={false} tickLine={false} />
                  <Tooltip
                    contentStyle={{ background: "#0f1528", border: "1px solid #2f3b63", borderRadius: "8px" }}
                    labelStyle={{ color: "#7f8db0", fontFamily: "DM Mono" }}
                    itemStyle={{ color: "#dfe8ff", fontWeight: 700 }}
                  />
                  <Bar dataKey="Current" fill="#1dd3b0" stroke="#57f3d7" radius={[6, 6, 0, 0]} />
                  <Bar dataKey="Next" fill="#7c82ff" stroke="#a5a9ff" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </>
        )}
      </section>
    </AppShell>
  );
}

export default StockForecastFeaturePage;
