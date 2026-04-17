from rest_framework import serializers

from .models import Chapter, Novel


class NovelSerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(source="author.username", read_only=True)

    class Meta:
        model = Novel
        fields = [
            "id",
            "title",
            "summary",
            "visibility",
            "is_deleted",
            "author",
            "author_username",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["author", "is_deleted"]


class ChapterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chapter
        fields = [
            "id",
            "novel",
            "title",
            "content_md",
            "content_html",
            "order",
            "is_published",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["content_html"]
