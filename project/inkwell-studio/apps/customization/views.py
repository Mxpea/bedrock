from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .css_validator import validate_advanced_css
from .models import AdvancedStyleGrant, AuthorHomepageConfig, CSSSecurityEvent, CustomCSSRequest, ThemeConfig, CustomFont
from .permissions import IsAdminRole
from .serializers import (
    AdvancedStyleGrantSerializer,
    AuthorHomepageConfigSerializer,
    CSSRequestReviewSerializer,
    CSSSecurityEventSerializer,
    CustomCSSRequestSerializer,
    ThemeConfigSerializer,
    CustomFontSerializer,
)


class CustomFontViewSet(viewsets.ModelViewSet):
    serializer_class = CustomFontSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            from django.db.models import Q
            return CustomFont.objects.filter(Q(is_public=True) | Q(uploader=user))
        return CustomFont.objects.filter(is_public=True)

    def perform_create(self, serializer):
        serializer.save(uploader=self.request.user)


class ThemeConfigViewSet(viewsets.ModelViewSet):
    serializer_class = ThemeConfigSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ThemeConfig.objects.select_related("novel").filter(novel__author=self.request.user)


class CustomCSSRequestViewSet(viewsets.ModelViewSet):
    serializer_class = CustomCSSRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or getattr(user, "role", "") == "admin":
            return CustomCSSRequest.objects.select_related("applicant", "novel", "reviewed_by").all()
        return CustomCSSRequest.objects.select_related("novel").filter(applicant=user)

    def perform_create(self, serializer):
        serializer.save(applicant=self.request.user)

    @action(detail=True, methods=["post"], permission_classes=[IsAdminRole])
    def review(self, request, pk=None):
        obj = self.get_object()
        review_serializer = CSSRequestReviewSerializer(data=request.data)
        review_serializer.is_valid(raise_exception=True)

        status_value = review_serializer.validated_data["status"]
        review_note = review_serializer.validated_data.get("review_note", "")

        result = validate_advanced_css(obj.css_snippet)
        obj.blocked_reasons = result.blocked_reasons
        obj.warning_reasons = result.warning_reasons

        if status_value == CustomCSSRequest.Status.APPROVED and not result.is_valid:
            return Response(
                {"detail": "CSS 命中危险规则，不能审批通过", "blocked_reasons": result.blocked_reasons},
                status=status.HTTP_400_BAD_REQUEST,
            )

        obj.mark_reviewed(reviewer=request.user, status=status_value, note=review_note)
        obj.save(
            update_fields=[
                "status",
                "review_note",
                "reviewed_by",
                "reviewed_at",
                "blocked_reasons",
                "warning_reasons",
                "updated_at",
            ]
        )

        if status_value == CustomCSSRequest.Status.APPROVED:
            scope = AdvancedStyleGrant.Scope.NOVEL if obj.novel_id else AdvancedStyleGrant.Scope.ACCOUNT
            grant, _ = AdvancedStyleGrant.objects.get_or_create(
                user=obj.applicant,
                novel=obj.novel if scope == AdvancedStyleGrant.Scope.NOVEL else None,
                scope=scope,
                defaults={"granted_by": request.user, "enabled": True},
            )
            if not grant.enabled:
                grant.enabled = True
                grant.granted_by = request.user
                grant.save(update_fields=["enabled", "granted_by", "updated_at"])

            if result.warning_reasons and obj.novel_id:
                rollback = any("全屏劫持" in warning for warning in result.warning_reasons)
                if rollback:
                    grant.enabled = False
                    grant.save(update_fields=["enabled", "updated_at"])
                CSSSecurityEvent.objects.create(
                    novel=obj.novel,
                    triggered_by=obj.applicant,
                    severity=CSSSecurityEvent.Severity.WARNING,
                    reason=";".join(result.warning_reasons),
                    matched_css_fragment=obj.css_snippet[:500],
                    auto_rollback_applied=rollback,
                )

        return Response(CustomCSSRequestSerializer(obj, context={"request": request}).data)


class AdvancedStyleGrantViewSet(mixins.ListModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    serializer_class = AdvancedStyleGrantSerializer
    permission_classes = [IsAdminRole]
    queryset = AdvancedStyleGrant.objects.select_related("user", "novel", "granted_by").all()


class AuthorHomepageConfigViewSet(viewsets.ModelViewSet):
    serializer_class = AuthorHomepageConfigSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return AuthorHomepageConfig.objects.filter(author=self.request.user)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class CSSSecurityEventViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = CSSSecurityEventSerializer
    permission_classes = [IsAdminRole]
    queryset = CSSSecurityEvent.objects.select_related("novel", "triggered_by").all()
