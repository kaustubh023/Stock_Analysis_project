import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api";
import AppShell from "../components/AppShell";

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
  const selectedPortfolioName = portfolioTypes.find((pt) => String(pt.id) === String(selectedType))?.name || "All portfolios";

  return (
    <AppShell
      eyebrow="Portfolio Explorer"
      title="Inspect holdings by portfolio"
      subtitle="Filter positions, browse sectors, and open the full per-stock analytics page."
      actions={<button className="ghost-button" onClick={() => navigate("/other-features")}>Open feature hub</button>}
    >
      {loading && <section className="card"><p>Loading explore data...</p></section>}
      {error && <section className="card"><p className="error">{error}</p></section>}

      {!loading && !error && (
        <section className="content-grid content-grid-dashboard">
          <div className="card card-highlight">
            <div className="section-head">
              <div>
                <span className="section-kicker mono">Filters</span>
                <h3>Choose a portfolio</h3>
              </div>
              <span className="chip">{filteredStocks.length} stocks</span>
            </div>
            <div className="form-stack">
              <div className="input-group">
                <label className="mono">Portfolio</label>
                <select value={selectedType} onChange={(e) => setSelectedType(e.target.value)}>
                  {portfolioTypes.map((pt) => (
                    <option key={pt.id} value={pt.id}>{pt.name}</option>
                  ))}
                </select>
              </div>
              <div className="explore-summary">
                <strong>{selectedPortfolioName}</strong>
                <p>Open any stock below to view pricing, valuation, opportunity and trend analysis.</p>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="section-head">
              <div>
                <span className="section-kicker mono">Results</span>
                <h3>Stocks in this portfolio</h3>
              </div>
            </div>
            <div className="stock-list stock-list-spacious">
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
                  <div className="stock-item-title-row">
                    <div>{stock.company_name}</div>
                    <span className="chip chip-subtle mono">{stock.symbol}</span>
                  </div>
                  <small>{stock.sector}</small>
                </button>
              ))}
              {filteredStocks.length === 0 && <p className="empty-state">No stocks found for this portfolio.</p>}
            </div>
          </div>
        </section>
      )}
    </AppShell>
  );
}

export default ExplorePage;
