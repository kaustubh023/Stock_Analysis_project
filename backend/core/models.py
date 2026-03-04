from django.db import models
from django.contrib.auth.models import User


class PortfolioType(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="portfolio_types")
    name = models.CharField(max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "name")
        ordering = ["name"]

    def __str__(self):
        return f"{self.user.username} - {self.name}"


class PortfolioStock(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="portfolio_stocks")
    portfolio_type = models.ForeignKey(PortfolioType, on_delete=models.CASCADE, related_name="stocks")
    sector = models.CharField(max_length=120)
    symbol = models.CharField(max_length=25)
    company_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "portfolio_type", "symbol")
        ordering = ["company_name"]

    def __str__(self):
        return f"{self.symbol} ({self.company_name})"
