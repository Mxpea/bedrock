import re

import bleach
import markdown

TOKEN_PATTERNS = {
    "highlight": re.compile(r"\{高亮\|(.+?)\}"),
    "wave": re.compile(r"\{波浪\|(.+?)\}"),
    "blur": re.compile(r"\{模糊\|(.+?)\}"),
    # Support both half-width/full-width separators and shorthand forms:
    # {注音|汉字|かな}, {注音|汉字|}, {注音|汉字}
    "ruby": re.compile(r"[\{｛]注音[\|｜]([\s\S]+?)(?:[\|｜]([\s\S]*?))?[\}｝]"),
    "scratch": re.compile(r"\{刮刮卡\|(.+?)\}"),
    "jitter": re.compile(r"\{抖动\|(.+?)\}"),
    "wobble": re.compile(r"\{晃动\|(.+?)\}"),
    "font": re.compile(r"\{字体:([^\|]+)\|(.+?)\}"),
    "align_left": re.compile(r"\{左对齐\|([\s\S]+?)\}"),
    "align_center": re.compile(r"\{居中\|([\s\S]+?)\}"),
    "align_right": re.compile(r"\{右对齐\|([\s\S]+?)\}"),
}

ALLOWED_ADVANCED_TAGS = ["ruby", "rt", "span", "div", "i", "b", "br", "hr"]
ALLOWED_ADVANCED_ATTRS = {"*": ["class", "id", "title", "data-font"]}

ALLOWED_MARKDOWN_TAGS = [
    "a",
    "p",
    "br",
    "hr",
    "blockquote",
    "code",
    "pre",
    "strong",
    "em",
    "ul",
    "ol",
    "li",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "img",
    "ruby",
    "rt",
    "span",
    "div",
    "i",
    "b",
]
ALLOWED_MARKDOWN_ATTRS = {
    "a": ["href", "title", "target", "rel"],
    "img": ["src", "alt", "title"],
    "*": ["class", "id", "title", "data-font"],
}

ALLOWED_PROTOCOLS = ["http", "https", "mailto", "data"]


def _replace_font_token(match: re.Match) -> str:
    # Keep only common font name characters to prevent attribute injection.
    raw_font = match.group(1).strip()
    font_name = re.sub(r"[^\w\s\-\u4e00-\u9fff]", "", raw_font)
    if not font_name:
        font_name = "sans-serif"
    content = match.group(2)
    return f'<span class="mk-custom-font" data-font="{font_name}">{content}</span>'


def _replace_ruby_token(match: re.Match) -> str:
    base_text = (match.group(1) or "").strip()
    ruby_text = (match.group(2) or "").strip()
    if not base_text:
        return ""
    if ruby_text:
        return f"<ruby>{base_text}<rt>{ruby_text}</rt></ruby>"
    return f"<ruby>{base_text}</ruby>"


def apply_safe_tokens(text: str) -> str:
    text = TOKEN_PATTERNS["highlight"].sub(r'<span class="mk-highlight">\1</span>', text)
    text = TOKEN_PATTERNS["wave"].sub(r'<span class="mk-wave">\1</span>', text)
    text = TOKEN_PATTERNS["blur"].sub(r'<span class="mk-blur">\1</span>', text)
    text = TOKEN_PATTERNS["ruby"].sub(_replace_ruby_token, text)
    text = TOKEN_PATTERNS["scratch"].sub(r'<span class="mk-scratch">\1</span>', text)
    text = TOKEN_PATTERNS["jitter"].sub(r'<span class="mk-jitter">\1</span>', text)
    text = TOKEN_PATTERNS["wobble"].sub(r'<span class="mk-wobble">\1</span>', text)
    text = TOKEN_PATTERNS["font"].sub(_replace_font_token, text)
    text = TOKEN_PATTERNS["align_left"].sub(r'<div class="mk-align-left">\1</div>', text)
    text = TOKEN_PATTERNS["align_center"].sub(r'<div class="mk-align-center">\1</div>', text)
    text = TOKEN_PATTERNS["align_right"].sub(r'<div class="mk-align-right">\1</div>', text)
    return text


def _render_markdown(text: str) -> str:
    return markdown.markdown(
        text,
        extensions=["extra", "sane_lists", "nl2br"],
        output_format="html5",
    )


def sanitize_standard_content(text: str) -> str:
    source = bleach.clean(text, tags=[], attributes={}, strip=True)
    source = apply_safe_tokens(source)
    html = _render_markdown(source)
    return bleach.clean(
        html,
        tags=ALLOWED_MARKDOWN_TAGS,
        attributes=ALLOWED_MARKDOWN_ATTRS,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )


def sanitize_advanced_content(text: str) -> str:
    source = apply_safe_tokens(text)
    html = _render_markdown(source)
    advanced_attrs = dict(ALLOWED_MARKDOWN_ATTRS)
    advanced_attrs["*"] = sorted(set(ALLOWED_MARKDOWN_ATTRS.get("*", []) + ALLOWED_ADVANCED_ATTRS.get("*", [])))
    return bleach.clean(
        html,
        tags=list(set(ALLOWED_MARKDOWN_TAGS + ALLOWED_ADVANCED_TAGS)),
        attributes=advanced_attrs,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )
