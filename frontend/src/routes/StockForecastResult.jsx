import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useLocation, useNavigate } from "react-router-dom";
import AppShell from "../components/AppShell";

function StockForecastResultPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const payload = location.state?.payload;

  if (!payload) {
    return (
      <AppShell
        eyebrow="Feature Hub / Forecast Result"
        title="Forecast result"
        subtitle="No forecast payload was found for this route."
        actions={<button className="ghost-button" onClick={() => navigate("/features/stock-forecast")}>Back to forecast</button>}
      >
        <section className="card"><p>No forecast data found. Run a new forecast.</p></section>
      </AppShell>
    );
  }

  const chartRows = [
    ...(payload.history || []).map((row) => ({
      date: row.date,
      history_price: row.price,
      forecast_price: null,
    })),
    ...(payload.forecast || []).map((row) => ({
      date: row.date,
      history_price: null,
      forecast_price: row.price,
    })),
  ];

  return (
    <AppShell
      eyebrow="Feature Hub / Forecast Result"
      title={`Forecast result for ${payload.symbol}`}
      subtitle="Inspect the model output without changing the existing forecast flow or payload format."
      actions={<button className="ghost-button" onClick={() => navigate("/features/stock-forecast")}>Back to forecast</button>}
    >
      <section className="card">
        <p className="mono">Symbol: {payload.symbol} | Horizon: {payload.forecast_days} days | Model: {payload.model}</p>
        <p>Current price: {formatCurrency(payload.current_price)} | Predicted end price: {formatCurrency(payload.predicted_price_end)}</p>
      </section>
      <section className="card">
        <div className="graph-card">
          <h4>History vs forecast</h4>
          <ResponsiveContainer width="100%" height={320}>
            <LineChart data={chartRows}>
              <CartesianGrid strokeDasharray="3 3" stroke="#253351" />
              <XAxis dataKey="date" hide />
              <YAxis tick={{ fill: "#97aacd" }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ background: "#0f1528", border: "1px solid #2f3b63", borderRadius: "8px" }} labelStyle={{ color: "#7f8db0", fontFamily: "DM Mono" }} itemStyle={{ color: "#dfe8ff", fontWeight: 700 }} />
              <Line type="monotone" dataKey="history_price" name="History" stroke="#1dd3b0" dot={false} connectNulls />
              <Line type="monotone" dataKey="forecast_price" name="Forecast" stroke="#f7c948" dot={false} connectNulls />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </section>
    </AppShell>
  );
}

function formatCurrency(value) {
  const n = Number(value || 0);
  return `Rs ${n.toLocaleString("en-US", { maximumFractionDigits: 2 })}`;
}

export default StockForecastResultPage;
