export default function ForecastResult({ symbol, company, days, current, predicted }) {
  return (
    <div className="stock-metrics">
      <div className="detail-metric neutral">
        <span className="detail-label mono">{company || symbol}</span>
        <strong className="mono">Current: Rs {current}</strong>
        <small>Predicted in {days} days: Rs {predicted}</small>
      </div>
    </div>
  );
}
