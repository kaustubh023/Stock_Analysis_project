from django.urls import path, include
from core.views import RegisterView, LoginView, UserExistsView

urlpatterns = [
    path("api/auth/register/", RegisterView.as_view(), name="register"),
    path("api/auth/login/", LoginView.as_view(), name="login"),
    path("api/auth/user-exists/", UserExistsView.as_view(), name="user_exists"),
    path("api/", include("core.urls")),
]
