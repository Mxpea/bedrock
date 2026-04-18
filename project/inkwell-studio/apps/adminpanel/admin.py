from django.contrib import admin

from .models import ContentReport, PlatformSetting, RoastMessage, RoastReply


@admin.register(PlatformSetting)
class PlatformSettingAdmin(admin.ModelAdmin):
    list_display = ("registration_mode", "advanced_css_review_mode", "require_public_review", "updated_at")


@admin.register(ContentReport)
class ContentReportAdmin(admin.ModelAdmin):
    list_display = ("id", "target_type", "reporter", "status", "workspace", "created_at")
    list_filter = ("target_type", "status")
    search_fields = ("reason", "workspace__title", "reporter__username")


@admin.register(RoastMessage)
class RoastMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "workspace", "author", "visibility", "status", "created_at")
    list_filter = ("visibility", "status")
    search_fields = ("content", "workspace__title", "author__username")


@admin.register(RoastReply)
class RoastReplyAdmin(admin.ModelAdmin):
    list_display = ("id", "roast", "author", "created_at")
    search_fields = ("content", "author__username")
