import re

import bleach

TOKEN_PATTERNS = {
    "highlight": re.compile(r"\{高亮\|(.+?)\}"),
    "wave": re.compile(r"\{波浪\|(.+?)\}"),
    "blur": re.compile(r"\{模糊\|(.+?)\}"),
    "ruby": re.compile(r"\{注音\|(.+?)\|(.+?)\}"),
    "scratch": re.compile(r"\{刮刮卡\|(.+?)\}"),
    "jitter": re.compile(r"\{抖动\|(.+?)\}"),
    "wobble": re.compile(r"\{晃动\|(.+?)\}"),
    "font": re.compile(r"\{字体:([^\|]+)\|(.+?)\}"),
}

ALLOWED_ADVANCED_TAGS = ["ruby", "rt", "span", "div", "i", "b", "br", "hr"]
ALLOWED_ADVANCED_ATTRS = {"*": ["class", "id", "title", "style"]}


def apply_safe_tokens(text: str) -> str:
    text = TOKEN_PATTERNS["highlight"].sub(r'<span class="mk-highlight">\1</span>', text)
    text = TOKEN_PATTERNS["wave"].sub(r'<span class="mk-wave">\1</span>', text)
    text = TOKEN_PATTERNS["blur"].sub(r'<span class="mk-blur">\1</span>', text)
    text = TOKEN_PATTERNS["ruby"].sub(r"<ruby>\1<rt>\2</rt></ruby>", text)
    text = TOKEN_PATTERNS["scratch"].sub(r'<span class="mk-scratch">\1</span>', text)
    text = TOKEN_PATTERNS["jitter"].sub(r'<span class="mk-jitter">\1</span>', text)
    text = TOKEN_PATTERNS["wobble"].sub(r'<span class="mk-wobble">\1</span>', text)
    text = TOKEN_PATTERNS["font"].sub(r'<span class="mk-custom-font" style="font-family: \'\1\', sans-serif;">\2</span>', text)
    return text


def sanitize_standard_content(text: str) -> str:
    html = apply_safe_tokens(bleach.clean(text, tags=[], attributes={}, strip=True))
    return html.replace("\n", "<br>")


def sanitize_advanced_content(text: str) -> str:
    html = apply_safe_tokens(text)
    return bleach.clean(html, tags=ALLOWED_ADVANCED_TAGS, attributes=ALLOWED_ADVANCED_ATTRS, strip=True)
