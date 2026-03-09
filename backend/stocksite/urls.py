from django.urls import path, include
from core.views import RegisterView, LoginView, UserExistsView, portfolio_trend_analysis_page
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path("portfolio/trend-analysis/", portfolio_trend_analysis_page, name="portfolio-trend-analysis-page"),
    path("api/auth/register/", RegisterView.as_view(), name="register"),
    path("api/auth/login/", LoginView.as_view(), name="login"),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh_legacy"),
    path("api/auth/user-exists/", UserExistsView.as_view(), name="user_exists"),
    path("api/user/register/", RegisterView.as_view(), name="user-register"),
    path("api/user/login/", LoginView.as_view(), name="user-login"),
    path("api/user/token/refresh/", TokenRefreshView.as_view(), name="user-token-refresh"),
    path("api/", include("forecast.urls")),
    path("api/", include("core.urls")),
]
