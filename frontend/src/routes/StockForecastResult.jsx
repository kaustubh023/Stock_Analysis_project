import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useLocation, useNavigate } from "react-router-dom";

function StockForecastResultPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const payload = location.state?.payload;

  if (!payload) {
    return (
      <div className="stock-details-page">
        <header className="stock-nav">
          <div className="stock-brand"><span className="pulse-dot" /><strong>Forecast Result</strong></div>
          <button className="stock-back-btn" onClick={() => navigate("/features/stock-forecast")}>Back</button>
        </header>
        <section className="stock-card"><p>No forecast data found. Run a new forecast.</p></section>
      </div>
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
    <div className="stock-details-page">
      <header className="stock-nav">
        <div className="stock-brand"><span className="pulse-dot" /><strong>Forecast Result</strong></div>
        <button className="stock-back-btn" onClick={() => navigate("/features/stock-forecast")}>Back</button>
      </header>
      <section className="stock-card">
        <p className="mono">Symbol: {payload.symbol} | Horizon: {payload.forecast_days} days | Model: {payload.model}</p>
        <p>Current Price: {formatCurrency(payload.current_price)} | Predicted End Price: {formatCurrency(payload.predicted_price_end)}</p>
      </section>
      <section className="stock-card">
        <ResponsiveContainer width="100%" height={320}>
          <LineChart data={chartRows}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" hide />
            <YAxis />
            <Tooltip contentStyle={{ background: "#0f1528", border: "1px solid #2f3b63", borderRadius: "8px" }} labelStyle={{ color: "#7f8db0", fontFamily: "DM Mono" }} itemStyle={{ color: "#dfe8ff", fontWeight: 700 }} />
            <Line type="monotone" dataKey="history_price" name="History" stroke="#00e5b0" dot={false} connectNulls />
            <Line type="monotone" dataKey="forecast_price" name="Forecast" stroke="#f7c948" dot={false} connectNulls />
          </LineChart>
        </ResponsiveContainer>
      </section>
    </div>
  );
}

function formatCurrency(value) {
  const n = Number(value || 0);
  return `₹${n.toLocaleString("en-US", { maximumFractionDigits: 2 })}`;
}

export default StockForecastResultPage;
