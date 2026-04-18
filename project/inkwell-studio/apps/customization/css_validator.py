import re
from dataclasses import dataclass

ALLOWED_STANDARD_PROPERTIES = {
    "--page-bg-color",
    "--text-font-family",
    "--link-color",
    "--paragraph-spacing",
}

SAFE_FONTS = {
    "Noto Serif SC",
    "Noto Sans SC",
    "Source Han Serif SC",
    "Source Han Sans SC",
    "FangSong",
    "KaiTi",
    "SimSun",
    "Microsoft YaHei",
    "PingFang SC",
    "Segoe UI",
}

DANGEROUS_PATTERNS = [
    re.compile(r"@import", re.IGNORECASE),
    re.compile(r"url\(", re.IGNORECASE),
    re.compile(r"expression\s*\(", re.IGNORECASE),
    re.compile(r"behavior\s*:", re.IGNORECASE),
]

FULLSCREEN_HIJACK = re.compile(
    r"position\s*:\s*fixed[^\}]*top\s*:\s*0[^\}]*left\s*:\s*0[^\}]*width\s*:\s*100vw[^\}]*height\s*:\s*100vh",
    re.IGNORECASE | re.DOTALL,
)


@dataclass
class CssValidationResult:
    is_valid: bool
    blocked_reasons: list[str]
    warning_reasons: list[str]


def validate_standard_theme_variables(theme: dict) -> CssValidationResult:
    blocked = []
    warnings = []

    unknown_keys = [key for key in theme.keys() if key not in ALLOWED_STANDARD_PROPERTIES]
    if unknown_keys:
        blocked.append(f"包含未授权变量: {', '.join(unknown_keys)}")

    font_name = theme.get("--text-font-family")
    if font_name and font_name not in SAFE_FONTS:
        blocked.append("字体不在安全白名单")

    spacing = theme.get("--paragraph-spacing")
    if spacing:
        try:
            numeric = float(str(spacing).replace("rem", "").replace("px", ""))
            if numeric < 0 or numeric > 4:
                blocked.append("段落间距超出允许范围")
        except ValueError:
            blocked.append("段落间距格式不合法")

    return CssValidationResult(is_valid=len(blocked) == 0, blocked_reasons=blocked, warning_reasons=warnings)


def validate_advanced_css(css_text: str) -> CssValidationResult:
    blocked = []
    warnings = []

    for pattern in DANGEROUS_PATTERNS:
        if pattern.search(css_text):
            blocked.append(f"命中危险模式: {pattern.pattern}")

    if FULLSCREEN_HIJACK.search(css_text):
        warnings.append("检测到可能的全屏劫持布局")

    return CssValidationResult(is_valid=len(blocked) == 0, blocked_reasons=blocked, warning_reasons=warnings)
