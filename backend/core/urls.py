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
)

urlpatterns = [
    path("portfolio-types/", PortfolioTypeListCreateView.as_view(), name="portfolio-types"),
    path("portfolio-stocks/", PortfolioStockListCreateView.as_view(), name="portfolio-stocks"),
    path("portfolio-stocks/<int:pk>/", PortfolioStockDeleteView.as_view(), name="portfolio-stock-delete"),
    path("stocks/search/", StockSearchView.as_view(), name="stock-search"),
    path("stocks/<str:symbol>/analytics/", StockAnalyticsView.as_view(), name="stock-analytics"),
    path("portfolio/pe-comparison/", PortfolioPEComparisonView.as_view(), name="portfolio-pe-comparison"),
    path("portfolio/compare/", CompareStocksView.as_view(), name="compare-stocks"),
    path("commodities/gold-silver-correlation/", GoldSilverCorrelationView.as_view(), name="gold-silver-correlation"),
]
