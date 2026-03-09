import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api";

function ExplorePage() {
  const navigate = useNavigate();
  const [stocks, setStocks] = useState([]);
  const [portfolioTypes, setPortfolioTypes] = useState([]);
  const [selectedType, setSelectedType] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError("");
      try {
        const [typesRes, stocksRes] = await Promise.all([
          api.get("/portfolio-types/"),
          api.get("/portfolio-stocks/"),
        ]);
        const types = typesRes.data || [];
        setPortfolioTypes(types);
        setStocks(stocksRes.data || []);
        if (types.length > 0) {
          setSelectedType(String(types[0].id));
        }
      } catch (err) {
        setError(err?.response?.data?.detail || "Unable to load explore data.");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const filteredStocks = stocks.filter((s) => !selectedType || String(s.portfolio_type) === String(selectedType));

  return (
    <div className="page dashboard-page">
      <header className="topbar dashboard-topbar">
        <div>
          <p className="dashboard-brand mono"><span className="pulse-dot" /> Explore</p>
          <h2>Portfolio Explorer</h2>
          <p>Select a portfolio and open per-stock dashboard</p>
        </div>
        <div className="inline">
          <button onClick={() => navigate("/dashboard")}>Back to Dashboard</button>
        </div>
      </header>

      {loading && <section className="card"><p>Loading explore data...</p></section>}
      {error && <section className="card"><p className="error">{error}</p></section>}

      {!loading && !error && (
        <section className="card">
          <div className="inline">
            <label className="mono">Portfolio</label>
            <select value={selectedType} onChange={(e) => setSelectedType(e.target.value)}>
              {portfolioTypes.map((pt) => (
                <option key={pt.id} value={pt.id}>{pt.name}</option>
              ))}
            </select>
            <button onClick={() => navigate("/other-features")}>Open Other Features</button>
          </div>
          <div className="stock-list">
            {filteredStocks.map((stock) => (
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
                <small>{stock.symbol} | {stock.sector}</small>
              </button>
            ))}
            {filteredStocks.length === 0 && <p>No stocks found for this portfolio.</p>}
          </div>
        </section>
      )}
    </div>
  );
}

export default ExplorePage;
