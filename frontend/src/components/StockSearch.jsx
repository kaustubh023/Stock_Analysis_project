import { useEffect, useRef, useState } from "react";
import api from "../api";

export default function StockSearch({ value, onSelect }) {
  const [q, setQ] = useState(value || "");
  const [open, setOpen] = useState(false);
  const [options, setOptions] = useState([]);
  const ref = useRef(null);

  useEffect(() => {
    const onDoc = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener("click", onDoc);
    return () => document.removeEventListener("click", onDoc);
  }, []);

  useEffect(() => {
    let active = true;
    const load = async () => {
      const term = q.trim();
      if (!term) {
        setOptions([]);
        return;
      }
      try {
        const res = await api.get(`/stocks/search/?q=${encodeURIComponent(term)}`);
        if (!active) return;
        setOptions(res.data?.results || []);
        setOpen(true);
      } catch {
        setOptions([]);
      }
    };
    const id = setTimeout(load, 250);
    return () => {
      active = false;
      clearTimeout(id);
    };
  }, [q]);

  return (
    <div ref={ref} style={{ position: "relative", width: "100%" }}>
      <input
        value={q}
        onChange={(e) => {
          setQ(e.target.value);
          setOpen(true);
        }}
        placeholder="Ticker (e.g. TCS.NS)"
      />
      {open && (
        <div className="suggestions" style={{ position: "absolute", width: "100%", zIndex: 50 }}>
          {options.length > 0 ? (
            options.map((s) => (
              <button
                key={`${s.symbol}`}
                className="suggestion"
                onClick={() => {
                  setQ(s.symbol);
                  setOpen(false);
                  onSelect && onSelect(s.symbol, s);
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
  );
}
