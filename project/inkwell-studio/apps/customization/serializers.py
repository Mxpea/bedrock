from rest_framework import serializers

from .css_validator import validate_advanced_css, validate_standard_theme_variables
from .models import AdvancedStyleGrant, AuthorHomepageConfig, CSSSecurityEvent, CustomCSSRequest, ThemeConfig, CustomFont


class CustomFontSerializer(serializers.ModelSerializer):
    font_url = serializers.SerializerMethodField()

    class Meta:
        model = CustomFont
        fields = ["id", "name", "font_file", "font_url", "is_public"]
        read_only_fields = ["id", "font_url"]

    def get_font_url(self, obj):
        request = self.context.get('request')
        if obj.font_file and hasattr(obj.font_file, 'url'):
            if request:
                return request.build_absolute_uri(obj.font_file.url)
            return obj.font_file.url
        return None

    def create(self, validated_data):
        request = self.context.get("request")
        validated_data["uploader"] = request.user
        return super().create(validated_data)


class ThemeConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = ThemeConfig
        fields = [
            "id",
            "novel",
            "page_bg_color",
            "text_font_family",
            "link_color",
            "paragraph_spacing",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        variables = {
            "--page-bg-color": attrs.get("page_bg_color", self.instance.page_bg_color if self.instance else ""),
            "--text-font-family": attrs.get(
                "text_font_family", self.instance.text_font_family if self.instance else ""
            ),
            "--link-color": attrs.get("link_color", self.instance.link_color if self.instance else ""),
            "--paragraph-spacing": attrs.get(
                "paragraph_spacing", self.instance.paragraph_spacing if self.instance else ""
            ),
        }
        result = validate_standard_theme_variables(variables)
        if not result.is_valid:
            raise serializers.ValidationError({"theme": result.blocked_reasons})
        return attrs

    def validate_novel(self, novel):
        request = self.context["request"]
        if novel.author != request.user:
            raise serializers.ValidationError("只能配置自己的作品")
        return novel


class CustomCSSRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomCSSRequest
        fields = [
            "id",
            "applicant",
            "novel",
            "reason",
            "css_snippet",
            "status",
            "review_note",
            "reviewed_by",
            "reviewed_at",
            "risk_acknowledged",
            "blocked_reasons",
            "warning_reasons",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "applicant",
            "status",
            "review_note",
            "reviewed_by",
            "reviewed_at",
            "blocked_reasons",
            "warning_reasons",
        ]

    def validate_novel(self, novel):
        request = self.context["request"]
        if novel and novel.author != request.user:
            raise serializers.ValidationError("不能为他人作品申请高级样式")
        return novel

    def validate_css_snippet(self, value):
        result = validate_advanced_css(value)
        if not result.is_valid:
            raise serializers.ValidationError(result.blocked_reasons)
        return value


class CSSRequestReviewSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[CustomCSSRequest.Status.APPROVED, CustomCSSRequest.Status.REJECTED])
    review_note = serializers.CharField(required=False, allow_blank=True)


class AdvancedStyleGrantSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdvancedStyleGrant
        fields = [
            "id",
            "user",
            "novel",
            "scope",
            "enabled",
            "granted_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["granted_by"]


class AuthorHomepageConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthorHomepageConfig
        fields = [
            "id",
            "author",
            "template_choice",
            "header_image_url",
            "avatar_url",
            "custom_html",
            "custom_css",
            "use_custom_page",
            "sandbox_mode",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["author", "sandbox_mode"]

    def validate_use_custom_page(self, value):
        if not value:
            return value

        user = self.context["request"].user
        has_grant = AdvancedStyleGrant.objects.filter(
            user=user,
            enabled=True,
            scope=AdvancedStyleGrant.Scope.ACCOUNT,
        ).exists()
        if not has_grant:
            raise serializers.ValidationError("仅认证高阶作者可启用完全自定义主页")
        return value

    def validate_custom_css(self, value):
        if not value:
            return value

        result = validate_advanced_css(value)
        if not result.is_valid:
            raise serializers.ValidationError(result.blocked_reasons)
        return value


class CSSSecurityEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = CSSSecurityEvent
        fields = [
            "id",
            "novel",
            "triggered_by",
            "severity",
            "reason",
            "matched_css_fragment",
            "auto_rollback_applied",
            "created_at",
        ]
