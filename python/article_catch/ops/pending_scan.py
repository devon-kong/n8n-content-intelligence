"""Scan Feishu target table for pending rows (summary / metric)."""

from __future__ import annotations

from typing import Any

from article_catch.clients.feishu import FeishuClient
from article_catch.util.feishu_fields import as_link, as_text


SUMMARY_FILTER = {
    "conjunction": "and",
    "conditions": [
        {"field_name": "摘要", "operator": "isEmpty", "value": []},
        {"field_name": "markdown", "operator": "isNotEmpty", "value": []},
    ],
}

METRIC_FILTER = {
    "conjunction": "and",
    "conditions": [
        {"field_name": "地址", "operator": "isNotEmpty", "value": []},
        {"field_name": "metric_status", "operator": "isEmpty", "value": []},
    ],
}


def scan_pending(
    client: FeishuClient,
    *,
    target_base: str,
    target_table: str,
    filter: dict[str, Any],
    field_names: list[str],
    page_size: int = 500,
) -> list[dict[str, Any]]:
    # N8N uses single page_size=500; we page if has_more to be safer
    return client.search_all(
        target_base,
        target_table,
        filter=filter,
        field_names=field_names,
        page_size=page_size,
    )


def parse_summary_pending(records: list[dict[str, Any]]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for r in records:
        fields = r.get("fields") or {}
        article_id = as_text(fields.get("article_id"))
        markdown = as_text(fields.get("markdown"))
        record_id = str(r.get("record_id") or r.get("id") or "")
        if article_id and markdown and record_id:
            out.append({"record_id": record_id, "article_id": article_id, "markdown": markdown})
    return out


def parse_metric_pending(records: list[dict[str, Any]]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for r in records:
        fields = r.get("fields") or {}
        article_id = as_text(fields.get("article_id"))
        url = as_link(fields.get("地址"))
        record_id = str(r.get("record_id") or r.get("id") or "")
        if article_id and url and record_id:
            out.append({"record_id": record_id, "article_id": article_id, "url": url})
    return out
