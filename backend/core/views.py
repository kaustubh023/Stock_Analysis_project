from django.contrib.auth.models import User
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import render
from rest_framework import generics, permissions, status
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken

from .models import PortfolioType, PortfolioStock
from .serializers import RegisterSerializer, PortfolioTypeSerializer, PortfolioStockSerializer
from .services import (
    compare_two_stocks,
    categorize_portfolio_risk,
    fetch_stock_metrics,
    forecast_stock_prices,
    portfolio_next_day_predictions,
    gold_silver_correlation,
    portfolio_kmeans_projection,
    portfolio_pe_comparison,
    build_portfolio_trend_analysis,
    search_indian_stocks,
)


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
        return Response({"items": portfolio_pe_comparison(symbols)})


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
            return Response(gold_silver_correlation())
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
        # Deduplicate by symbol to avoid repeated API pulls for same stock in different sectors/types.
        seen = set()
        stocks = []
        for s in raw_stocks:
            sym = (s.get("symbol") or "").strip().upper()
            if not sym or sym in seen:
                continue
            seen.add(sym)
            s["symbol"] = sym
            stocks.append(s)
        try:
            result = portfolio_kmeans_projection(stocks=stocks, k=k, method=method)
            return Response(result)
        except Exception:
            # Graceful fallback so UI is not blocked by upstream rate limits.
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
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(categorize_portfolio_risk, stocks)
                result = future.result(timeout=12)
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
        for s in raw_stocks:
            sym = (s.get("symbol") or "").strip().upper()
            if not sym or sym in seen:
                continue
            seen.add(sym)
            s["symbol"] = sym
            stocks.append(s)
        try:
            result = portfolio_next_day_predictions(stocks)
            return Response(result)
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
