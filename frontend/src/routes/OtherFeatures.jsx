import { useNavigate } from "react-router-dom";
import AppShell from "../components/AppShell";

function OtherFeaturesPage() {
  const navigate = useNavigate();

  const features = [
    {
      title: "Compare Stocks",
      note: "Compare return, volatility and Sharpe for two owned stocks.",
      tag: "Portfolio compare",
      to: "/features/compare-stocks",
    },
    {
      title: "Risk Categorization",
      note: "Classify each stock into low, medium or high risk bands.",
      tag: "Risk lens",
      to: "/features/risk-categorization",
    },
    {
      title: "Portfolio Clustering",
      note: "Group portfolio stocks using PCA or UMAP with k-means clustering.",
      tag: "Quant analysis",
      to: "/features/portfolio-cluster",
    },
    {
      title: "Gold/Silver Correlation",
      note: "Study the five-year relationship between gold and silver with multiple charts.",
      tag: "Commodity view",
      to: "/features/gold-silver",
    },
    {
      title: "Stock Forecasting",
      note: "Generate near-term forecasts for a chosen stock and inspect portfolio next-day predictions.",
      tag: "Forecasting",
      to: "/features/stock-forecast",
    },
    {
      title: "BTC-USD Hourly Forecast",
      note: "Review a dedicated ARIMA-based next-hour crypto forecast.",
      tag: "Crypto",
      to: "/features/btc-usd-hourly",
    },
  ];

  return (
    <AppShell
      eyebrow="Feature Hub"
      title="Advanced analytics workspace"
      subtitle="Every tool below keeps the same project flow and data sources, but gives each analysis its own dedicated surface."
    >
      <section className="feature-grid">
        {features.map((feature) => (
          <article key={feature.to} className="card feature-card">
            <span className="chip chip-subtle mono">{feature.tag}</span>
            <h3>{feature.title}</h3>
            <p className="note">{feature.note}</p>
            <button onClick={() => navigate(feature.to)}>Open analysis</button>
          </article>
        ))}
      </section>
    </AppShell>
  );
}

export default OtherFeaturesPage;
