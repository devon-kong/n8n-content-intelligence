"""Normalization for skip compare: title / time / url / account — NOT markdown."""

from __future__ import annotations

from typing import Any

from article_catch.util.feishu_fields import as_link, as_text


def norm_text(v: Any) -> str:
    return as_text(v).replace("\r\n", "\n").strip()


def norm_url(v: Any) -> str:
    return as_link(v).strip()


def norm_time(v: Any) -> str:
    raw = as_text(v)
    if raw == "":
        return ""
    try:
        n = float(raw)
        if n == n:  # not NaN
            return str(int(n) if n == int(n) else n)
    except (TypeError, ValueError):
        pass
    from article_catch.util.article import parse_date

    d = parse_date(raw)
    if d is not None:
        return str(int(d.timestamp() * 1000))
    return raw.strip()


def norm_title(s: str) -> str:
    return norm_text(s)


def norm_account(s: str) -> str:
    return norm_text(s)


def norm_published(s: str) -> str:
    return norm_time(s)


def skip_fingerprint(title: Any, published_at: Any, url: Any, account: Any) -> tuple[str, str, str, str]:
    """Fields used for skip equality. Markdown must never be included."""
    return (
        norm_text(title),
        norm_time(published_at),
        norm_url(url),
        norm_text(account),
    )
