"""Post-upsert visibility check (N8N Verify Count)."""

from __future__ import annotations

from typing import Any

from article_catch.clients.feishu import FeishuClient
from article_catch.util.feishu_fields import as_text

CHUNK_SIZE = 50


def verify_visibility(
    client: FeishuClient,
    *,
    target_base: str,
    target_table: str,
    article_ids: list[str],
) -> dict[str, Any]:
    expected = sorted({str(x).strip() for x in article_ids if str(x).strip()})
    if not expected:
        raise RuntimeError("Verify Count：无法获取期望的 article_ids")

    found_map: dict[str, dict[str, Any]] = {}
    for i in range(0, len(expected), CHUNK_SIZE):
        chunk = expected[i : i + CHUNK_SIZE]
        filt = {
            "conjunction": "or",
            "conditions": [
                {"field_name": "article_id", "operator": "is", "value": [aid]} for aid in chunk
            ],
        }
        data = client.search_records(
            target_base,
            target_table,
            filter=filt,
            field_names=["article_id", "markdown", "地址"],
            page_size=100,
        )
        for rec in (data.get("data") or {}).get("items") or []:
            fields = rec.get("fields") or {}
            aid = as_text(fields.get("article_id"))
            if aid:
                found_map[aid] = fields

    missing: list[str] = []
    no_markdown: list[str] = []
    no_url: list[str] = []
    for aid in expected:
        f = found_map.get(aid)
        if not f:
            missing.append(aid)
            continue
        if not as_text(f.get("markdown") or f.get("摘要")):
            no_markdown.append(aid)
        if not as_text(f.get("地址") or f.get("url")):
            no_url.append(aid)

    errors: list[str] = []
    if missing:
        errors.append("未在飞书找到：" + ", ".join(missing))
    if no_markdown:
        errors.append("markdown 为空：" + ", ".join(no_markdown))
    if no_url:
        errors.append("地址为空：" + ", ".join(no_url))
    if errors:
        raise RuntimeError("飞书可见性检查失败 | " + " | ".join(errors))

    return {
        "visibility_check": "passed",
        "found": len(found_map),
        "expected": len(expected),
        "article_ids": expected,
    }
