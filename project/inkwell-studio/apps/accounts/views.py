from django.contrib.auth import get_user_model, login as auth_login
from rest_framework import generics, permissions
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.core.throttling import LoginThrottle

from .serializers import RegisterSerializer, UserSerializer


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class MeView(generics.RetrieveAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class LoginView(TokenObtainPairView):
    throttle_classes = [LoginThrottle]

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
