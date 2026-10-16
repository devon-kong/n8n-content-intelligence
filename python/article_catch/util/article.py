"""Feed item → Article; window filter; article_id dedupe. Ported from catch better."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from article_catch.models import Article
from article_catch.util.html_md import clean_markdown, html_to_markdown, strip_html


def _u32(n: int) -> int:
    return n & 0xFFFFFFFF


def _imul(a: int, b: int) -> int:
    """JS Math.imul equivalent (signed 32-bit multiply)."""
    a = _u32(a)
    b = _u32(b)
    # signed interpretation of product low 32 bits
    prod = (a * b) & 0xFFFFFFFF
    if prod >= 0x80000000:
        return prod - 0x100000000
    return prod


def stable_hash(s: str) -> str:
    """Port of N8N stableHash → wx_…"""
    s = str(s or "")
    # JavaScript length/charCodeAt operate on UTF-16 code units, including
    # surrogate pairs. Python's code-point iteration differs for emoji.
    encoded = s.encode("utf-16-le", errors="surrogatepass")
    units = [int.from_bytes(encoded[i:i + 2], "little") for i in range(0, len(encoded), 2)]
    h1 = 0xDEADBEEF ^ len(units)
    h2 = 0x41C6CE57 ^ len(units)
    for c in units:
        h1 = _imul(h1 ^ c, 2654435761)
        h2 = _imul(h2 ^ c, 1597334677)
    h1 = _imul(h1 ^ (_u32(h1) >> 16), 2246822507) ^ _imul(h2 ^ (_u32(h2) >> 13), 3266489909)
    h2 = _imul(h2 ^ (_u32(h2) >> 16), 2246822507) ^ _imul(h1 ^ (_u32(h1) >> 13), 3266489909)
    # JS: 4294967296*(2097151&h2)+(h1>>>0)
    part = 4294967296 * (2097151 & _u32(h2)) + _u32(h1)
    return "wx_" + _to_base36(part)


def _to_base36(n: int) -> str:
    if n == 0:
        return "0"
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    neg = n < 0
    n = abs(n)
    out: list[str] = []
    while n:
        n, r = divmod(n, 36)
        out.append(digits[r])
    s = "".join(reversed(out))
    return "-" + s if neg else s


def parse_date(v: Any) -> datetime | None:
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    if isinstance(v, (int, float)):
        ms = float(v) * 1000 if float(v) < 1e12 else float(v)
        return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc)
    r = str(v).strip()
    if re.fullmatch(r"\d+", r):
        n = float(r)
        ms = n * 1000 if n < 1e12 else n
        return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc)
    try:
        iso = r if "T" in r else r.replace(" ", "T")
        # handle trailing Z
        if iso.endswith("Z"):
            iso = iso[:-1] + "+00:00"
        d = datetime.fromisoformat(iso)
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def first_val(*vals: Any) -> Any:
    for v in vals:
        if v is None:
            continue
        if isinstance(v, str) and not v.strip():
            continue
        if v != "":
            return v
    return ""


def pick_feed_items(feed: Any) -> list[dict[str, Any]]:
    if isinstance(feed, list):
        return [x for x in feed if isinstance(x, dict)]
    if not isinstance(feed, dict):
        return []
    for k in ("items", "entries", "data"):
        v = feed.get(k)
        if isinstance(v, list):
            return [x for x in v if isinstance(x, dict)]
    data = feed.get("data")
    if isinstance(data, dict) and isinstance(data.get("items"), list):
        return [x for x in data["items"] if isinstance(x, dict)]
    return []


def normalize_feed_item(
    item: dict[str, Any],
    *,
    account_name: str = "",
    account_biz_id: str = "",
    feed_title: str = "",
) -> Article | None:
    title = strip_html(str(first_val(item.get("title"))))
    url = str(
        first_val(
            item.get("url"),
            item.get("external_url"),
            item.get("link"),
            item.get("guid"),
            item.get("id"),
        )
    ).strip()
    if not title and not url:
        return None
    published_raw = first_val(
        item.get("date_published"),
        item.get("date_modified"),
        item.get("published"),
        item.get("updated"),
        item.get("pubDate"),
        item.get("created"),
        item.get("create_time"),
    )
    published_date = parse_date(published_raw)
    content_html = str(
        first_val(
            item.get("content_html"),
            item.get("content"),
            item.get("html"),
            item.get("raw_html"),
        )
    )
    content_text = strip_html(
        str(
            first_val(
                item.get("content_text"),
                item.get("summary"),
                item.get("description"),
                item.get("desc"),
            )
        )
    )
    markdown = (
        html_to_markdown(content_html)
        if content_html
        else clean_markdown(str(content_text or "").strip())
    )
    if not markdown:
        return None
    publish_time = published_date.isoformat().replace("+00:00", "Z") if published_date else str(published_raw or "")
    biz = str(first_val(account_biz_id, item.get("biz_id"), item.get("biz"), item.get("bid")))
    name = str(first_val(account_name, item.get("biz_name"), feed_title))
    id_seed = first_val(
        url,
        item.get("guid"),
        item.get("id"),
        ":".join(x for x in ["wechat2rss", biz, publish_time, title or url] if x),
    )
    return Article(
        article_id=stable_hash(str(id_seed)),
        title=title,
        markdown=markdown,
        published_at=publish_time,
        url=url,
        account=name,
        biz_id=biz,
        publish_time_ms=int(published_date.timestamp() * 1000) if published_date else None,
        raw=item,
    )


def filter_by_window(articles: list[Article], window_days: int) -> list[Article]:
    if window_days <= 0:
        return list(articles)
    after_ms = int(datetime.now(tz=timezone.utc).timestamp() * 1000) - window_days * 24 * 60 * 60 * 1000
    out: list[Article] = []
    for a in articles:
        d = parse_date(a.published_at) if a.published_at else None
        if d is not None and int(d.timestamp() * 1000) < after_ms:
            continue
        out.append(a)
    return out


def dedupe_by_article_id(articles: list[Article]) -> list[Article]:
    seen: set[str] = set()
    out: list[Article] = []
    for a in articles:
        if not a.article_id or a.article_id in seen:
            continue
        seen.add(a.article_id)
        out.append(a)
    return out


def articles_from_feed(
    feed: Any,
    *,
    account_name: str = "",
    account_biz_id: str = "",
    window_days: int = 7,
) -> list[Article]:
    feed_title = ""
    if isinstance(feed, dict):
        feed_title = str(feed.get("title") or "")
    items = pick_feed_items(feed)
    arts: list[Article] = []
    for it in items:
        a = normalize_feed_item(
            it,
            account_name=account_name,
            account_biz_id=account_biz_id,
            feed_title=feed_title,
        )
        if a:
            arts.append(a)
    return dedupe_by_article_id(filter_by_window(arts, window_days))
