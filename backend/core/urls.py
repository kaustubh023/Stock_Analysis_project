from django.urls import path
from .views import (
    PortfolioTypeListCreateView,
    PortfolioStockListCreateView,
    PortfolioStockDeleteView,
    StockSearchView,
    StockAnalyticsView,
    PortfolioPEComparisonView,
    CompareStocksView,
    GoldSilverCorrelationView,
    PortfolioClusteringView,
    RiskCategorizationView,
    StockForecastView,
    PortfolioNextDayForecastView,
)

urlpatterns = [
    path("portfolio-types/", PortfolioTypeListCreateView.as_view(), name="portfolio-types"),
    path("portfolio-stocks/", PortfolioStockListCreateView.as_view(), name="portfolio-stocks"),
    path("portfolio-stocks/<int:pk>/", PortfolioStockDeleteView.as_view(), name="portfolio-stock-delete"),
    path("stocks/search/", StockSearchView.as_view(), name="stock-search"),
    path("stocks/<str:symbol>/analytics/", StockAnalyticsView.as_view(), name="stock-analytics"),
    path("portfolio/pe-comparison/", PortfolioPEComparisonView.as_view(), name="portfolio-pe-comparison"),
    path("portfolio/compare/", CompareStocksView.as_view(), name="compare-stocks"),
    path("portfolio/clustering/", PortfolioClusteringView.as_view(), name="portfolio-clustering"),
    path("commodities/gold-silver-correlation/", GoldSilverCorrelationView.as_view(), name="gold-silver-correlation"),
    path("dashboard/<str:symbol>/", StockAnalyticsView.as_view(), name="dashboard-stock"),
    path("stock/compare/", CompareStocksView.as_view(), name="stock-compare-stocks"),
    path("stock/risk-categorization/", RiskCategorizationView.as_view(), name="stock-risk-categorization"),
    path("stock/portfolio-cluster/", PortfolioClusteringView.as_view(), name="stock-portfolio-cluster"),
    path("stock/forecast/", StockForecastView.as_view(), name="stock-forecast"),
    path("stock/portfolio-forecast-next-day/", PortfolioNextDayForecastView.as_view(), name="stock-portfolio-forecast-next-day"),
]
