import { Suspense, lazy } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import ProtectedRoute from "./components/ProtectedRoute";
import { useAuth } from "./context/AuthContext";

const CompareStocksFeaturePage = lazy(() => import("./routes/CompareStocksFeature"));
const DashboardPage = lazy(() => import("./routes/Dashboard"));
const ExplorePage = lazy(() => import("./routes/Explore"));
const ExploreGoldSilverPage = lazy(() => import("./routes/ExploreGoldSilver"));
const LoginPage = lazy(() => import("./routes/Login"));
const OtherFeaturesPage = lazy(() => import("./routes/OtherFeatures"));
const PortfolioClusteringPage = lazy(() => import("./routes/PortfolioClustering"));
const RiskCategorizationFeaturePage = lazy(() => import("./routes/RiskCategorizationFeature"));
const StockDetailPage = lazy(() => import("./routes/StockDetail"));
const StockForecastFeaturePage = lazy(() => import("./routes/StockForecastFeature"));
const StockForecastResultPage = lazy(() => import("./routes/StockForecastResult"));
const BTCUSDForecastFeaturePage = lazy(() => import("./routes/BTCUSDForecastFeature"));

function App() {
  const { isAuthenticated } = useAuth();

  return (
    <Suspense fallback={<div style={{ padding: "24px", color: "#c6d4ff" }}>Loading...</div>}>
      <Routes>
        <Route path="/" element={<Navigate to={isAuthenticated ? "/dashboard" : "/login"} replace />} />
        <Route path="/login" element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <LoginPage />} />

        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <DashboardPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/portfolios"
          element={
            <ProtectedRoute>
              <DashboardPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/stocks"
          element={
            <ProtectedRoute>
              <ExplorePage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/stock/:symbol"
          element={
            <ProtectedRoute>
              <StockDetailPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/clusters"
          element={
            <ProtectedRoute>
              <PortfolioClusteringPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/explore"
          element={
            <ProtectedRoute>
              <ExplorePage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/other-features"
          element={
            <ProtectedRoute>
              <OtherFeaturesPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/features/compare-stocks"
          element={
            <ProtectedRoute>
              <CompareStocksFeaturePage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/features/risk-categorization"
          element={
            <ProtectedRoute>
              <RiskCategorizationFeaturePage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/features/portfolio-cluster"
          element={
            <ProtectedRoute>
              <PortfolioClusteringPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/features/stock-forecast"
          element={
            <ProtectedRoute>
              <StockForecastFeaturePage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/features/btc-usd-hourly"
          element={
            <ProtectedRoute>
              <BTCUSDForecastFeaturePage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/features/stock-forecast/result"
          element={
            <ProtectedRoute>
              <StockForecastResultPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/features/gold-silver"
          element={
            <ProtectedRoute>
              <ExploreGoldSilverPage />
            </ProtectedRoute>
          }
        />
      </Routes>
    </Suspense>
  );
}

export default App;
