from rest_framework import serializers

from .models import Chapter, Novel


class NovelSerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(source="author.username", read_only=True)
    workspace_name = serializers.CharField(source="title", read_only=True)
    visibility_label = serializers.CharField(source="get_visibility_display", read_only=True)
    module_label = serializers.CharField(source="get_last_open_module_display", read_only=True)
    icon_url = serializers.SerializerMethodField()

    def get_icon_url(self, obj):
        if not obj.icon:
            return ""
        request = self.context.get("request")
        url = obj.icon.url
        return request.build_absolute_uri(url) if request else url

    class Meta:
        model = Novel
        fields = [
            "id",
            "title",
            "summary",
            "icon",
            "icon_url",
            "is_locked",
            "visibility",
            "last_open_module",
            "last_open_chapter_id",
            "is_deleted",
            "author",
            "author_username",
            "workspace_name",
            "visibility_label",
            "module_label",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["author", "is_deleted", "icon_url", "is_locked"]


class ChapterSerializer(serializers.ModelSerializer):
    workspace_name = serializers.CharField(source="novel.title", read_only=True)

    class Meta:
        model = Chapter
        fields = [
            "id",
            "novel",
            "workspace_name",
            "title",
            "content_md",
            "content_html",
            "order",
            "is_published",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["content_html"]
