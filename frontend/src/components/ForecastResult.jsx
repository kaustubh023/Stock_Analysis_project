export default function ForecastResult({ symbol, company, days, current, predicted }) {
  return (
    <div className="stock-metrics">
      <div className="detail-metric neutral">
        <span className="detail-label mono">{company || symbol}</span>
        <strong className="mono">Current: ₹{current}</strong>
        <small>Predicted in {days} days: ₹{predicted}</small>
      </div>
    </div>
  );
}
