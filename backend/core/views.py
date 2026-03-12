from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

from django.contrib.auth.models import User
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import render
from rest_framework import generics, permissions, status
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken

from .models import PortfolioStock, PortfolioType
from .serializers import PortfolioStockSerializer, PortfolioTypeSerializer, RegisterSerializer
from .services import (
    build_portfolio_trend_analysis,
    categorize_portfolio_risk,
    compare_two_stocks,
    fetch_stock_metrics,
    forecast_stock_prices,
    get_cached_gold_silver_correlation,
    get_cached_portfolio_next_day_predictions,
    get_cached_portfolio_pe_comparison,
    gold_silver_correlation,
    portfolio_kmeans_projection,
    portfolio_next_day_predictions,
    portfolio_pe_comparison,
    search_indian_stocks,
)


def run_with_timeout(fn, *args, timeout: int):
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(fn, *args)
    try:
        return future.result(timeout=timeout)
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


class RegisterView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "username": user.username,
                "email": user.email,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "token": token.key,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = (request.data.get("username") or "").strip()
        password = request.data.get("password") or ""
        if not username or not password:
            return Response({"detail": "Username/email and password are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(Q(username__iexact=username) | Q(email__iexact=username))
        except User.DoesNotExist:
            return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        candidate_passwords = [password]
        stripped = password.strip()
        if stripped != password:
            candidate_passwords.append(stripped)

        if not any(user.check_password(candidate) for candidate in candidate_passwords):
            return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        token, _ = Token.objects.get_or_create(user=user)
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "username": user.username,
                "token": token.key,
            }
        )


class UserExistsView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        username = (request.query_params.get("username") or "").strip()
        if not username:
            return Response({"exists": False})
        exists = User.objects.filter(Q(username__iexact=username) | Q(email__iexact=username)).exists()
        return Response({"exists": exists})


class PortfolioTypeListCreateView(generics.ListCreateAPIView):
    serializer_class = PortfolioTypeSerializer

    def get_queryset(self):
        return PortfolioType.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class PortfolioStockListCreateView(generics.ListCreateAPIView):
    serializer_class = PortfolioStockSerializer

    def get_queryset(self):
        queryset = PortfolioStock.objects.filter(user=self.request.user).select_related("portfolio_type")
        portfolio_type_id = self.request.query_params.get("portfolio_type")
        if portfolio_type_id:
            queryset = queryset.filter(portfolio_type_id=portfolio_type_id)
        return queryset


class PortfolioStockDeleteView(generics.DestroyAPIView):
    serializer_class = PortfolioStockSerializer

    def get_queryset(self):
        return PortfolioStock.objects.filter(user=self.request.user)


class StockSearchView(APIView):
    def get(self, request):
        query = request.query_params.get("q", "").strip()
        return Response({"results": search_indian_stocks(query)})


class StockAnalyticsView(APIView):
    def get(self, request, symbol):
        try:
            data = fetch_stock_metrics(symbol)
            return Response(data)
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class PortfolioPEComparisonView(APIView):
    def get(self, request):
        symbols = list(
            PortfolioStock.objects.filter(user=request.user)
            .values_list("symbol", flat=True)
            .distinct()
        )
        try:
            result = run_with_timeout(portfolio_pe_comparison, symbols, timeout=12)
            return Response({"items": result})
        except FuturesTimeoutError:
            return Response(
                {
                    "items": get_cached_portfolio_pe_comparison(symbols),
                    "detail": "PE comparison timed out while fetching market data. Showing cached values where available.",
                }
            )


class CompareStocksView(APIView):
    def post(self, request):
        symbol_a = request.data.get("symbol_a")
        symbol_b = request.data.get("symbol_b")

        owned_symbols = set(
            PortfolioStock.objects.filter(user=request.user).values_list("symbol", flat=True)
        )

        if symbol_a not in owned_symbols or symbol_b not in owned_symbols:
            return Response(
                {"detail": "Both stocks must belong to your portfolio."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            return Response(compare_two_stocks(symbol_a, symbol_b))
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class GoldSilverCorrelationView(APIView):
    def get(self, request):
        try:
            result = run_with_timeout(gold_silver_correlation, timeout=15)
            return Response(result)
        except FuturesTimeoutError:
            cached = get_cached_gold_silver_correlation()
            if cached is not None:
                payload = dict(cached)
                payload["detail"] = "Gold/silver refresh timed out. Showing cached analysis."
                return Response(payload)
            return Response(
                {"detail": "Gold/silver analysis timed out while fetching market data. Please retry shortly."},
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class PortfolioClusteringView(APIView):
    def get(self, request):
        try:
            k = int(request.query_params.get("k", 3))
        except ValueError:
            k = 3
        method = (request.query_params.get("method") or "pca").lower()
        raw_stocks = list(
            PortfolioStock.objects.filter(user=request.user)
            .values("symbol", "company_name", "sector")
        )
        seen = set()
        stocks = []
        for stock in raw_stocks:
            symbol = (stock.get("symbol") or "").strip().upper()
            if not symbol or symbol in seen:
                continue
            seen.add(symbol)
            stock["symbol"] = symbol
            stocks.append(stock)
        try:
            result = run_with_timeout(portfolio_kmeans_projection, stocks, k, method, timeout=15)
            return Response(result)
        except FuturesTimeoutError:
            return Response(
                {
                    "items": [],
                    "cluster_summary": [],
                    "method_used": "pca",
                    "k": max(2, min(k, 6)),
                    "detail": "Clustering timed out while fetching market data. Please retry shortly.",
                    "skipped": 0,
                }
            )
        except Exception:
            return Response(
                {
                    "items": [],
                    "cluster_summary": [],
                    "method_used": "pca",
                    "k": max(2, min(k, 6)),
                    "detail": "Clustering data is temporarily unavailable due to market data rate limits. Please retry shortly.",
                    "skipped": 0,
                }
            )


class RiskCategorizationView(APIView):
    def get(self, request):
        stocks = list(
            PortfolioStock.objects.filter(user=request.user)
            .values("symbol", "company_name", "sector")
            .distinct()
        )
        try:
            result = run_with_timeout(categorize_portfolio_risk, stocks, timeout=12)
            return Response(result)
        except FuturesTimeoutError:
            return Response(
                {"detail": "Risk categorization timed out while fetching market data. Please retry in a moment."},
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class StockForecastView(APIView):
    def post(self, request):
        symbol = request.data.get("symbol")
        forecast_days = request.data.get("forecast_days", 30)
        try:
            return Response(forecast_stock_prices(symbol=symbol, forecast_days=forecast_days))
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class PortfolioNextDayForecastView(APIView):
    def get(self, request):
        raw_stocks = list(
            PortfolioStock.objects.filter(user=request.user)
            .values("symbol", "company_name", "sector")
            .distinct()
        )
        seen = set()
        stocks = []
        for stock in raw_stocks:
            symbol = (stock.get("symbol") or "").strip().upper()
            if not symbol or symbol in seen:
                continue
            seen.add(symbol)
            stock["symbol"] = symbol
            stocks.append(stock)
        try:
            result = run_with_timeout(portfolio_next_day_predictions, stocks, timeout=15)
            return Response(result)
        except FuturesTimeoutError:
            return Response(
                {
                    **get_cached_portfolio_next_day_predictions(stocks),
                    "detail": "Portfolio forecast timed out while fetching market data. Showing cached values where available.",
                }
            )
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


def portfolio_trend_analysis_page(request):
    user = request.user if request.user.is_authenticated else None
    if user is None:
        token_key = (request.GET.get("token") or "").strip()
        if token_key:
            try:
                user = Token.objects.select_related("user").get(key=token_key).user
            except Token.DoesNotExist:
                try:
                    jwt_auth = JWTAuthentication()
                    validated_token = jwt_auth.get_validated_token(token_key)
                    user = jwt_auth.get_user(validated_token)
                except Exception:
                    user = None
    if user is None:
        return HttpResponseForbidden("Authentication required.")

    requested_symbol = (request.GET.get("symbol") or "").strip().upper()
    stocks_qs = PortfolioStock.objects.filter(user=user)
    if requested_symbol:
        stocks_qs = stocks_qs.filter(symbol__iexact=requested_symbol)

    stocks = list(stocks_qs.values("symbol", "company_name").distinct())
    trend_items = build_portfolio_trend_analysis(stocks)
    return render(
        request,
        "core/portfolio_trend_analysis.html",
        {
            "trend_items": trend_items,
            "selected_symbol": requested_symbol,
        },
    )
