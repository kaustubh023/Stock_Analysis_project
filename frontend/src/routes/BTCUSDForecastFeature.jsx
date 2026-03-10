import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api";
import ForecastGraph from "../components/ForecastGraph";
import AppShell from "../components/AppShell";

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
    <AppShell
      eyebrow="Feature Hub / Crypto"
      title="BTC-USD hourly forecast"
      subtitle="Review the latest BTC-USD price history and the projected next-hour move without affecting the rest of the app flow."
      actions={<button className="ghost-button" onClick={() => navigate("/other-features")}>Back to hub</button>}
    >
      <section className="card">
        <h3>BTC-USD price (next 1 hour)</h3>
        {loading && <p>Loading BTC-USD data...</p>}
        {error && <p className="error">{error}</p>}
        {result && !loading && !error && (
          <>
            <div className="metrics-grid">
              <div className="detail-metric neutral">
                <span className="detail-label mono">Current BTC-USD</span>
                <strong className="mono">${result.current_price}</strong>
                <small>Next 1 hour: ${result.forecast_prices?.[0]}</small>
              </div>
            </div>
            <div className="graph-card">
              <h4>BTC-USD hourly price</h4>
              <ForecastGraph
                history={(result.history || []).map((r) => ({ date: r.date, price: r.price }))}
                future={futureRows}
              />
            </div>
          </>
        )}
      </section>
    </AppShell>
  );
}

export default BTCUSDForecastFeaturePage;
