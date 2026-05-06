from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from .models import InviteCode, User
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import exceptions

import pyotp


class RegisterSerializer(serializers.ModelSerializer):
    invite_code = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["username", "email", "password", "invite_code"]

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate_invite_code(self, value):
        # Allow first user to register without an invite code
        if not User.objects.exists():
            return value
        try:
            from apps.adminpanel.models import PlatformSetting

            setting = PlatformSetting.get_solo()
            require_invite = setting.registration_mode == PlatformSetting.RegistrationMode.INVITE_ONLY
        except PlatformSetting.DoesNotExist:
            require_invite = False

        if require_invite and not value:
            raise serializers.ValidationError("当前站点仅支持邀请码注册")

        if not value:
            return value
        try:
            invite = InviteCode.objects.get(code=value, is_active=True, used_by__isnull=True)
        except InviteCode.DoesNotExist as exc:
            raise serializers.ValidationError("邀请码无效或已使用") from exc
        return invite

    def create(self, validated_data):
        invite = validated_data.pop("invite_code", "")
        password = validated_data.pop("password")
        with transaction.atomic():
            is_first_user = not User.objects.exists()

            user = User(**validated_data)
            user.set_password(password)
            if is_first_user:
                user.role = User.Role.ADMIN
                user.is_staff = True
                user.is_superuser = True
            user.save()

            if invite:
                invite.used_by = user
                invite.is_active = False
                invite.used_at = timezone.now()
                invite.save(update_fields=["used_by", "is_active", "used_at", "updated_at"])

        return user


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        validate_password(value)
        return value

    def validate(self, attrs):
        user = self.context["request"].user
        if not user.check_password(attrs.get("old_password")):
            raise serializers.ValidationError({"old_password": "旧密码不正确"})
        return attrs

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save()
        return user


class TwoFactorSetupSerializer(serializers.Serializer):
    # returns otpauth_url to display as QR
    def to_representation(self, instance):
        return {"otpauth_url": instance}


class TwoFactorVerifySerializer(serializers.Serializer):
    code = serializers.CharField()

    def validate_code(self, value):
        if not value or not str(value).strip():
            raise serializers.ValidationError("Code不能为空")
        return value

    def validate(self, attrs):
        user = self.context["request"].user
        secret = self.context.get("secret") or user.two_factor_secret
        if not secret:
            raise serializers.ValidationError("No 2FA secret configured")

        code = str(attrs.get("code"))
        totp = pyotp.TOTP(secret)
        # accept TOTP codes (allow small clock drift)
        if totp.verify(code, valid_window=2):
            return attrs

        # fallback: check recovery codes via model helper
        if user.verify_and_consume_recovery_code(code):
            return attrs

        raise serializers.ValidationError({"code": "Invalid one-time code"})


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)

        user = self.user
        # If user has 2FA enabled, require an `otp` field in the request and validate it
        if getattr(user, "two_factor_enabled", False):
            req = self.context["request"].data
            otp = req.get("otp")
            recovery = req.get("recovery_code")
            secret = getattr(user, "two_factor_secret", None)

            # try OTP first
            if otp:
                if not secret:
                    raise exceptions.AuthenticationFailed("Two-factor not configured")
                totp = pyotp.TOTP(secret)
                if not totp.verify(otp, valid_window=2):
                    # otp invalid, but allow recovery if provided below
                    if not recovery:
                        raise exceptions.AuthenticationFailed("Invalid two-factor code")
                else:
                    return data

            # fallback to recovery code
            if recovery:
                if not user.verify_and_consume_recovery_code(recovery):
                    raise exceptions.AuthenticationFailed("Invalid recovery code")
            else:
                # neither otp nor recovery provided/valid
                raise exceptions.AuthenticationFailed("Two-factor code required")

        return data


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "role", "custom_level", "is_staff", "is_superuser", "date_joined", "two_factor_enabled"]
        read_only_fields = ["id", "role", "custom_level", "is_staff", "is_superuser", "date_joined", "two_factor_enabled"]
