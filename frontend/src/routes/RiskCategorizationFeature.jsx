import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api";
import AppShell from "../components/AppShell";

function RiskCategorizationFeaturePage() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError("");
      try {
        const res = await api.get("/stock/risk-categorization/", { timeout: 15000 });
        setData(res.data);
      } catch (err) {
        if (err?.code === "ECONNABORTED") {
          setError("Risk categorization request timed out. Please retry.");
        } else {
          setError(err?.response?.data?.detail || "Unable to fetch risk categories.");
        }
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const low = (data?.items || []).filter((i) => i.risk_category === "Low");
  const medium = (data?.items || []).filter((i) => i.risk_category === "Medium");
  const high = (data?.items || []).filter((i) => i.risk_category === "High");

  return (
    <AppShell
      eyebrow="Feature Hub / Risk"
      title="Risk categorization"
      subtitle="Review how your holdings cluster into low, medium and high-risk bands based on return and volatility."
      actions={<button className="ghost-button" onClick={() => navigate("/other-features")}>Back to hub</button>}
    >
      {loading && <section className="card"><p>Loading risk profile...</p></section>}
      {error && <section className="card"><p className="error">{error}</p></section>}
      {data && (
        <section className="card">
          <div className="inline inline-compact">
            <span className="chip mono">Low: {data.summary?.Low || 0}</span>
            <span className="chip mono">Medium: {data.summary?.Medium || 0}</span>
            <span className="chip mono">High: {data.summary?.High || 0}</span>
          </div>
          <div className="risk-grid grid three">
            <div className="risk-col">
              <div className="risk-head">
                <h3 className="risk-title low">Low Risk</h3>
                <span className="risk-pill low">{low.length}</span>
              </div>
              <div className="stock-list">
                {low.map((item) => (
                  <div key={item.symbol} className="stock-item">
                    <div>{item.company_name}</div>
                    <small>{item.symbol} | {item.sector} | Return {item.annual_return_pct}% | Volatility {item.volatility_pct}%</small>
                  </div>
                ))}
                {low.length === 0 && <p className="empty-state">No low-risk stocks.</p>}
              </div>
            </div>
            <div className="risk-col">
              <div className="risk-head">
                <h3 className="risk-title med">Medium Risk</h3>
                <span className="risk-pill med">{medium.length}</span>
              </div>
              <div className="stock-list">
                {medium.map((item) => (
                  <div key={item.symbol} className="stock-item">
                    <div>{item.company_name}</div>
                    <small>{item.symbol} | {item.sector} | Return {item.annual_return_pct}% | Volatility {item.volatility_pct}%</small>
                  </div>
                ))}
                {medium.length === 0 && <p className="empty-state">No medium-risk stocks.</p>}
              </div>
            </div>
            <div className="risk-col">
              <div className="risk-head">
                <h3 className="risk-title high">High Risk</h3>
                <span className="risk-pill high">{high.length}</span>
              </div>
              <div className="stock-list">
                {high.map((item) => (
                  <div key={item.symbol} className="stock-item">
                    <div>{item.company_name}</div>
                    <small>{item.symbol} | {item.sector} | Return {item.annual_return_pct}% | Volatility {item.volatility_pct}%</small>
                  </div>
                ))}
                {high.length === 0 && <p className="empty-state">No high-risk stocks.</p>}
              </div>
            </div>
          </div>
        </section>
      )}
    </AppShell>
  );
}

export default RiskCategorizationFeaturePage;
