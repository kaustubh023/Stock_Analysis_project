import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

function CompareStocksFeaturePage() {
  const navigate = useNavigate();
  const [stocks, setStocks] = useState([]);
  const [symbolA, setSymbolA] = useState("");
  const [symbolB, setSymbolB] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const load = async () => {
      try {
        const stocksRes = await api.get("/portfolio-stocks/");
        const unique = [...new Set((stocksRes.data || []).map((s) => s.symbol))];
        setStocks(unique);
      } catch (err) {
        setError(err?.response?.data?.detail || "Unable to load stock list.");
      }
    };
    load();
  }, []);

  const compare = async () => {
    setError("");
    if (!symbolA || !symbolB || symbolA === symbolB) {
      setError("Select two different stocks.");
      return;
    }
    try {
      const res = await api.post("/stock/compare/", { symbol_a: symbolA, symbol_b: symbolB });
      setResult(res.data);
    } catch (err) {
      setError(err?.response?.data?.detail || "Comparison failed.");
    }
  };

  const chartRows = useMemo(() => {
    if (!result) return [];
    return [
      {
        metric: "Return %",
        [result.stock_a.symbol]: result.stock_a.one_year_return_pct,
        [result.stock_b.symbol]: result.stock_b.one_year_return_pct,
      },
      {
        metric: "Volatility %",
        [result.stock_a.symbol]: result.stock_a.volatility_pct,
        [result.stock_b.symbol]: result.stock_b.volatility_pct,
      },
      {
        metric: "Sharpe",
        [result.stock_a.symbol]: result.stock_a.sharpe,
        [result.stock_b.symbol]: result.stock_b.sharpe,
      },
    ];
  }, [result]);

  return (
    <div className="stock-details-page">
      <header className="stock-nav">
        <div className="stock-brand"><span className="pulse-dot" /><strong>Compare Stocks</strong></div>
        <button className="stock-back-btn" onClick={() => navigate("/other-features")}>Back</button>
      </header>
      <section className="stock-card">
        <div className="inline">
          <select value={symbolA} onChange={(e) => setSymbolA(e.target.value)}>
            <option value="">Stock A</option>
            {stocks.map((s) => <option key={`ca-${s}`} value={s}>{s}</option>)}
          </select>
          <select value={symbolB} onChange={(e) => setSymbolB(e.target.value)}>
            <option value="">Stock B</option>
            {stocks.map((s) => <option key={`cb-${s}`} value={s}>{s}</option>)}
          </select>
          <button onClick={compare}>Compare</button>
        </div>
        {error && <p className="error">{error}</p>}
        {result && (
          <div className="compare-box">
            <p><strong>More Profitable:</strong> {result.more_profitable}</p>
            <p>{result.stock_a.symbol}: Return {result.stock_a.one_year_return_pct}% | Volatility {result.stock_a.volatility_pct}% | Sharpe {result.stock_a.sharpe}</p>
            <p>{result.stock_b.symbol}: Return {result.stock_b.one_year_return_pct}% | Volatility {result.stock_b.volatility_pct}% | Sharpe {result.stock_b.sharpe}</p>
            <div style={{ height: 280, background: "#fbfdff", border: "1px solid #e3edf5", borderRadius: 12, padding: 8 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartRows}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="metric" />
                  <YAxis />
                  <Tooltip
                    contentStyle={{ background: "#0f1528", border: "1px solid #2f3b63", borderRadius: "8px" }}
                    labelStyle={{ color: "#7f8db0", fontFamily: "DM Mono" }}
                    itemStyle={{ color: "#dfe8ff", fontWeight: 700 }}
                  />
                  <Legend />
                  <Bar dataKey={result.stock_a.symbol} fill="#22d3ee" stroke="#67e8f9" radius={[6, 6, 0, 0]} />
                  <Bar dataKey={result.stock_b.symbol} fill="#a78bfa" stroke="#c4b5fd" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}

export default CompareStocksFeaturePage;
