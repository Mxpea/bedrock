import os
import uuid

from django.core.files.storage import default_storage
from django.utils.text import slugify
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from django.db.models import Q

from apps.customization.markdown_extensions import sanitize_advanced_content, sanitize_standard_content
from apps.customization.models import AdvancedStyleGrant
from .models import Chapter, Novel
from .permissions import CanReadNovel, IsAuthorOrReadOnly
from .serializers import ChapterSerializer, NovelSerializer


class NovelViewSet(viewsets.ModelViewSet):
    serializer_class = NovelSerializer
    filterset_fields = ["visibility"]
    search_fields = ["title", "summary"]
    ordering_fields = ["created_at", "updated_at", "title", "last_open_module"]

    def get_permissions(self):
        if self.action in {"list", "retrieve"}:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated(), IsAuthorOrReadOnly(), CanReadNovel()]

    def get_queryset(self):
        user = self.request.user
        queryset = Novel.objects.filter(is_deleted=False)

        owner_filter = self.request.GET.get("owner")
        if owner_filter == "me" and user.is_authenticated:
            return queryset.filter(author=user)

        if user.is_authenticated:
            return queryset.filter(Q(author=user) | Q(visibility__in=[Novel.Visibility.PUBLIC, Novel.Visibility.LINK]))

        return queryset.filter(visibility=Novel.Visibility.PUBLIC)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def perform_destroy(self, instance):
        if instance.author != self.request.user:
            raise PermissionDenied("只有作者可以删除作品")
        instance.is_deleted = True
        instance.save(update_fields=["is_deleted", "updated_at"])


class ChapterViewSet(viewsets.ModelViewSet):
    serializer_class = ChapterSerializer
    permission_classes = [permissions.IsAuthenticated, IsAuthorOrReadOnly]
    filterset_fields = ["novel", "is_published"]
    search_fields = ["title", "content_md"]
    ordering_fields = ["order", "created_at"]

    def get_queryset(self):
        user = self.request.user
        return Chapter.objects.select_related("novel").filter(novel__author=user, novel__is_deleted=False)

    def perform_create(self, serializer):
        novel = serializer.validated_data["novel"]
        if novel.author != self.request.user:
            raise PermissionDenied("只能向自己的作品新增章节")
        chapter = serializer.save()
        novel.last_open_module = Novel.Module.WRITING
        novel.last_open_chapter_id = chapter.id
        novel.save(update_fields=["last_open_module", "last_open_chapter_id", "updated_at"])

    def perform_update(self, serializer):
        chapter = serializer.save()
        novel = chapter.novel
        if novel.author == self.request.user:
            novel.last_open_module = Novel.Module.WRITING
            novel.last_open_chapter_id = chapter.id
            novel.save(update_fields=["last_open_module", "last_open_chapter_id", "updated_at"])

    @action(detail=False, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def render_preview(self, request):
        content_md = request.data.get("content_md", "")
        novel_id = request.data.get("novel")

        use_advanced = False
        if novel_id:
            novel = Novel.objects.filter(id=novel_id, author=request.user, is_deleted=False).first()
            if novel:
                use_advanced = AdvancedStyleGrant.objects.filter(
                    Q(user=request.user, enabled=True, scope=AdvancedStyleGrant.Scope.ACCOUNT)
                    | Q(user=request.user, novel=novel, enabled=True, scope=AdvancedStyleGrant.Scope.NOVEL)
                ).exists()

        rendered = sanitize_advanced_content(content_md) if use_advanced else sanitize_standard_content(content_md)
        return Response({"html": rendered})

    @action(
        detail=False,
        methods=["post"],
        permission_classes=[permissions.IsAuthenticated],
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_image(self, request):
        novel_id = request.data.get("novel")
        if not novel_id:
            return Response({"detail": "缺少工作区ID"}, status=status.HTTP_400_BAD_REQUEST)

        novel = Novel.objects.filter(id=novel_id, author=request.user, is_deleted=False).first()
        if not novel:
            return Response({"detail": "工作区不存在或无权访问"}, status=status.HTTP_404_NOT_FOUND)

        image_file = request.FILES.get("image")
        if not image_file:
            return Response({"detail": "未上传图片文件"}, status=status.HTTP_400_BAD_REQUEST)

        if not (image_file.content_type or "").startswith("image/"):
            return Response({"detail": "仅支持图片文件"}, status=status.HTTP_400_BAD_REQUEST)

        max_size = 10 * 1024 * 1024
        if image_file.size > max_size:
            return Response({"detail": "图片大小不能超过 10MB"}, status=status.HTTP_400_BAD_REQUEST)

        ext = os.path.splitext(image_file.name)[1].lower()
        if ext not in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}:
            return Response({"detail": "不支持的图片格式"}, status=status.HTTP_400_BAD_REQUEST)

        safe_stem = slugify(os.path.splitext(image_file.name)[0]) or "image"
        safe_name = f"{safe_stem}-{uuid.uuid4().hex[:10]}{ext}"
        workspace_segment = str(novel_id)
        storage_path = (
            f"workspace_assets/user_{request.user.id}/workspace_{workspace_segment}/images/{safe_name}"
        )

        stored_path = default_storage.save(storage_path, image_file)
        return Response({"url": default_storage.url(stored_path), "path": stored_path}, status=status.HTTP_201_CREATED)
