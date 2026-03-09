import { useEffect, useMemo, useState } from "react";
import { Area, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import api from "../api";
import { useAuth } from "../context/AuthContext";

function StockDetailPage() {
  const navigate = useNavigate();
  const { accessToken } = useAuth();
  const location = useLocation();
  const { symbol } = useParams();
  const [stockAnalytics, setStockAnalytics] = useState(null);
  const [error, setError] = useState("");
  const sector = location.state?.sector || "Indian Stocks";
  const companyFromState = location.state?.company_name;

  const openTrendForStock = () => {
    if (!accessToken || !symbol) return;
    const base = window.location.origin.includes("5173") ? "http://127.0.0.1:8000" : window.location.origin;
    const url = `${base}/portfolio/trend-analysis/?token=${encodeURIComponent(accessToken)}&symbol=${encodeURIComponent(symbol)}`;
    window.open(url, "_blank");
  };

  useEffect(() => {
    if (!symbol) return;
    const load = async () => {
      try {
        const res = await api.get(`/stocks/${encodeURIComponent(symbol)}/analytics/`);
        setStockAnalytics(res.data);
      } catch (err) {
        setError(err?.response?.data?.detail || "Unable to load stock details.");
      }
    };
    load();
  }, [symbol]);

  const today = useMemo(() => {
    const d = new Date();
    return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
  }, []);

  const lastChange = useMemo(() => {
    const points = stockAnalytics?.graphs?.opportunity || [];
    if (points.length < 2) return null;
    const prev = Number(points[points.length - 2].value || 0);
    const curr = Number(points[points.length - 1].value || 0);
    const delta = -(curr - prev);
    const price = Number(stockAnalytics?.metrics?.current_price || 0);
    const pct = price > 0 ? (delta / price) * 100 : 0;
    return { delta, pct };
  }, [stockAnalytics]);

  return (
    <div className="stock-details-page">
      <header className="stock-nav">
        <div className="stock-brand">
          <span className="pulse-dot" />
          <strong>AutoVest Analytics</strong>
        </div>
        <p className="stock-breadcrumb">Portfolio â€º Indian Stocks â€º <span className="mono">{symbol}</span></p>
        <div className="inline">
          <button className="stock-back-btn" onClick={openTrendForStock}>Trend Analysis</button>
          <button className="stock-back-btn" onClick={() => navigate("/dashboard")}>Back to Portfolio</button>
        </div>
      </header>

      {error && <section className="stock-card"><p className="error">{error}</p></section>}
      {!stockAnalytics && !error && <section className="stock-card"><p>Loading...</p></section>}

      {stockAnalytics && (
        <>
          <section className="stock-hero fade-up delay-1">
            <div className="hero-left">
              <span className="live-badge"><span className="pulse-dot" /> NSE Â· LIVE</span>
              <h1>{companyFromState || stockAnalytics.metrics.company}</h1>
              <p className="stock-sub mono">{stockAnalytics.metrics.symbol} Â· {sector}</p>
            </div>
            <div className="hero-right">
              <h2 className="mono">{formatCurrency(stockAnalytics.metrics.current_price)}</h2>
              {lastChange && (
                <span className={`change-badge ${lastChange.delta >= 0 ? "pos" : "neg"} mono`}>
                  {lastChange.delta >= 0 ? "+" : ""}{lastChange.delta.toFixed(2)} ({lastChange.pct.toFixed(2)}%)
                </span>
              )}
            </div>
          </section>

          <div className="gradient-divider" />

          <section className="stock-metrics fade-up delay-2">
            <DetailMetric label="Name" value={stockAnalytics.metrics.company} subtitle="Registered company name" tone="neutral" />
            <DetailMetric label="Ticker" value={stockAnalytics.metrics.symbol} subtitle="Exchange tradable symbol" tone="neutral" mono />
            <DetailMetric label="Price" value={formatCurrency(stockAnalytics.metrics.current_price)} subtitle="Latest traded price" tone="neutral" mono />
            <DetailMetric label="Min Price" value={formatCurrency(stockAnalytics.metrics.min_price)} subtitle="1Y lowest close" tone="neg" mono />
            <DetailMetric label="Max Price" value={formatCurrency(stockAnalytics.metrics.max_price)} subtitle="1Y highest close" tone="pos" mono />
            <DetailMetric label="PE Ratio" value={stockAnalytics.metrics.pe_ratio} subtitle="Price to earnings multiple" tone="neutral" mono />
            <DetailMetric label="MarketCap" value={formatMarketCap(stockAnalytics.metrics.market_cap)} subtitle="Total market capitalization" tone="neutral" mono />
            <DetailMetric label="Intrinsic" value={formatCurrency(stockAnalytics.metrics.intrinsic)} subtitle="Estimated fair value" tone="neutral" mono />
            <DetailMetric
              label="Discount%"
              value={`${stockAnalytics.metrics.discount_pct}%`}
              subtitle="Vs intrinsic value"
              tone={Number(stockAnalytics.metrics.discount_pct) >= 0 ? "pos" : "neg"}
              mono
            />
            <DetailMetric
              label="Opportunity"
              value={
                <span className={`opportunity-badge ${String(stockAnalytics.metrics.opportunity).toLowerCase() === "high" ? "high" : "low"}`}>
                  {stockAnalytics.metrics.opportunity}
                </span>
              }
              subtitle="Current valuation signal"
              tone={String(stockAnalytics.metrics.opportunity).toLowerCase() === "high" ? "pos" : "neg"}
            />
          </section>

          <div className="gradient-divider" />

          <section className="stock-charts fade-up delay-3">
            <ChartShell title="PE Ratio Graph" badge="TRAILING">
              <DetailLineChart data={stockAnalytics.graphs.pe} color="#818cf8" gradientId="peGrad" />
            </ChartShell>
            <ChartShell title="Opportunity Graph" badge="RELATIVE">
              <DetailLineChart data={stockAnalytics.graphs.opportunity} color="#00e5b0" gradientId="oppGrad" />
            </ChartShell>
            <ChartShell title="Discount Graph" badge="VS INTRINSIC">
              <DetailLineChart data={stockAnalytics.graphs.discount} color="#f7c948" gradientId="discGrad" />
            </ChartShell>
          </section>

          <footer className="stock-footer">
            <p className="mono">AutoVest Analytics Â· Data from Yahoo Finance Â· Not investment advice Â· Updated {today}</p>
          </footer>
        </>
      )}
    </div>
  );
}

function formatCurrency(value) {
  const n = Number(value || 0);
  return `₹${n.toLocaleString("en-US", { maximumFractionDigits: 2 })}`;
}

function formatMarketCap(value) {
  const n = Number(value || 0);
  if (!n) return "N/A";
  if (n >= 1e12) return `₹${(n / 1e12).toFixed(2)}T`;
  if (n >= 1e9) return `₹${(n / 1e9).toFixed(2)}B`;
  if (n >= 1e6) return `₹${(n / 1e6).toFixed(2)}M`;
  if (n >= 1e3) return `₹${(n / 1e3).toFixed(2)}K`;
  return `₹${n.toLocaleString("en-US", { maximumFractionDigits: 2 })}`;
}

function DetailMetric({ label, value, subtitle, tone = "neutral", mono = false }) {
  return (
    <div className={`detail-metric ${tone}`}>
      <span className="detail-label">{label}</span>
      <strong className={mono ? "mono" : ""}>{value}</strong>
      <small>{subtitle}</small>
    </div>
  );
}

function ChartShell({ title, badge, children }) {
  return (
    <div className="stock-chart-card">
      <div className="stock-chart-head">
        <h4>{title}</h4>
        <span className="chart-pill mono">{badge}</span>
      </div>
      {children}
    </div>
  );
}

function TooltipDark({ active, payload, label }) {
  if (!active || !payload || !payload.length) return null;
  return (
    <div className="dark-tooltip">
      <div className="mono">{label}</div>
      <div><strong className="mono">{Number(payload[0].value || 0).toFixed(2)}</strong></div>
    </div>
  );
}

function DetailLineChart({ data, color, gradientId }) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={data}>
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.18} />
            <stop offset="100%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#2a3458" />
        <XAxis dataKey="date" hide />
        <YAxis tick={{ fill: "#6878a7", fontSize: 11 }} axisLine={false} tickLine={false} />
        <Tooltip content={<TooltipDark />} />
        <Area type="monotone" dataKey="value" stroke="none" fill={`url(#${gradientId})`} />
        <Line type="monotone" dataKey="value" stroke={color} strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}

export default StockDetailPage;
