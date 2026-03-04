# Generated manually for this scaffold
from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="PortfolioType",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="portfolio_types", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["name"], "unique_together": {("user", "name")}},
        ),
        migrations.CreateModel(
            name="PortfolioStock",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sector", models.CharField(max_length=120)),
                ("symbol", models.CharField(max_length=25)),
                ("company_name", models.CharField(max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("portfolio_type", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="stocks", to="core.portfoliotype")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="portfolio_stocks", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["company_name"], "unique_together": {("user", "portfolio_type", "symbol")}},
        ),
    ]
