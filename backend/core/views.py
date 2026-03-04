from django.contrib.auth.models import User
from django.db.models import Q
from rest_framework import generics, permissions, status
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import PortfolioType, PortfolioStock
from .serializers import RegisterSerializer, PortfolioTypeSerializer, PortfolioStockSerializer
from .services import (
    compare_two_stocks,
    fetch_stock_metrics,
    gold_silver_correlation,
    portfolio_pe_comparison,
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
        return Response(
            {
                "username": user.username,
                "email": user.email,
                "access": token.key,
                "refresh": "",
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
        return Response(
            {
                "access": token.key,
                "refresh": "",
                "username": user.username,
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
