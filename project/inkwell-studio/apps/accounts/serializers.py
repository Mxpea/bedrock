from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers

from .models import InviteCode, User


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
                invite.save(update_fields=["used_by", "is_active", "updated_at"])

        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "role", "date_joined"]
