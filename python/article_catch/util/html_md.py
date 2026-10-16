"""HTML → markdown / cleanup. Ported from wechat-catch-better Normalize And Filter Articles."""

from __future__ import annotations

import re

_NOISE_KEYWORDS = [
    "阅读原文",
    "点击蓝字",
    "长按识别二维码",
    "扫码关注",
    "关注公众号",
    "关注我们",
    "点赞",
    "在看",
    "喜欢",
    "分享",
    "转载",
    "版权声明",
    "商务合作",
    "广告",
    "跳转微信",
    "原创声明",
    "禁止二改",
    "禁止抄袭",
    "禁止洗稿",
]


def decode_html(t: str | None) -> str:
    if not t or not isinstance(t, str):
        return ""
    s = t
    s = s.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    s = s.replace("&quot;", '"').replace("&#39;", "'")

    def _hex(m: re.Match[str]) -> str:
        return chr(int(m.group(1), 16))

    def _dec(m: re.Match[str]) -> str:
        return chr(int(m.group(1), 10))

    s = re.sub(r"&#x([0-9a-f]+);", _hex, s, flags=re.I)
    s = re.sub(r"&#(\d+);", _dec, s)
    return s


def strip_html(t: str | None) -> str:
    return re.sub(r"\s+", " ", decode_html(re.sub(r"<[^>]+>", "", str(t or "")))).strip()


def clean_markdown(md: str | None) -> str:
    if not md or not isinstance(md, str):
        return ""
    md = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", md)
    md = re.sub(r"\[([^\]]*)\]\([^)]+\)", lambda m: m.group(1).strip(), md)

    def keep_line(line: str) -> bool:
        if not line:
            return True
        if re.match(r"^https?://\S+$", line):
            return False
        if re.match(r"^//\S+$", line):
            return False
        if re.match(r"^[\-_*—=~·•●○▲▼▸►◆□■/\\|！☆★♥♦#@%&\s]{3,}$", line):
            return False
        plain = re.sub(r"[*_~`#>]", "", line).strip()
        if len(plain) <= 30 and any(k in line for k in _NOISE_KEYWORDS):
            return False
        return True

    lines = [ln.strip() for ln in md.split("\n")]
    lines = [ln for ln in lines if keep_line(ln)]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def html_to_markdown(html: str | None) -> str:
    if not html or not isinstance(html, str):
        return ""
    t = html
    for pat in (
        r"<script[\s\S]*?</script>",
        r"<style[\s\S]*?</style>",
        r"<svg[\s\S]*?</svg>",
        r"<video[\s\S]*?</video>",
        r"<audio[\s\S]*?</audio>",
        r"<iframe[\s\S]*?</iframe>",
        r"<canvas[\s\S]*?</canvas>",
    ):
        t = re.sub(pat, "", t, flags=re.I)
    t = re.sub(r"<img[^>]*>", "", t, flags=re.I)

    def _a(m: re.Match[str]) -> str:
        text = re.sub(r"<[^>]+>", "", m.group(1)).strip()
        return text or ""

    t = re.sub(r"<a[^>]*>([\s\S]*?)</a>", _a, t, flags=re.I)
    t = re.sub(r"<br\s*/?>", "\n", t, flags=re.I)
    t = re.sub(r"<h1[^>]*>([\s\S]*?)</h1>", r"\n# \1\n", t, flags=re.I)
    t = re.sub(r"<h2[^>]*>([\s\S]*?)</h2>", r"\n## \1\n", t, flags=re.I)
    t = re.sub(r"<h3[^>]*>([\s\S]*?)</h3>", r"\n### \1\n", t, flags=re.I)
    t = re.sub(r"<h4[^>]*>([\s\S]*?)</h4>", r"\n#### \1\n", t, flags=re.I)
    t = re.sub(r"<p[^>]*>([\s\S]*?)</p>", r"\n\1\n", t, flags=re.I)
    t = re.sub(r"<li[^>]*>([\s\S]*?)</li>", r"\n- \1", t, flags=re.I)
    t = re.sub(r"<blockquote[^>]*>([\s\S]*?)</blockquote>", r"\n> \1\n", t, flags=re.I)
    t = re.sub(r"<(strong|b)[^>]*>([\s\S]*?)</\1>", r"**\2**", t, flags=re.I)
    t = re.sub(r"<(em|i)[^>]*>([\s\S]*?)</\1>", r"*\2*", t, flags=re.I)
    t = re.sub(r"<code[^>]*>([\s\S]*?)</code>", r"`\1`", t, flags=re.I)
    t = re.sub(r"<[^>]+>", "", t)
    return clean_markdown(decode_html(t))
