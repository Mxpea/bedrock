from django.urls import path

from .views import (
    LoginView,
    MeView,
    RefreshView,
    RegisterView,
    ChangePasswordView,
    TwoFactorSetupView,
    TwoFactorVerifyView,
    TwoFactorDisableView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("refresh/", RefreshView.as_view(), name="refresh"),
    path("me/", MeView.as_view(), name="me"),
    path("password/change/", ChangePasswordView.as_view(), name="change-password"),
    path("2fa/setup/", TwoFactorSetupView.as_view(), name="2fa-setup"),
    path("2fa/verify/", TwoFactorVerifyView.as_view(), name="2fa-verify"),
    path("2fa/disable/", TwoFactorDisableView.as_view(), name="2fa-disable"),
]
