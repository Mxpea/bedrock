from django.contrib import admin

from .models import AdvancedStyleGrant, AuthorHomepageConfig, CSSSecurityEvent, CustomCSSRequest, ThemeConfig


@admin.register(ThemeConfig)
class ThemeConfigAdmin(admin.ModelAdmin):
    list_display = ("id", "novel", "text_font_family", "updated_at")
    search_fields = ("novel__title", "novel__author__username")


@admin.register(CustomCSSRequest)
class CustomCSSRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "applicant", "novel", "status", "created_at", "reviewed_at")
    list_filter = ("status",)
    search_fields = ("applicant__username", "novel__title")


@admin.register(AdvancedStyleGrant)
class AdvancedStyleGrantAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "novel", "scope", "enabled", "granted_by", "updated_at")
    list_filter = ("scope", "enabled")
    search_fields = ("user__username", "novel__title")


@admin.register(CSSSecurityEvent)
class CSSSecurityEventAdmin(admin.ModelAdmin):
    list_display = ("id", "novel", "severity", "reason", "auto_rollback_applied", "created_at")
    list_filter = ("severity", "auto_rollback_applied")


@admin.register(AuthorHomepageConfig)
class AuthorHomepageConfigAdmin(admin.ModelAdmin):
    list_display = ("id", "author", "template_choice", "use_custom_page", "updated_at")
    list_filter = ("template_choice", "use_custom_page")
