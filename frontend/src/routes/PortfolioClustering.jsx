import { useEffect, useState } from "react";
import { Cell, CartesianGrid, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis } from "recharts";
import { useNavigate } from "react-router-dom";
import api from "../api";
import AppShell from "../components/AppShell";

function PortfolioClusteringPage() {
  const navigate = useNavigate();
  const [k, setK] = useState(3);
  const [method, setMethod] = useState("pca");
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const clusterColors = ["#00e5b0", "#818cf8", "#f7c948", "#ff4d6d", "#7dd3fc", "#a78bfa"];

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await api.get(`/portfolio/clustering/?k=${k}&method=${method}`);
      setData(res.data);
    } catch (err) {
      setError(err?.response?.data?.detail || "Unable to compute clustering.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [k, method]);

  return (
    <AppShell
      eyebrow="Analytics / Cluster Lab"
      title="Portfolio clustering"
      subtitle="Project your portfolio into clusters and inspect how similar stocks group together under different projection methods."
      actions={<button className="ghost-button" onClick={() => navigate("/dashboard")}>Back to dashboard</button>}
    >
      <section className="card">
        <div className="inline inline-compact">
          <label className="mono">Clusters (k)</label>
          <select value={k} onChange={(e) => setK(Number(e.target.value))}>
            {[2, 3, 4, 5, 6].map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
          <label className="mono">Projection</label>
          <select value={method} onChange={(e) => setMethod(e.target.value)}>
            <option value="pca">PCA</option>
            <option value="umap">UMAP</option>
          </select>
          <button onClick={load}>Refresh</button>
        </div>
      </section>

      {loading && <section className="card"><p>Computing clusters...</p></section>}
      {error && <section className="card"><p className="error">{error}</p></section>}

      {data && (
        <>
          {data.detail && <section className="card"><p>{data.detail}</p></section>}
          {data.items && data.items.length > 0 && (
            <section className="card">
              <h3>Portfolio clusters ({String(data.method_used).toUpperCase()} + KMeans)</h3>
              <ResponsiveContainer width="100%" height={360}>
                <ScatterChart>
                  <CartesianGrid stroke="#2a3458" />
                  <XAxis type="number" dataKey="x" name="Component 1" tick={{ fill: "#97aacd" }} axisLine={false} tickLine={false} />
                  <YAxis type="number" dataKey="y" name="Component 2" tick={{ fill: "#97aacd" }} axisLine={false} tickLine={false} />
                  <Tooltip
                    cursor={{ strokeDasharray: "3 3" }}
                    contentStyle={{ background: "#0f1528", border: "1px solid #2f3b63", borderRadius: "8px" }}
                    labelStyle={{ color: "#7f8db0", fontFamily: "DM Mono" }}
                    itemStyle={{ color: "#dfe8ff", fontWeight: 700 }}
                  />
                  <Scatter data={data.items}>
                    {data.items.map((entry, index) => (
                      <Cell key={`c-${index}`} fill={clusterColors[entry.cluster % clusterColors.length]} />
                    ))}
                  </Scatter>
                </ScatterChart>
              </ResponsiveContainer>
            </section>
          )}
          {data.cluster_summary && data.cluster_summary.length > 0 && (
            <section className="card">
              <h3>Cluster summary</h3>
              <div className="stock-metrics">
                {data.cluster_summary.map((s) => (
                  <div key={s.cluster} className="detail-metric neutral">
                    <span className="detail-label mono">Cluster {s.cluster}</span>
                    <strong className="mono">Stocks: {s.count}</strong>
                    <small>Avg Return: {s.avg_return_pct}% | Avg Volatility: {s.avg_volatility_pct}%</small>
                  </div>
                ))}
              </div>
            </section>
          )}
        </>
      )}
    </AppShell>
  );
}

export default PortfolioClusteringPage;
