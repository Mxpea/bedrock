import os
import uuid
import re
from io import BytesIO

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils.text import slugify
from django.utils.html import strip_tags
from PIL import Image, ImageOps
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.db.models import Max

from apps.customization.markdown_extensions import sanitize_advanced_content, sanitize_standard_content
from apps.customization.models import AdvancedStyleGrant
from .models import Chapter, Novel, Character, WorldviewEntry, WorldviewLink
from .permissions import CanReadNovel, IsAuthorOrReadOnly
from .serializers import ChapterSerializer, NovelSerializer, CharacterSerializer, WorldviewEntrySerializer


class NovelViewSet(viewsets.ModelViewSet):
    serializer_class = NovelSerializer
    lookup_field = "public_id"
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

    def get_object(self):
        lookup_value = self.kwargs.get(self.lookup_url_kwarg or self.lookup_field)
        queryset = self.filter_queryset(self.get_queryset())
        return get_object_or_404(queryset, Q(public_id=lookup_value) | Q(id=lookup_value))

    def perform_update(self, serializer):
        instance = self.get_object()
        user = self.request.user
        is_admin = user.is_superuser or user.is_staff or getattr(user, "role", "") == "admin"
        if instance.is_locked and instance.author == user and not is_admin:
            raise PermissionDenied("工作区已被锁定，暂不可修改")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.author != self.request.user:
            raise PermissionDenied("只有作者可以删除作品")
        instance.is_deleted = True
        instance.save(update_fields=["is_deleted", "updated_at"])

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[permissions.IsAuthenticated],
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_icon(self, request, pk=None):
        workspace = self.get_queryset().filter(Q(public_id=pk) | Q(id=pk), author=request.user).first()
        if not workspace:
            return Response({"detail": "工作区不存在或无权访问"}, status=status.HTTP_404_NOT_FOUND)

        is_admin = request.user.is_superuser or request.user.is_staff or getattr(request.user, "role", "") == "admin"
        if workspace.is_locked and workspace.author == request.user and not is_admin:
            return Response({"detail": "工作区已被锁定，暂不可修改图标"}, status=status.HTTP_403_FORBIDDEN)

        icon_file = request.FILES.get("icon")
        if not icon_file:
            return Response({"detail": "未上传图标文件"}, status=status.HTTP_400_BAD_REQUEST)

        if not (icon_file.content_type or "").startswith("image/"):
            return Response({"detail": "仅支持图片文件"}, status=status.HTTP_400_BAD_REQUEST)

        max_size = 10 * 1024 * 1024
        if icon_file.size > max_size:
            return Response({"detail": "图标大小不能超过 10MB"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            image = Image.open(icon_file)
            image = ImageOps.exif_transpose(image)
            image = image.convert("RGBA")
            icon_256 = ImageOps.fit(image, (256, 256), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))

            output = BytesIO()
            icon_256.save(output, format="PNG", optimize=True)
            output.seek(0)
        except Exception:
            return Response({"detail": "图片处理失败，请上传有效图像"}, status=status.HTTP_400_BAD_REQUEST)

        workspace_segment = workspace.public_id or str(pk or workspace.pk)
        icon_name = f"workspace-icons/user_{request.user.id}/workspace_{workspace_segment}/icon-{uuid.uuid4().hex[:10]}.png"

        if workspace.icon:
            workspace.icon.delete(save=False)

        workspace.icon.save(icon_name, ContentFile(output.read()), save=True)

        serializer = self.get_serializer(workspace)
        return Response({"icon_url": serializer.data.get("icon_url", "")}, status=status.HTTP_200_OK)


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
        if novel.is_locked:
            raise PermissionDenied("工作区已被锁定，暂不可新增章节")
        if "order" not in serializer.initial_data:
            next_order = (Chapter.objects.filter(novel=novel).aggregate(max_order=Max("order"))["max_order"] or 0) + 1
            chapter = serializer.save(order=next_order)
        else:
            chapter = serializer.save()
        novel.last_open_module = Novel.Module.WRITING
        novel.last_open_chapter_id = chapter.id
        novel.save(update_fields=["last_open_module", "last_open_chapter_id", "updated_at"])

    def perform_update(self, serializer):
        chapter_instance = self.get_object()
        if chapter_instance.novel.is_locked:
            raise PermissionDenied("工作区已被锁定，暂不可编辑章节")
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
            novel = Novel.objects.filter(Q(public_id=novel_id) | Q(id=novel_id), author=request.user, is_deleted=False).first()
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

        novel = Novel.objects.filter(Q(public_id=novel_id) | Q(id=novel_id), author=request.user, is_deleted=False).first()
        if not novel:
            return Response({"detail": "工作区不存在或无权访问"}, status=status.HTTP_404_NOT_FOUND)
        if novel.is_locked:
            return Response({"detail": "工作区已被锁定，暂不可上传素材"}, status=status.HTTP_403_FORBIDDEN)

        image_file = request.FILES.get("image")
        if not image_file:
            return Response({"detail": "未上传图片文件"}, status=status.HTTP_400_BAD_REQUEST)

        if not (image_file.content_type or "").startswith("image/"):
            return Response({"detail": "仅支持图片文件"}, status=status.HTTP_400_BAD_REQUEST)

        max_size = 10 * 1024 * 1024
        if image_file.size > max_size:
            return Response({"detail": "图片大小不能超过 10MB"}, status=status.HTTP_400_BAD_REQUEST)

        ext = os.path.splitext(image_file.name)[1].lower()
        if ext not in {".png", ".jpg", ".jpeg", ".gif", ".webp"}:
            return Response({"detail": "不支持的图片格式"}, status=status.HTTP_400_BAD_REQUEST)

        safe_stem = slugify(os.path.splitext(image_file.name)[0]) or "image"
        safe_name = f"{safe_stem}-{uuid.uuid4().hex[:10]}{ext}"
        workspace_segment = novel.public_id or str(novel_id)
        storage_path = (
            f"workspace_assets/user_{request.user.id}/workspace_{workspace_segment}/images/{safe_name}"
        )

        stored_path = default_storage.save(storage_path, image_file)
        return Response({"url": default_storage.url(stored_path), "path": stored_path}, status=status.HTTP_201_CREATED)


class CharacterViewSet(viewsets.ModelViewSet):
    serializer_class = CharacterSerializer
    permission_classes = [permissions.IsAuthenticated]
    ordering_fields = ["sort_order", "created_at", "updated_at", "name"]

    def get_queryset(self):
        queryset = Character.objects.select_related("novel").filter(
            novel__author=self.request.user,
            novel__is_deleted=False,
        )

        novel_id = self.request.GET.get("novel")
        if novel_id:
            queryset = queryset.filter(Q(novel_id=novel_id) | Q(novel__public_id=novel_id))

        keyword = (self.request.GET.get("q") or "").strip()
        if keyword:
            queryset = queryset.filter(
                Q(name__icontains=keyword)
                | Q(summary__icontains=keyword)
                | Q(description__icontains=keyword)
                | Q(notes__icontains=keyword)
            )

        tag = (self.request.GET.get("tag") or "").strip()
        if tag:
            queryset = queryset.filter(tags__contains=[tag])

        starred = (self.request.GET.get("starred") or "").strip().lower()
        if starred in {"1", "true", "yes"}:
            queryset = queryset.filter(is_starred=True)

        ALLOWED_ORDERINGS = {
            "sort_order", "-sort_order",
            "created_at", "-created_at",
            "updated_at", "-updated_at",
            "name", "-name",
        }
        ordering = (self.request.GET.get("ordering") or "").strip()
        if ordering and ordering in ALLOWED_ORDERINGS:
            return queryset.order_by(ordering)

        return queryset.order_by("-is_pinned", "sort_order", "id")

    def perform_create(self, serializer):
        novel = serializer.validated_data["novel"]
        if novel.is_locked:
            raise PermissionDenied("工作区已被锁定，暂不可新建人物")
        serializer.save()

    def perform_update(self, serializer):
        instance = self.get_object()
        if instance.novel.is_locked:
            raise PermissionDenied("工作区已被锁定，暂不可编辑人物")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.novel.is_locked:
            raise PermissionDenied("工作区已被锁定，暂不可删除人物")
        instance.delete()

    @action(detail=False, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def reorder(self, request):
        ids = request.data.get("ids")
        if not isinstance(ids, list):
            return Response({"detail": "ids 必须为数组"}, status=status.HTTP_400_BAD_REQUEST)

        from django.utils import timezone as tz

        items = list(self.get_queryset().filter(id__in=ids))
        mapping = {item.pk: item for item in items}

        now = tz.now()
        update_items = []
        for idx, raw_id in enumerate(ids):
            try:
                key = int(raw_id)
            except (TypeError, ValueError):
                continue
            obj = mapping.get(key)
            if not obj:
                continue
            obj.sort_order = idx
            obj.updated_at = now
            update_items.append(obj)

        if update_items:
            Character.objects.bulk_update(update_items, ["sort_order", "updated_at"])

        return Response({"ok": True}, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[permissions.IsAuthenticated],
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_avatar(self, request, pk=None):
        character = self.get_object()
        if character.novel.is_locked:
            return Response({"detail": "工作区已被锁定，暂不可修改头像"}, status=status.HTTP_403_FORBIDDEN)

        avatar_file = request.FILES.get("avatar")
        if not avatar_file:
            return Response({"detail": "未上传头像文件"}, status=status.HTTP_400_BAD_REQUEST)

        if not (avatar_file.content_type or "").startswith("image/"):
            return Response({"detail": "仅支持图片文件"}, status=status.HTTP_400_BAD_REQUEST)

        max_size = 10 * 1024 * 1024
        if avatar_file.size > max_size:
            return Response({"detail": "头像大小不能超过 10MB"}, status=status.HTTP_400_BAD_REQUEST)

        if character.avatar:
            character.avatar.delete(save=False)

        ext = os.path.splitext(avatar_file.name or "")[1].lower()
        if ext not in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
            ext = ".png"

        avatar_name = (
            f"character-avatars/user_{request.user.id}/workspace_{character.novel.public_id or character.novel_id}/"
            f"character_{character.id}_{uuid.uuid4().hex[:10]}{ext}"
        )

        character.avatar.save(
            avatar_name,
            avatar_file,
            save=True,
        )

        serializer = self.get_serializer(character)
        return Response({"avatar_url": serializer.data.get("avatar_url", "")}, status=status.HTTP_200_OK)


class WorldviewEntryViewSet(viewsets.ModelViewSet):
    serializer_class = WorldviewEntrySerializer
    permission_classes = [permissions.IsAuthenticated]
    ordering_fields = ["name", "created_at", "updated_at"]

    def get_queryset(self):
        queryset = WorldviewEntry.objects.select_related("novel").filter(
            novel__author=self.request.user,
            novel__is_deleted=False,
        )

        novel_id = (self.request.GET.get("novel") or "").strip()
        if novel_id:
            queryset = queryset.filter(Q(novel_id=novel_id) | Q(novel__public_id=novel_id))

        keyword = (self.request.GET.get("q") or "").strip()
        if keyword:
            queryset = queryset.filter(
                Q(name__icontains=keyword)
                | Q(content_md__icontains=keyword)
                | Q(plain_content__icontains=keyword)
                | Q(aliases__icontains=keyword)
            )

        category = (self.request.GET.get("category") or "").strip()
        if category:
            queryset = queryset.filter(category=category)

        folder = (self.request.GET.get("folder") or "").strip().strip("/")
        if folder:
            queryset = queryset.filter(Q(folder_path=folder) | Q(folder_path__startswith=folder + "/"))

        tags = [item.strip() for item in (self.request.GET.get("tags") or "").split(",") if item.strip()]
        for tag in tags:
            queryset = queryset.filter(tags__contains=[tag])

        return queryset.order_by("name", "id")

    def perform_create(self, serializer):
        novel = serializer.validated_data["novel"]
        if novel.is_locked:
            raise PermissionDenied("工作区已被锁定，暂不可新建世界观词条")
        instance = serializer.save()
        self._refresh_entry_fields(instance)
        self._refresh_links(instance)

    def perform_update(self, serializer):
        instance = self.get_object()
        if instance.novel.is_locked:
            raise PermissionDenied("工作区已被锁定，暂不可编辑世界观词条")
        instance = serializer.save()
        self._refresh_entry_fields(instance)
        self._refresh_links(instance)

    def perform_destroy(self, instance):
        if instance.novel.is_locked:
            raise PermissionDenied("工作区已被锁定，暂不可删除世界观词条")
        WorldviewLink.objects.filter(Q(source=instance) | Q(target=instance)).delete()
        instance.delete()

    @action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def facets(self, request):
        queryset = self.get_queryset()

        category_counts = {}
        for item in queryset.values("category"):
            name = (item.get("category") or "未分类").strip() or "未分类"
            category_counts[name] = category_counts.get(name, 0) + 1

        tag_counts = {}
        for item in queryset.values("tags"):
            for tag in (item.get("tags") or []):
                text = str(tag).strip()
                if text:
                    tag_counts[text] = tag_counts.get(text, 0) + 1

        return Response(
            {
                "categories": [{"name": name, "count": count} for name, count in sorted(category_counts.items())],
                "tags": [{"name": name, "count": count} for name, count in sorted(tag_counts.items())],
            },
            status=status.HTTP_200_OK,
        )

    def _refresh_entry_fields(self, entry):
        html = sanitize_standard_content(entry.content_md or "")
        plain = strip_tags(html)
        WorldviewEntry.objects.filter(pk=entry.pk).update(content_html=html, plain_content=plain)
        entry.content_html = html
        entry.plain_content = plain

    def _refresh_links(self, entry):
        pattern = re.compile(r"\[\[([^\]]+)\]\]")
        text = entry.content_md or ""
        names = [name.strip() for name in pattern.findall(text) if name.strip()]

        WorldviewLink.objects.filter(source=entry).delete()

        if not names:
            return

        targets = {
            item.name: item
            for item in WorldviewEntry.objects.filter(
                novel_id=entry.novel_id,
                name__in=list(set(names)),
            ).exclude(pk=entry.pk)
        }

        created = []
        for match in pattern.finditer(text):
            raw_name = match.group(1).strip()
            target = targets.get(raw_name)
            if not target:
                continue
            start = max(match.start() - 24, 0)
            end = min(match.end() + 24, len(text))
            context = text[start:end].replace("\n", " ").strip()
            created.append(
                WorldviewLink(
                    novel_id=entry.novel_id,
                    source_id=entry.id,
                    target_id=target.id,
                    context=context[:255],
                )
            )

        if created:
            dedup = {}
            for item in created:
                dedup[(item.source_id, item.target_id)] = item
            WorldviewLink.objects.bulk_create(list(dedup.values()), ignore_conflicts=True)
