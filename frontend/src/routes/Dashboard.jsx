import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import api from "../api";
import { useAuth } from "../context/AuthContext";

function DashboardPage() {
  const navigate = useNavigate();
  const { username, logout: clearAuth } = useAuth();
  const [portfolioTypes, setPortfolioTypes] = useState([]);
  const [stocks, setStocks] = useState([]);
  const [peComparison, setPeComparison] = useState([]);
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
  const [message, setMessage] = useState("");
  const searchBoxRef = useRef(null);
  const searchCacheRef = useRef(new Map());
  const hasPortfolioType = portfolioTypes.length > 0;

  const loadPEComparison = async (portfolioStocks = []) => {
    const symbols = [...new Set((portfolioStocks || []).map((s) => String(s.symbol || "").trim()).filter(Boolean))];
    if (symbols.length === 0) {
      setPeComparison([]);
      return;
    }
    try {
      const peRes = await api.get("/portfolio/pe-comparison/");
      const items = peRes?.data?.items || [];
      const bySymbol = new Map(
        items.map((row) => [String(row?.symbol || "").toUpperCase(), row])
      );
      const orderedRows = symbols.map((symbol) => {
        const key = symbol.toUpperCase();
        const row = bySymbol.get(key);
        const pe = Number(row?.pe_ratio);
        return {
          symbol: key,
          pe_ratio: Number.isFinite(pe) && pe > 0 ? Number(pe.toFixed(2)) : null,
        };
      });
      setPeComparison(orderedRows);
    } catch {
      setPeComparison(symbols.map((symbol) => ({ symbol: symbol.toUpperCase(), pe_ratio: null })));
    }
  };

  const loadPortfolio = async () => {
    const [typesRes, stocksRes] = await Promise.all([
      api.get("/portfolio-types/"),
      api.get("/portfolio-stocks/"),
    ]);
    const types = typesRes.data || [];
    const portfolioStocks = stocksRes.data || [];
    setPortfolioTypes(types);
    setStocks(portfolioStocks);
    loadPEComparison(portfolioStocks);
  };

  useEffect(() => {
    loadPortfolio();
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
    clearAuth();
    navigate("/login", { replace: true });
  };

  const stockSymbols = useMemo(() => [...new Set(stocks.map((s) => s.symbol))], [stocks]);
  const peComparisonChartData = useMemo(
    () =>
      (peComparison || []).map((row) => {
        const pe = Number(row?.pe_ratio);
        const peAvailable = Number.isFinite(pe) && pe > 0;
        return {
          ...row,
          pe_ratio_value: peAvailable ? pe : null,
          pe_available: peAvailable,
        };
      }),
    [peComparison]
  );
  const peUnavailableSymbols = useMemo(
    () => peComparisonChartData.filter((row) => !row.pe_available).map((row) => row.symbol),
    [peComparisonChartData]
  );

  return (
    <div className="page dashboard-page">
      <header className="topbar dashboard-topbar">
        <div>
          <p className="dashboard-brand mono"><span className="pulse-dot" /> AutoVest Analytics</p>
          <h2>Welcome, {username}</h2>
          <p>Your portfolio and analytics workspace</p>
        </div>
        <div className="inline">
          <button onClick={() => navigate("/explore")}>Explore</button>
          <button onClick={() => navigate("/other-features")}>Other Features</button>
          <button onClick={() => navigate("/clusters")}>Cluster Lab</button>
          <button onClick={logout}>Logout</button>
        </div>
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
            {peComparisonChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={peComparisonChartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="symbol" />
                  <YAxis />
                  <Tooltip
                    formatter={(_, __, item) => {
                      const payload = item?.payload || {};
                      return [payload.pe_available ? payload.pe_ratio : "N/A", "PE Ratio"];
                    }}
                    contentStyle={{ background: "#0f1528", border: "1px solid #2f3b63", borderRadius: "8px" }}
                    labelStyle={{ color: "#7f8db0", fontFamily: "DM Mono" }}
                    itemStyle={{ color: "#dfe8ff", fontWeight: 700 }}
                  />
                  <Bar dataKey="pe_ratio_value" fill="#22d3ee" stroke="#67e8f9" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="note">No stocks found in your portfolio.</p>
            )}
            {peUnavailableSymbols.length > 0 && (
              <p className="note">
                PE unavailable: {peUnavailableSymbols.join(", ")}
              </p>
            )}
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

    </div>
  );
}

export default DashboardPage;
