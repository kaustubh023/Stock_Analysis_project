import { useEffect, useMemo, useRef, useState } from "react";
import { Navigate, Route, Routes, useLocation, useNavigate, useParams } from "react-router-dom";
import {
  Area,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import api from "./api";

function App() {
  const token = localStorage.getItem("access_token");

  return (
    <Routes>
      <Route path="/" element={token ? <Navigate to="/dashboard" /> : <AuthPage />} />
      <Route path="/dashboard" element={token ? <DashboardPage /> : <Navigate to="/" />} />
      <Route path="/stock/:symbol" element={token ? <StockDetailsPage /> : <Navigate to="/" />} />
    </Routes>
  );
}

function AuthPage() {
  const navigate = useNavigate();
  const [isRegister, setIsRegister] = useState(false);
  const [form, setForm] = useState({ username: "", email: "", password: "" });
  const [error, setError] = useState("");

  const formatApiError = (err) => {
    const data = err?.response?.data;
    if (!data) return "Authentication failed.";
    if (typeof data === "string") return data;
    if (data.detail) return data.detail;
    if (typeof data === "object") {
      const messages = [];
      Object.entries(data).forEach(([field, value]) => {
        if (Array.isArray(value)) {
          messages.push(`${field}: ${value.join(", ")}`);
        } else if (value) {
          messages.push(`${field}: ${String(value)}`);
        }
      });
      if (messages.length) return messages.join(" | ");
    }
    return "Authentication failed.";
  };

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    // Prevent stale/invalid tokens from interfering with auth flow.
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("username");
    try {
      if (isRegister) {
        let registerResp = null;
        try {
          registerResp = await api.post("/auth/register/", form);
        } catch (regErr) {
          const data = regErr?.response?.data || {};
          const raw = JSON.stringify(data).toLowerCase();
          const alreadyExists =
            raw.includes("already exists") ||
            raw.includes("already taken") ||
            raw.includes("unique");
          // If account already exists, continue with login using entered credentials.
          if (!alreadyExists) {
            throw regErr;
          }
        }
        // New account created: token comes from register endpoint directly.
        if (registerResp?.data?.access) {
          localStorage.setItem("access_token", registerResp.data.access);
          localStorage.setItem("refresh_token", registerResp.data.refresh || "");
          localStorage.setItem("username", registerResp.data.username || form.username);
          window.location.replace("/dashboard");
          return;
        }
      }
      const resp = await api.post("/auth/login/", { username: form.username, password: form.password });
      localStorage.setItem("access_token", resp.data.access);
      localStorage.setItem("refresh_token", resp.data.refresh);
      localStorage.setItem("username", resp.data.username);
      window.location.replace("/dashboard");
    } catch (err) {
      // Login mode: if user doesn't exist, guide to register first.
      if (!isRegister) {
        try {
          const check = await api.get(`/auth/user-exists/?username=${encodeURIComponent(form.username)}`);
          if (!check.data?.exists) {
            setIsRegister(true);
            setError("Account does not exist. Please create an account first.");
            return;
          }
        } catch {
          // fallback to default error below
        }
      }
      setError(formatApiError(err));
    }
  };

  return (
    <div className="auth-shell">
      <section className="auth-left">
        <div className="auth-grid-overlay" />
        <svg className="auth-chart-bg" viewBox="0 0 1200 800" preserveAspectRatio="none">
          <path d="M30 560 L130 490 L210 520 L300 430 L390 460 L470 350 L560 380 L650 280 L760 320 L860 230 L960 280 L1080 190" />
          <g>
            <line x1="120" y1="520" x2="120" y2="620" />
            <line x1="220" y1="460" x2="220" y2="580" />
            <line x1="320" y1="420" x2="320" y2="540" />
            <line x1="420" y1="360" x2="420" y2="510" />
            <line x1="520" y1="320" x2="520" y2="460" />
            <line x1="620" y1="280" x2="620" y2="420" />
            <line x1="720" y1="240" x2="720" y2="390" />
            <line x1="820" y1="220" x2="820" y2="350" />
            <line x1="920" y1="170" x2="920" y2="300" />
          </g>
        </svg>

        <div className="auth-brand">
          <span className="pulse-dot" />
          <h1>StockSense</h1>
        </div>

        <div className="floating-stats">
          <div className="float-card f1">
            <div className="mono">NIFTY 50 · +1.24% · 22,450.30</div>
            <svg viewBox="0 0 200 38"><polyline points="2,30 38,24 68,27 98,17 126,20 162,11 198,8" /></svg>
          </div>
          <div className="float-card f2">
            <div className="mono">SENSEX · -0.38% · 73,912.11</div>
            <svg viewBox="0 0 200 38" className="neg"><polyline points="2,8 36,12 66,16 98,18 126,24 162,28 198,32" /></svg>
          </div>
          <div className="float-card f3">
            <div className="mono">Your Portfolio · ▲ 8.3% this month</div>
          </div>
        </div>

        <p className="auth-quote">"Investing is not about timing the market, it's about time in the market."</p>
      </section>

      <section className="auth-right">
        <div className="auth-form-wrap">
          <span className="secure-badge mono">SECURE LOGIN</span>
          <h2>{isRegister ? "Create Account" : "Welcome Back"}</h2>
          <p>{isRegister ? "Register to access your Stock Analysis dashboard" : "Sign in to your Stock Analysis dashboard"}</p>

          <form onSubmit={submit}>
            <label className="input-shell">
              <svg viewBox="0 0 24 24" fill="none"><path d="M12 12a4 4 0 1 0-4-4 4 4 0 0 0 4 4Zm0 2c-4.4 0-8 2.24-8 5v1h16v-1c0-2.76-3.6-5-8-5Z" stroke="currentColor" strokeWidth="1.5" /></svg>
              <input placeholder="Username" required value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} />
            </label>
            {isRegister && (
              <label className="input-shell">
                <svg viewBox="0 0 24 24" fill="none"><path d="M4 6h16v12H4z" stroke="currentColor" strokeWidth="1.5" /><path d="m4 8 8 6 8-6" stroke="currentColor" strokeWidth="1.5" /></svg>
                <input placeholder="Email" type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
              </label>
            )}
            <label className="input-shell">
              <svg viewBox="0 0 24 24" fill="none"><path d="M7 11V8a5 5 0 0 1 10 0v3" stroke="currentColor" strokeWidth="1.5" /><rect x="5" y="11" width="14" height="10" rx="2" stroke="currentColor" strokeWidth="1.5" /></svg>
              <input placeholder="Password" type="password" required value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
            </label>
            {error && <div className="error">{error}</div>}
            <button className="auth-submit" type="submit">{isRegister ? "Register & Login" : "Login"}</button>
          </form>

          <button className="auth-toggle" onClick={() => setIsRegister((v) => !v)}>
            {isRegister ? "Already have account? Login" : "No account? Register"}
          </button>
        </div>
      </section>
    </div>
  );
}

function DashboardPage() {
  const navigate = useNavigate();
  const username = localStorage.getItem("username");
  const [portfolioTypes, setPortfolioTypes] = useState([]);
  const [stocks, setStocks] = useState([]);
  const [peComparison, setPeComparison] = useState([]);
  const [goldSilver, setGoldSilver] = useState(null);
  const [newType, setNewType] = useState("");
  const [selectedType, setSelectedType] = useState("");
  const [sector, setSector] = useState("");
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedSuggestion, setSelectedSuggestion] = useState(null);
  const [compareA, setCompareA] = useState("");
  const [compareB, setCompareB] = useState("");
  const [compareResult, setCompareResult] = useState(null);
  const [commodityView, setCommodityView] = useState("gold");
  const [message, setMessage] = useState("");
  const searchBoxRef = useRef(null);
  const searchCacheRef = useRef(new Map());
  const hasPortfolioType = portfolioTypes.length > 0;

  const loadPortfolio = async () => {
    const [typesRes, stocksRes, peRes] = await Promise.all([
      api.get("/portfolio-types/"),
      api.get("/portfolio-stocks/"),
      api.get("/portfolio/pe-comparison/"),
    ]);
    setPortfolioTypes(typesRes.data);
    setStocks(stocksRes.data);
    setPeComparison(peRes.data.items);
  };

  const loadGoldSilver = async () => {
    const res = await api.get("/commodities/gold-silver-correlation/");
    setGoldSilver(res.data);
  };

  useEffect(() => {
    loadPortfolio();
    loadGoldSilver();
  }, []);

  useEffect(() => {
    const timer = setTimeout(async () => {
      if (!selectedType || query.length < 1) {
        setSuggestions([]);
        setShowSuggestions(false);
        return;
      }
      const key = query.trim().toLowerCase();
      if (!key) {
        setSuggestions([]);
        setShowSuggestions(false);
        return;
      }
      if (searchCacheRef.current.has(key)) {
        setSuggestions(searchCacheRef.current.get(key));
        setShowSuggestions(true);
        return;
      }
      try {
        const res = await api.get(`/stocks/search/?q=${encodeURIComponent(query)}`);
        const rows = res.data.results || [];
        searchCacheRef.current.set(key, rows);
        setSuggestions(rows);
      } catch {
        setSuggestions([]);
      } finally {
        setShowSuggestions(true);
      }
    }, 70);

    return () => clearTimeout(timer);
  }, [query, selectedType]);

  useEffect(() => {
    setQuery("");
    setSelectedSuggestion(null);
    setSuggestions([]);
    setShowSuggestions(false);
  }, [sector, selectedType]);

  useEffect(() => {
    if (!selectedType && portfolioTypes.length > 0) {
      setSelectedType(String(portfolioTypes[0].id));
    }
  }, [portfolioTypes, selectedType]);

  useEffect(() => {
    const onClickOutside = (event) => {
      if (!searchBoxRef.current) return;
      if (!searchBoxRef.current.contains(event.target)) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener("mousedown", onClickOutside);
    return () => {
      document.removeEventListener("mousedown", onClickOutside);
    };
  }, []);

  const addPortfolioType = async () => {
    if (!newType.trim()) return;
    const resp = await api.post("/portfolio-types/", { name: newType.trim() });
    setNewType("");
    if (resp?.data?.id) {
      setSelectedType(String(resp.data.id));
    }
    await loadPortfolio();
  };

  const addStockToPortfolio = async () => {
    if (!selectedType || !sector || !selectedSuggestion) {
      setMessage("Select portfolio type, sector and stock suggestion.");
      return;
    }

    await api.post("/portfolio-stocks/", {
      portfolio_type: Number(selectedType),
      sector,
      symbol: selectedSuggestion.symbol,
      company_name: selectedSuggestion.name,
    });

    setMessage("Stock added to portfolio.");
    setSelectedSuggestion(null);
    setQuery("");
    setSuggestions([]);
    await loadPortfolio();
  };

  const compareStocks = async () => {
    if (!compareA || !compareB || compareA === compareB) {
      setMessage("Pick two different stocks for comparison.");
      return;
    }
    const res = await api.post("/portfolio/compare/", { symbol_a: compareA, symbol_b: compareB });
    setCompareResult(res.data);
    setMessage("");
  };

  const logout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("username");
    // Force a full reload so auth guards re-evaluate reliably.
    window.location.replace("/");
  };

  const stockSymbols = useMemo(() => [...new Set(stocks.map((s) => s.symbol))], [stocks]);

  return (
    <div className="page dashboard-page">
      <header className="topbar dashboard-topbar">
        <div>
          <p className="dashboard-brand mono"><span className="pulse-dot" /> AutoVest Analytics</p>
          <h2>Welcome, {username}</h2>
          <p>Your portfolio and analytics workspace</p>
        </div>
        <button onClick={logout}>Logout</button>
      </header>

      <section className="grid two">
        <div className="card">
          <h3>Create Portfolio Name</h3>
          <div className="inline">
            <input value={newType} onChange={(e) => setNewType(e.target.value)} placeholder="e.g. Long Term Wealth" />
            <button onClick={addPortfolioType}>Create</button>
          </div>
          {!hasPortfolioType && <p className="note">Create portfolio name first to continue.</p>}

          <h3>Add Stock</h3>
          <p className="note">Step 1: Enter sector manually</p>
          <input
            value={sector}
            onChange={(e) => setSector(e.target.value)}
            placeholder={selectedType ? "e.g. Banking, IT, Pharma" : "Create/select portfolio first"}
            disabled={!hasPortfolioType || !selectedType}
          />

          <p className="note">Step 2: Search Indian stock (starts with)</p>
          <div ref={searchBoxRef}>
            <input
              value={query}
              onFocus={() => {
                if (selectedType && query.length >= 1) {
                  setShowSuggestions(true);
                }
              }}
              onChange={(e) => {
                setSelectedSuggestion(null);
                setQuery(e.target.value);
              }}
              placeholder={selectedType ? 'Type "a", "as", ticker, etc.' : "Create/select portfolio first"}
              disabled={!hasPortfolioType || !selectedType}
            />
            {showSuggestions && selectedType && query.length >= 1 && (
              <div className="suggestions">
                {suggestions.length > 0 ? (
                  suggestions.map((s) => (
                    <button
                      key={s.symbol}
                      className="suggestion"
                      onClick={() => {
                        setSelectedSuggestion(s);
                        setQuery(`${s.symbol} - ${s.name} (${s.exchange})`);
                        setShowSuggestions(false);
                      }}
                    >
                      {s.symbol} - {s.name} ({s.exchange})
                    </button>
                  ))
                ) : (
                  <div className="suggestion-empty">No stocks found</div>
                )}
              </div>
            )}
          </div>

          <button onClick={addStockToPortfolio}>Add to Portfolio</button>
          {message && <p className="note">{message}</p>}
        </div>

        <div className="card">
          <h3>Your Portfolio Stocks</h3>
          <div className="stock-list">
            {stocks.map((stock) => (
              <button
                key={stock.id}
                className="stock-item"
                onClick={() =>
                  navigate(`/stock/${encodeURIComponent(stock.symbol)}`, {
                    state: {
                      sector: stock.sector,
                      company_name: stock.company_name,
                    },
                  })
                }
              >
                <div>{stock.company_name}</div>
                <small>{stock.symbol} | {stock.sector} | {stock.portfolio_type_name}</small>
              </button>
            ))}
            {stocks.length === 0 && <p>No stocks yet.</p>}
          </div>
        </div>
      </section>

      <section className="grid two">
        <div className="card">
          <h3>Portfolio PE Ratio Comparison</h3>
          <div className="chart-box">
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={peComparison}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="symbol" />
                <YAxis />
                <Tooltip contentStyle={{ background: "#0f1528", border: "1px solid #2f3b63", borderRadius: "8px" }} labelStyle={{ color: "#7f8db0", fontFamily: "DM Mono" }} itemStyle={{ color: "#dfe8ff", fontWeight: 700 }} />
                <Bar dataKey="pe_ratio" fill="#006d77" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card">
          <h3>Compare Two Stocks (Your Portfolio)</h3>
          <div className="inline">
            <select value={compareA} onChange={(e) => setCompareA(e.target.value)}>
              <option value="">Stock A</option>
              {stockSymbols.map((s) => <option key={`a-${s}`} value={s}>{s}</option>)}
            </select>
            <select value={compareB} onChange={(e) => setCompareB(e.target.value)}>
              <option value="">Stock B</option>
              {stockSymbols.map((s) => <option key={`b-${s}`} value={s}>{s}</option>)}
            </select>
            <button onClick={compareStocks}>Compare</button>
          </div>

          {compareResult && (
            <div className="compare-box">
              <p><strong>More Profitable:</strong> {compareResult.more_profitable}</p>
              <p>{compareResult.stock_a.symbol}: Return {compareResult.stock_a.one_year_return_pct}% | Volatility {compareResult.stock_a.volatility_pct}% | Sharpe {compareResult.stock_a.sharpe}</p>
              <p>{compareResult.stock_b.symbol}: Return {compareResult.stock_b.one_year_return_pct}% | Volatility {compareResult.stock_b.volatility_pct}% | Sharpe {compareResult.stock_b.sharpe}</p>
            </div>
          )}
        </div>
      </section>

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
                  <XAxis
                    type="number"
                    dataKey="x"
                    name={commodityView === "gold" ? "Gold" : "Silver"}
                  />
                  <YAxis
                    type="number"
                    dataKey="y"
                    name={commodityView === "gold" ? "Silver" : "Gold"}
                  />
                  <Tooltip cursor={{ strokeDasharray: "3 3" }} contentStyle={{ background: "#0f1528", border: "1px solid #2f3b63", borderRadius: "8px" }} labelStyle={{ color: "#7f8db0", fontFamily: "DM Mono" }} itemStyle={{ color: "#dfe8ff", fontWeight: 700 }} />
                  <Scatter
                    data={
                      commodityView === "gold"
                        ? goldSilver.scatter_graph
                        : goldSilver.scatter_graph.map((p) => ({ x: p.y, y: p.x }))
                    }
                    fill={commodityView === "gold" ? "#b8860b" : "#c0c0c0"}
                  />
                </ScatterChart>
              </ResponsiveContainer>
            </GraphCard>

            <GraphCard title="Linear Regression Graph">
              <ResponsiveContainer width="100%" height={260}>
                <LineChart
                  data={buildCommodityRegression(goldSilver.line_graph, commodityView)}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="x" />
                  <YAxis />
                  <Tooltip contentStyle={{ background: "#0f1528", border: "1px solid #2f3b63", borderRadius: "8px" }} labelStyle={{ color: "#7f8db0", fontFamily: "DM Mono" }} itemStyle={{ color: "#dfe8ff", fontWeight: 700 }} />
                  <Line
                    type="monotone"
                    dataKey="y"
                    stroke={commodityView === "gold" ? "#b8860b" : "#c0c0c0"}
                    dot={false}
                  />
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

function StockDetailsPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { symbol } = useParams();
  const [stockAnalytics, setStockAnalytics] = useState(null);
  const [error, setError] = useState("");
  const sector = location.state?.sector || "Indian Stocks";
  const companyFromState = location.state?.company_name;

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
        <p className="stock-breadcrumb">Portfolio › Indian Stocks › <span className="mono">{symbol}</span></p>
        <button className="stock-back-btn" onClick={() => navigate("/dashboard")}>Back to Portfolio</button>
      </header>

      {error && <section className="stock-card"><p className="error">{error}</p></section>}
      {!stockAnalytics && !error && <section className="stock-card"><p>Loading...</p></section>}

      {stockAnalytics && (
        <>
          <section className="stock-hero fade-up delay-1">
            <div className="hero-left">
              <span className="live-badge"><span className="pulse-dot" /> NSE · LIVE</span>
              <h1>{companyFromState || stockAnalytics.metrics.company}</h1>
              <p className="stock-sub mono">{stockAnalytics.metrics.symbol} · {sector}</p>
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
            <DetailMetric label="MarketCap" value={formatIndianMarketCap(stockAnalytics.metrics.market_cap)} subtitle="Total market capitalization" tone="neutral" mono />
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
            <p className="mono">AutoVest Analytics · Data from Yahoo Finance · Not investment advice · Updated {today}</p>
          </footer>
        </>
      )}
    </div>
  );
}

function formatCurrency(value) {
  const n = Number(value || 0);
  return `₹${n.toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
}

function formatIndianMarketCap(value) {
  const n = Number(value || 0);
  if (!n) return "N/A";
  const lakhCrore = n / 1e12;
  if (lakhCrore >= 1) return `₹${lakhCrore.toFixed(2)}L Cr`;
  const crore = n / 1e7;
  return `₹${crore.toFixed(2)} Cr`;
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

function GraphCard({ title, children }) {
  return (
    <div className="graph-card">
      <h4>{title}</h4>
      {children}
    </div>
  );
}

function TimeLine({ data, color }) {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" hide />
        <YAxis />
        <Tooltip />
        <Line type="monotone" dataKey="value" stroke={color} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}

function Metric({ label, value }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

export default App;
