from django.contrib.auth import get_user_model, login as auth_login
from rest_framework import generics, permissions
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework import permissions, status
from rest_framework.response import Response

from .serializers import (
    RegisterSerializer,
    UserSerializer,
    ChangePasswordSerializer,
    TwoFactorSetupSerializer,
    TwoFactorVerifySerializer,
    CustomTokenObtainPairSerializer,
)
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import pyotp

from apps.core.throttling import LoginThrottle



class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class LoginView(TokenObtainPairView):
    throttle_classes = [LoginThrottle]
    serializer_class = CustomTokenObtainPairSerializer

    # Allow CSRF exempt since JWT login is typically called from clients
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        if response.status_code == 200:
            # The JWT view has already verified the credentials.  Look up the
            # user directly rather than calling authenticate() again (which
            # would hash the password a second time).
            username = request.data.get("username")
            User = get_user_model()
            try:
                user = User.objects.get(username=username, is_active=True)
                user.backend = "django.contrib.auth.backends.ModelBackend"
                auth_login(request, user)
            except User.DoesNotExist:
                pass

        return response


class RefreshView(TokenRefreshView):
    permission_classes = [permissions.AllowAny]


class ChangePasswordView(generics.GenericAPIView):
    serializer_class = ChangePasswordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "密码已修改"}, status=status.HTTP_200_OK)


class TwoFactorSetupView(generics.GenericAPIView):
    serializer_class = TwoFactorSetupSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        # generate a new secret for the user (not yet enabled)
        secret = pyotp.random_base32()
        # construct otpauth url for QR code display
        issuer = request.get_host().split(":")[0]
        otpauth = pyotp.totp.TOTP(secret).provisioning_uri(name=user.email, issuer_name=issuer)
        # store secret on the user record temporarily until verification
        user.two_factor_secret = secret
        # ensure it's not enabled until verification
        user.two_factor_enabled = False
        user.save(update_fields=["two_factor_secret", "two_factor_enabled"])
        return Response({"otpauth_url": otpauth})


class TwoFactorVerifyView(generics.GenericAPIView):
    serializer_class = TwoFactorVerifySerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        # determine secret from user record
        secret = request.user.two_factor_secret
        # remember whether this is the initial setup (not yet enabled)
        initial_setup = not bool(request.user.two_factor_enabled)

        serializer = self.get_serializer(data=request.data, context={"request": request, "secret": secret})
        serializer.is_valid(raise_exception=True)

        # If this was the initial setup verification, enable 2FA and generate recovery codes
        resp = {"detail": "2FA 验证通过"}
        if initial_setup:
            request.user.two_factor_enabled = True
            # ensure secret remains stored (it was written during setup)
            # generate recovery codes and return them (plain) to user once
            recovery_codes = request.user.generate_recovery_codes()
            request.user.save(update_fields=["two_factor_enabled", "two_factor_recovery_codes"])
            resp = {"detail": "2FA 已启用", "recovery_codes": recovery_codes}

        return Response(resp)

class TwoFactorDisableView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        user.two_factor_enabled = False
        user.two_factor_secret = None
        user.two_factor_recovery_codes = []
        user.save(update_fields=["two_factor_enabled", "two_factor_secret", "two_factor_recovery_codes"])
        return Response({"detail": "2FA 已成功禁用"})
