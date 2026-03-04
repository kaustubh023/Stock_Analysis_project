from django.contrib.auth.models import User
from rest_framework import serializers
from .models import PortfolioType, PortfolioStock


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ["username", "email", "password"]

    def create(self, validated_data):
        validated_data["username"] = (validated_data.get("username") or "").strip()
        validated_data["email"] = (validated_data.get("email") or "").strip().lower()
        validated_data["password"] = (validated_data.get("password") or "").strip()
        return User.objects.create_user(**validated_data)


class PortfolioTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortfolioType
        fields = ["id", "name", "created_at"]


class PortfolioStockSerializer(serializers.ModelSerializer):
    portfolio_type_name = serializers.CharField(source="portfolio_type.name", read_only=True)

    class Meta:
        model = PortfolioStock
        fields = [
            "id",
            "portfolio_type",
            "portfolio_type_name",
            "sector",
            "symbol",
            "company_name",
            "created_at",
        ]

    def validate(self, attrs):
        request = self.context["request"]
        portfolio_type = attrs["portfolio_type"]
        if portfolio_type.user_id != request.user.id:
            raise serializers.ValidationError("Invalid portfolio type for this user.")
        return attrs

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)
