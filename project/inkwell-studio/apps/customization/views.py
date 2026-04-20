from PIL import Image
from io import BytesIO
from uuid import uuid4
from django.core.files.base import ContentFile
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
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

    @action(
        detail=False,
        methods=["post"],
        parser_classes=[MultiPartParser, FormParser],
        permission_classes=[permissions.IsAuthenticated],
    )
    def upload_background(self, request):
        novel_id = request.data.get("novel")
        image_file = request.FILES.get("background_image")

        if not novel_id:
            return Response({"detail": "缺少工作区ID"}, status=status.HTTP_400_BAD_REQUEST)
        if not image_file:
            return Response({"detail": "未上传背景图片"}, status=status.HTTP_400_BAD_REQUEST)
        if not (image_file.content_type or "").startswith("image/"):
            return Response({"detail": "仅支持图片文件"}, status=status.HTTP_400_BAD_REQUEST)
        if image_file.size > 12 * 1024 * 1024:
            return Response({"detail": "背景图片大小不能超过 12MB"}, status=status.HTTP_400_BAD_REQUEST)

        from apps.novels.models import Novel

        novel = Novel.objects.filter(id=novel_id, author=request.user, is_deleted=False).first()
        if not novel:
            return Response({"detail": "工作区不存在或无权访问"}, status=status.HTTP_404_NOT_FOUND)

        theme_config, _ = ThemeConfig.objects.get_or_create(novel=novel)
        if theme_config.background_image:
            theme_config.background_image.delete(save=False)

        theme_config.background_image = image_file
        theme_config.save(update_fields=["background_image", "updated_at"])

        serializer = self.get_serializer(theme_config)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def clear_background(self, request, pk=None):
        theme_config = self.get_object()
        if theme_config.background_image:
            theme_config.background_image.delete(save=False)
            theme_config.background_image = None
            theme_config.save(update_fields=["background_image", "updated_at"])
        serializer = self.get_serializer(theme_config)
        return Response(serializer.data, status=status.HTTP_200_OK)


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

    @action(detail=False, methods=["get", "patch"], permission_classes=[permissions.IsAuthenticated])
    def mine(self, request):
        config, _ = AuthorHomepageConfig.objects.get_or_create(author=request.user)
        if request.method == "GET":
            serializer = self.get_serializer(config)
            return Response(serializer.data)

        serializer = self.get_serializer(config, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(author=request.user)
        return Response(serializer.data)

    @action(detail=False, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def publish(self, request):
        config, _ = AuthorHomepageConfig.objects.get_or_create(author=request.user)
        config.page_schema_published = config.page_schema_draft or {}
        config.save(update_fields=["page_schema_published", "updated_at"])
        serializer = self.get_serializer(config)
        return Response(serializer.data)



    @action(
        detail=False,
        methods=["post"],
        permission_classes=[permissions.IsAuthenticated],
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_header(self, request):
        config, _ = AuthorHomepageConfig.objects.get_or_create(author=request.user)
        image_file = request.FILES.get("header_image")
        if not image_file:
            return Response({"detail": "未上头图"}, status=status.HTTP_400_BAD_REQUEST)
        if config.header_image:
            config.header_image.delete(save=False)
        config.header_image = image_file
        config.save(update_fields=["header_image", "updated_at"])
        serializer = self.get_serializer(config)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=["post"],
        permission_classes=[permissions.IsAuthenticated],
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_avatar(self, request):
        config, _ = AuthorHomepageConfig.objects.get_or_create(author=request.user)
        image_file = request.FILES.get("avatar")
        if not image_file:
            return Response({"detail": "未上传头像"}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            img = Image.open(image_file)
            
            if img.mode != "RGB":
                img = img.convert("RGB")
                
            width, height = img.size
            new_size = min(width, height)
            left = (width - new_size) / 2
            top = (height - new_size) / 2
            right = (width + new_size) / 2
            bottom = (height + new_size) / 2
            
            img = img.crop((left, top, right, bottom))
            
            img = img.resize((512, 512), Image.Resampling.LANCZOS)
            
            img_io = BytesIO()
            img.save(img_io, format='JPEG', quality=90)
            file_name = f"{request.user.username}_avatar_{uuid4().hex[:8]}.jpg"
            img_content = ContentFile(img_io.getvalue(), name=file_name)
            
            if config.avatar:
                config.avatar.delete(save=False)
                
            config.avatar = img_content
            config.save(update_fields=["avatar", "updated_at"])
            
            serializer = self.get_serializer(config)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({"detail": f"头像处理失败: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)


class CSSSecurityEventViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = CSSSecurityEventSerializer
    permission_classes = [IsAdminRole]
    queryset = CSSSecurityEvent.objects.select_related("novel", "triggered_by").all()
