import { useState } from "react";
import api from "../api";
import { useAuth } from "../context/AuthContext";

function LoginPage() {
  const { login, logout } = useAuth();
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
    logout();
    try {
      if (isRegister) {
        let registerResp = null;
        try {
          registerResp = await api.post("/user/register/", form);
        } catch (regErr) {
          const data = regErr?.response?.data || {};
          const raw = JSON.stringify(data).toLowerCase();
          const alreadyExists =
            raw.includes("already exists") ||
            raw.includes("already taken") ||
            raw.includes("unique");
          if (!alreadyExists) {
            throw regErr;
          }
        }
        if (registerResp?.data?.access) {
          login({
            access: registerResp.data.access,
            refresh: registerResp.data.refresh || "",
            username: registerResp.data.username || form.username,
          });
          window.location.replace("/dashboard");
          return;
        }
      }
      const resp = await api.post("/user/login/", { username: form.username, password: form.password });
      login({
        access: resp.data.access,
        refresh: resp.data.refresh,
        username: resp.data.username,
      });
      window.location.replace("/dashboard");
    } catch (err) {
      if (!isRegister) {
        try {
          const check = await api.get(`/auth/user-exists/?username=${encodeURIComponent(form.username)}`);
          if (!check.data?.exists) {
            setIsRegister(true);
            setError("Account does not exist. Please create an account first.");
            return;
          }
        } catch {
          // ignore
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
            <div className="mono">NIFTY 50 Â· +1.24% Â· 22,450.30</div>
            <svg viewBox="0 0 200 38"><polyline points="2,30 38,24 68,27 98,17 126,20 162,11 198,8" /></svg>
          </div>
          <div className="float-card f2">
            <div className="mono">SENSEX Â· -0.38% Â· 73,912.11</div>
            <svg viewBox="0 0 200 38" className="neg"><polyline points="2,8 36,12 66,16 98,18 126,24 162,28 198,32" /></svg>
          </div>
          <div className="float-card f3">
            <div className="mono">Your Portfolio Â· â–² 8.3% this month</div>
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

export default LoginPage;
