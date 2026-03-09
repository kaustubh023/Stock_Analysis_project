import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

function TooltipDark({ active, payload, label }) {
  if (!active || !payload || !payload.length) return null;
  return (
    <div className="dark-tooltip">
      <div className="mono">{label}</div>
      <div><strong className="mono">{Number(payload[0].value || 0).toFixed(2)}</strong></div>
    </div>
  );
}

export default function ForecastGraph({ history = [], future = [] }) {
  const rows = [
    ...(history || []).map((r) => ({ date: r.date, history_price: r.price, forecast_price: null })),
    ...(future || []).map((r) => ({ date: r.date, history_price: null, forecast_price: r.price })),
  ];
  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={rows}>
        <CartesianGrid strokeDasharray="3 3" stroke="#2a3458" />
        <XAxis dataKey="date" />
        <YAxis tick={{ fill: "#6878a7", fontSize: 11 }} axisLine={false} tickLine={false} />
        <Tooltip content={<TooltipDark />} />
        <Line type="monotone" dataKey="history_price" stroke="#22d3ee" strokeWidth={2} dot={false} />
        <Line type="monotone" dataKey="forecast_price" stroke="#a78bfa" strokeWidth={2} strokeDasharray="4 4" dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}
