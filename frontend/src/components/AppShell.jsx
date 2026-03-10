import { NavLink, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const navItems = [
  { to: "/dashboard", label: "Dashboard", match: ["/dashboard", "/portfolios"] },
  { to: "/explore", label: "Explore", match: ["/explore", "/stocks", "/stock/"] },
  { to: "/clusters", label: "Clusters", match: ["/clusters", "/features/portfolio-cluster"] },
  { to: "/other-features", label: "Features", match: ["/other-features", "/features/"] },
];

function isActive(pathname, item) {
  return item.match.some((prefix) => pathname.startsWith(prefix));
}

function AppShell({ eyebrow, title, subtitle, actions, children }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { username, logout: clearAuth } = useAuth();

  const logout = () => {
    clearAuth();
    navigate("/login", { replace: true });
  };

  return (
    <div className="app-shell">
      <aside className="app-sidebar">
        <div className="app-brand-block">
          <div className="app-brand-mark">
            <span className="pulse-dot" />
          </div>
          <div>
            <p className="app-brand-kicker mono">Market workspace</p>
            <h1>AutoVest Analytics</h1>
          </div>
        </div>

        <nav className="app-nav">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={`app-nav-link ${isActive(location.pathname, item) ? "active" : ""}`}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-card">
          <span className="sidebar-label mono">Signed in</span>
          <strong>{username || "Investor"}</strong>
          <p>Portfolio analytics, stock discovery, forecasting and cluster-based insights.</p>
        </div>

        <button className="sidebar-logout" onClick={logout}>Logout</button>
      </aside>

      <main className="app-main">
        <header className="app-header">
          <div>
            <p className="app-eyebrow mono">{eyebrow}</p>
            <h2>{title}</h2>
            <p className="app-subtitle">{subtitle}</p>
          </div>
          {actions ? <div className="app-actions">{actions}</div> : null}
        </header>
        <div className="app-content">{children}</div>
      </main>
    </div>
  );
}

export default AppShell;
