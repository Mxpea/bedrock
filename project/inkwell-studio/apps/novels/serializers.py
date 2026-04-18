from rest_framework import serializers

from .models import Chapter, Novel, Character


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
            "outline_canvas",
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


class CharacterSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = Character
        fields = [
            "id",
            "novel",
            "name",
            "aliases",
            "avatar",
            "avatar_url",
            "role_title",
            "gender",
            "age_label",
            "tags",
            "summary",
            "description",
            "notes",
            "relationships",
            "chapter_mentions",
            "is_starred",
            "is_pinned",
            "sort_order",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["chapter_mentions", "avatar_url"]

    def get_avatar_url(self, obj):
        if not obj.avatar:
            return ""
        request = self.context.get("request")
        url = obj.avatar.url
        return request.build_absolute_uri(url) if request else url

    def to_representation(self, instance):
        data = super().to_representation(instance)
        mentions = instance.compute_chapter_mentions()
        data["chapter_mentions"] = mentions
        data["mention_chapters"] = mentions
        data["appearances_count"] = len(mentions)
        return data

    def validate_novel(self, novel):
        request = self.context.get("request")
        if not request or novel.author != request.user:
            raise serializers.ValidationError("只能操作自己的工作区人物")
        return novel

    def validate_aliases(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("别名必须为数组")
        return [str(item).strip() for item in value if str(item).strip()]

    def validate_tags(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("标签必须为数组")
        tags = []
        for item in value:
            text = str(item).strip()
            if text and text not in tags:
                tags.append(text)
        return tags

    def validate_relationships(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("关系数据必须为数组")
        return value

    def create(self, validated_data):
        instance = super().create(validated_data)
        mentions = instance.compute_chapter_mentions()
        instance.chapter_mentions = mentions
        instance.save(update_fields=["chapter_mentions", "updated_at"])
        return instance

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        mentions = instance.compute_chapter_mentions()
        instance.chapter_mentions = mentions
        instance.save(update_fields=["chapter_mentions", "updated_at"])
        return instance
