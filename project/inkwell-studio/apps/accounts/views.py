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


class RefreshView(TokenRefreshView):
    permission_classes = [permissions.AllowAny]
