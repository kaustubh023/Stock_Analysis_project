import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api";
import ForecastGraph from "../components/ForecastGraph";

function BTCUSDForecastFeaturePage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError("");
      try {
        const res = await api.get("/crypto/btcusd-hourly/");
        setResult(res.data);
      } catch (err) {
        setError(err?.response?.data?.detail || "Failed to load BTC-USD forecast.");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const futureRows = (result?.dates || []).map((d, i) => ({
    date: d,
    price: result?.forecast_prices?.[i],
  }));

  return (
    <div className="stock-details-page">
      <header className="stock-nav">
        <div className="stock-brand"><span className="pulse-dot" /><strong>BTC-USD Hourly Forecast</strong></div>
        <button className="stock-back-btn" onClick={() => navigate("/other-features")}>Back</button>
      </header>
      <section className="stock-card">
        <h3>BTC-USD Price (Next 1 Hour)</h3>
        {loading && <p>Loading BTC-USD data...</p>}
        {error && <p className="error">{error}</p>}
        {result && !loading && !error && (
          <>
            <div className="metrics-grid" style={{ marginBottom: 12 }}>
              <div className="detail-metric neutral">
                <span className="detail-label mono">Current BTC-USD</span>
                <strong className="mono">${result.current_price}</strong>
                <small>Next 1 hour: ${result.forecast_prices?.[0]}</small>
              </div>
            </div>
            <div className="graph-card">
              <h4>BTC-USD Hourly Price (History & Next Hour)</h4>
              <ForecastGraph
                history={(result.history || []).map((r) => ({ date: r.date, price: r.price }))}
                future={futureRows}
              />
            </div>
          </>
        )}
      </section>
    </div>
  );
}

export default BTCUSDForecastFeaturePage;

