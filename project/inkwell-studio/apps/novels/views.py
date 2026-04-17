from rest_framework import permissions, viewsets
from rest_framework.exceptions import PermissionDenied
from django.db.models import Q

from .models import Chapter, Novel
from .permissions import CanReadNovel, IsAuthorOrReadOnly
from .serializers import ChapterSerializer, NovelSerializer


class NovelViewSet(viewsets.ModelViewSet):
    serializer_class = NovelSerializer
    permission_classes = [permissions.IsAuthenticated, IsAuthorOrReadOnly, CanReadNovel]
    filterset_fields = ["visibility"]
    search_fields = ["title", "summary"]
    ordering_fields = ["created_at", "updated_at", "title"]

    def get_queryset(self):
        user = self.request.user
        return Novel.objects.filter(is_deleted=False).filter(
            Q(author=user) | Q(visibility__in=[Novel.Visibility.PUBLIC, Novel.Visibility.LINK])
        )

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
        serializer.save()
