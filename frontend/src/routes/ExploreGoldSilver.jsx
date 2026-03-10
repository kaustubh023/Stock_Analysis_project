import { useEffect, useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis } from "recharts";
import { useNavigate } from "react-router-dom";
import api from "../api";
import AppShell from "../components/AppShell";

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
    <AppShell
      eyebrow="Feature Hub / Commodities"
      title="Gold and silver correlation"
      subtitle="Use the shared app shell to inspect commodity correlation with line, scatter and regression views."
      actions={<button className="ghost-button" onClick={() => navigate("/other-features")}>Back to hub</button>}
    >
      {loading && <section className="card"><p>Loading gold/silver analysis...</p></section>}
      {error && <section className="card"><p className="error">{error}</p></section>}

      {goldSilver && (
        <section className="card">
          <div className="section-head">
            <div>
              <span className="section-kicker mono">Commodity lens</span>
              <h3>Gold vs silver (5 years)</h3>
            </div>
            <span className="chip mono">Correlation: {goldSilver.correlation}</span>
          </div>
          <div className="inline inline-compact">
            <select value={commodityView} onChange={(e) => setCommodityView(e.target.value)}>
              <option value="gold">Gold</option>
              <option value="silver">Silver</option>
            </select>
          </div>
          <div className="grid three">
            <GraphCard title="Gold & Silver Correlation Graph">
              <ResponsiveContainer width="100%" height={260}>
                <LineChart data={goldSilver.line_graph}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#253351" />
                  <XAxis dataKey="date" hide />
                  <YAxis tick={{ fill: "#97aacd" }} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={{ background: "#0f1528", border: "1px solid #2f3b63", borderRadius: "8px" }} labelStyle={{ color: "#7f8db0", fontFamily: "DM Mono" }} itemStyle={{ color: "#dfe8ff", fontWeight: 700 }} />
                  <Legend />
                  <Line type="monotone" dataKey="gold" stroke="#d4a017" dot={false} />
                  <Line type="monotone" dataKey="silver" stroke="#c7d2da" dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </GraphCard>

            <GraphCard title="Scatter Graph">
              <ResponsiveContainer width="100%" height={260}>
                <ScatterChart>
                  <CartesianGrid stroke="#253351" />
                  <XAxis type="number" dataKey="x" name={commodityView === "gold" ? "Gold" : "Silver"} tick={{ fill: "#97aacd" }} axisLine={false} tickLine={false} />
                  <YAxis type="number" dataKey="y" name={commodityView === "gold" ? "Silver" : "Gold"} tick={{ fill: "#97aacd" }} axisLine={false} tickLine={false} />
                  <Tooltip cursor={{ strokeDasharray: "3 3" }} contentStyle={{ background: "#0f1528", border: "1px solid #2f3b63", borderRadius: "8px" }} labelStyle={{ color: "#7f8db0", fontFamily: "DM Mono" }} itemStyle={{ color: "#dfe8ff", fontWeight: 700 }} />
                  <Scatter
                    data={commodityView === "gold" ? goldSilver.scatter_graph : goldSilver.scatter_graph.map((point) => ({ x: point.y, y: point.x }))}
                    fill={commodityView === "gold" ? "#d4a017" : "#c7d2da"}
                  />
                </ScatterChart>
              </ResponsiveContainer>
            </GraphCard>

            <GraphCard title="Linear Regression Graph">
              <ResponsiveContainer width="100%" height={260}>
                <LineChart data={buildCommodityRegression(goldSilver.line_graph, commodityView)}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#253351" />
                  <XAxis dataKey="x" tick={{ fill: "#97aacd" }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: "#97aacd" }} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={{ background: "#0f1528", border: "1px solid #2f3b63", borderRadius: "8px" }} labelStyle={{ color: "#7f8db0", fontFamily: "DM Mono" }} itemStyle={{ color: "#dfe8ff", fontWeight: 700 }} />
                  <Line type="monotone" dataKey="y" stroke={commodityView === "gold" ? "#d4a017" : "#c7d2da"} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </GraphCard>
          </div>
        </section>
      )}
    </AppShell>
  );
}

function buildCommodityRegression(lineData, mode) {
  const points = (lineData || [])
    .map((row) => ({
      x: Number(mode === "gold" ? row.gold : row.silver),
      y: Number(mode === "gold" ? row.silver : row.gold),
    }))
    .filter((point) => Number.isFinite(point.x) && Number.isFinite(point.y));

  if (points.length < 2) return [];
  const n = points.length;
  const sumX = points.reduce((a, point) => a + point.x, 0);
  const sumY = points.reduce((a, point) => a + point.y, 0);
  const sumXY = points.reduce((a, point) => a + point.x * point.y, 0);
  const sumXX = points.reduce((a, point) => a + point.x * point.x, 0);
  const den = n * sumXX - sumX * sumX;
  const slope = den !== 0 ? (n * sumXY - sumX * sumY) / den : 0;
  const intercept = (sumY - slope * sumX) / n;
  const minX = Math.min(...points.map((point) => point.x));
  const maxX = Math.max(...points.map((point) => point.x));

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
