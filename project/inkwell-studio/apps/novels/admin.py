from django.contrib import admin

from .models import Chapter, Novel, Character


@admin.register(Novel)
class NovelAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "author",
        "visibility",
        "last_open_module",
        "last_open_chapter_id",
        "is_deleted",
        "created_at",
    )
    search_fields = ("title", "author__username")
    list_filter = ("visibility", "is_deleted")


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "novel", "order", "is_published", "created_at")
    search_fields = ("title", "novel__title")
    list_filter = ("is_published",)


@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "novel", "is_starred", "is_pinned", "sort_order", "updated_at")
    search_fields = ("name", "summary", "novel__title")
    list_filter = ("is_starred", "is_pinned")
