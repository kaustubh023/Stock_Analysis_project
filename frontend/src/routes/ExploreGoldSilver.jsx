import { useEffect, useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis } from "recharts";
import { useNavigate } from "react-router-dom";
import api from "../api";

function ExploreGoldSilverPage() {
  const navigate = useNavigate();
  const [goldSilver, setGoldSilver] = useState(null);
  const [commodityView, setCommodityView] = useState("gold");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError("");
      try {
        const res = await api.get("/commodities/gold-silver-correlation/");
        setGoldSilver(res.data);
      } catch (err) {
        setError(err?.response?.data?.detail || "Unable to load gold/silver analysis.");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  return (
    <div className="page dashboard-page">
      <header className="topbar dashboard-topbar">
        <div>
          <p className="dashboard-brand mono"><span className="pulse-dot" /> Explore</p>
          <h2>Gold/Silver Correlation</h2>
          <p>Dedicated commodity analytics page</p>
        </div>
        <div className="inline">
          <button onClick={() => navigate("/other-features")}>Back to Other Features</button>
        </div>
      </header>

      {loading && <section className="card"><p>Loading gold/silver analysis...</p></section>}
      {error && <section className="card"><p className="error">{error}</p></section>}

      {goldSilver && (
        <section className="card">
          <h3>Gold vs Silver (5 Years) Correlation: {goldSilver.correlation}</h3>
          <div className="inline">
            <select value={commodityView} onChange={(e) => setCommodityView(e.target.value)}>
              <option value="gold">Gold</option>
              <option value="silver">Silver</option>
            </select>
          </div>
          <div className="grid three">
            <GraphCard title="Gold & Silver Correlation Graph">
              <ResponsiveContainer width="100%" height={260}>
                <LineChart data={goldSilver.line_graph}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" hide />
                  <YAxis />
                  <Tooltip contentStyle={{ background: "#0f1528", border: "1px solid #2f3b63", borderRadius: "8px" }} labelStyle={{ color: "#7f8db0", fontFamily: "DM Mono" }} itemStyle={{ color: "#dfe8ff", fontWeight: 700 }} />
                  <Legend />
                  <Line type="monotone" dataKey="gold" stroke="#b8860b" dot={false} />
                  <Line type="monotone" dataKey="silver" stroke="#708090" dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </GraphCard>

            <GraphCard title="Scatter Graph">
              <ResponsiveContainer width="100%" height={260}>
                <ScatterChart>
                  <CartesianGrid />
                  <XAxis type="number" dataKey="x" name={commodityView === "gold" ? "Gold" : "Silver"} />
                  <YAxis type="number" dataKey="y" name={commodityView === "gold" ? "Silver" : "Gold"} />
                  <Tooltip cursor={{ strokeDasharray: "3 3" }} contentStyle={{ background: "#0f1528", border: "1px solid #2f3b63", borderRadius: "8px" }} labelStyle={{ color: "#7f8db0", fontFamily: "DM Mono" }} itemStyle={{ color: "#dfe8ff", fontWeight: 700 }} />
                  <Scatter
                    data={commodityView === "gold" ? goldSilver.scatter_graph : goldSilver.scatter_graph.map((p) => ({ x: p.y, y: p.x }))}
                    fill={commodityView === "gold" ? "#b8860b" : "#c0c0c0"}
                  />
                </ScatterChart>
              </ResponsiveContainer>
            </GraphCard>

            <GraphCard title="Linear Regression Graph">
              <ResponsiveContainer width="100%" height={260}>
                <LineChart data={buildCommodityRegression(goldSilver.line_graph, commodityView)}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="x" />
                  <YAxis />
                  <Tooltip contentStyle={{ background: "#0f1528", border: "1px solid #2f3b63", borderRadius: "8px" }} labelStyle={{ color: "#7f8db0", fontFamily: "DM Mono" }} itemStyle={{ color: "#dfe8ff", fontWeight: 700 }} />
                  <Line type="monotone" dataKey="y" stroke={commodityView === "gold" ? "#b8860b" : "#c0c0c0"} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </GraphCard>
          </div>
        </section>
      )}
    </div>
  );
}

function buildCommodityRegression(lineData, mode) {
  const points = (lineData || [])
    .map((row) => ({
      x: Number(mode === "gold" ? row.gold : row.silver),
      y: Number(mode === "gold" ? row.silver : row.gold),
    }))
    .filter((p) => Number.isFinite(p.x) && Number.isFinite(p.y));

  if (points.length < 2) return [];
  const n = points.length;
  const sumX = points.reduce((a, p) => a + p.x, 0);
  const sumY = points.reduce((a, p) => a + p.y, 0);
  const sumXY = points.reduce((a, p) => a + p.x * p.y, 0);
  const sumXX = points.reduce((a, p) => a + p.x * p.x, 0);
  const den = n * sumXX - sumX * sumX;
  const slope = den !== 0 ? (n * sumXY - sumX * sumY) / den : 0;
  const intercept = (sumY - slope * sumX) / n;
  const minX = Math.min(...points.map((p) => p.x));
  const maxX = Math.max(...points.map((p) => p.x));
  if (!Number.isFinite(minX) || !Number.isFinite(maxX) || minX === maxX) {
    return points.slice(0, 2);
  }

  const out = [];
  const steps = 100;
  const step = (maxX - minX) / (steps - 1);
  for (let i = 0; i < steps; i += 1) {
    const x = minX + step * i;
    out.push({ x: Number(x.toFixed(2)), y: Number((slope * x + intercept).toFixed(2)) });
  }
  return out;
}

function GraphCard({ title, children }) {
  return (
    <div className="graph-card">
      <h4>{title}</h4>
      {children}
    </div>
  );
}

export default ExploreGoldSilverPage;
