import { useNavigate } from "react-router-dom";

function OtherFeaturesPage() {
  const navigate = useNavigate();
  return (
    <div className="page dashboard-page">
      <header className="topbar dashboard-topbar">
        <div>
          <p className="dashboard-brand mono"><span className="pulse-dot" /> Feature Hub</p>
          <h2>Other Features</h2>
          <p>Run advanced analytics on your portfolio stocks</p>
        </div>
        <div className="inline">
          <button onClick={() => navigate("/dashboard")}>Back to Dashboard</button>
        </div>
      </header>

      <section className="grid two">
        <div className="card">
          <h3>Compare Stocks</h3>
          <p className="note">Compare return, volatility and sharpe for two owned stocks.</p>
          <button onClick={() => navigate("/features/compare-stocks")}>Open</button>
        </div>
        <div className="card">
          <h3>Risk Categorization</h3>
          <p className="note">Classify each stock into low, medium or high risk bands.</p>
          <button onClick={() => navigate("/features/risk-categorization")}>Open</button>
        </div>
        <div className="card">
          <h3>Portfolio Clustering</h3>
          <p className="note">Group portfolio stocks using PCA/UMAP and k-means.</p>
          <button onClick={() => navigate("/features/portfolio-cluster")}>Open</button>
        </div>
        <div className="card">
          <h3>Gold/Silver Correlation</h3>
          <p className="note">View dedicated 5-year gold vs silver analysis charts.</p>
          <button onClick={() => navigate("/features/gold-silver")}>Open</button>
        </div>
        <div className="card">
          <h3>Stock Forecasting</h3>
          <p className="note">Generate linear-regression-based near-term forecasts.</p>
          <button onClick={() => navigate("/features/stock-forecast")}>Open</button>
        </div>
        <div className="card">
          <h3>BTC-USD Hourly Forecast</h3>
          <p className="note">ARIMA-based next 1-hour price prediction and chart.</p>
          <button onClick={() => navigate("/features/btc-usd-hourly")}>Open</button>
        </div>
      </section>
    </div>
  );
}

export default OtherFeaturesPage;
