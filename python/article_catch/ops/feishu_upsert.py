"""Decide create/update/skip and apply single-record upserts."""

from __future__ import annotations

from typing import Any, Iterable

from article_catch.clients.feishu import FeishuClient
from article_catch.models import Article, UpsertDecision
from article_catch.util.feishu_fields import make_url_field
from article_catch.util.text_norm import norm_text, norm_time, norm_url

CATCH_FIELD_WHITELIST = ("标题", "markdown", "发布时间", "地址", "账号", "article_id")
EXISTING_FIELD_NAMES = ["article_id", "标题", "发布时间", "地址", "账号"]
CHUNK_SIZE = 50


def article_to_catch_fields(article: Article) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    if article.title:
        fields["标题"] = article.title
    if article.markdown:
        fields["markdown"] = article.markdown
    if article.publish_time_ms is not None:
        fields["发布时间"] = article.publish_time_ms
    elif article.published_at:
        from article_catch.util.article import parse_date

        d = parse_date(article.published_at)
        if d is not None:
            fields["发布时间"] = int(d.timestamp() * 1000)
    if article.url:
        fields["地址"] = make_url_field(article.url, article.title or article.url)
    if article.account:
        fields["账号"] = str(article.account)
    if article.article_id:
        fields["article_id"] = str(article.article_id)
    extra = set(fields) - set(CATCH_FIELD_WHITELIST)
    if extra:
        raise ValueError(f"catch fields not allowed: {extra}")
    return fields


def build_existing_map(
    client: FeishuClient,
    *,
    target_base: str,
    target_table: str,
    article_ids: list[str],
) -> dict[str, dict[str, Any]]:
    if not article_ids:
        return {}
    existing: dict[str, dict[str, Any]] = {}
    for i in range(0, len(article_ids), CHUNK_SIZE):
        chunk = article_ids[i : i + CHUNK_SIZE]
        filt = {
            "conjunction": "or",
            "conditions": [
                {"field_name": "article_id", "operator": "is", "value": [str(aid)]} for aid in chunk
            ],
        }
        data = client.search_records(
            target_base,
            target_table,
            filter=filt,
            field_names=EXISTING_FIELD_NAMES,
            page_size=100,
        )
        records = (data.get("data") or {}).get("items") or []
        for rec in records:
            fields = rec.get("fields") or {}
            aid = norm_text(fields.get("article_id"))
            if not aid:
                continue
            existing[aid] = {
                "record_id": rec.get("record_id") or rec.get("id") or "",
                "fields": fields,
            }
    return existing


def decide_actions(
    articles: Iterable[Article],
    existing_map: dict[str, dict[str, Any]],
) -> list[UpsertDecision]:
    out: list[UpsertDecision] = []
    for article in articles:
        fields = article_to_catch_fields(article)
        aid = article.article_id
        ex = existing_map.get(aid)
        if not ex:
            out.append(
                UpsertDecision(
                    action="create",
                    article=article,
                    feishu_fields=fields,
                    changed_fields=["__new_record__"],
                )
            )
            continue
        ef = ex.get("fields") or {}
        changed: list[str] = []
        if norm_text(ef.get("标题")) != norm_text(fields.get("标题")):
            changed.append("标题")
        if norm_time(ef.get("发布时间")) != norm_time(fields.get("发布时间")):
            changed.append("发布时间")
        if norm_url(ef.get("地址")) != norm_url(fields.get("地址")):
            changed.append("地址")
        if norm_text(ef.get("账号")) != norm_text(fields.get("账号")):
            changed.append("账号")
        rid = ex.get("record_id") or ""
        if changed:
            if not rid:
                raise RuntimeError(f"已存在记录缺少 record_id，无法 update：article_id={aid}")
            out.append(
                UpsertDecision(
                    action="update",
                    article=article,
                    record_id=rid,
                    feishu_fields=fields,
                    changed_fields=changed,
                )
            )
        else:
            out.append(
                UpsertDecision(
                    action="skip",
                    article=article,
                    record_id=rid,
                    feishu_fields=fields,
                    changed_fields=[],
                )
            )
    return out


def apply_upserts(
    client: FeishuClient,
    *,
    target_base: str,
    target_table: str,
    decisions: list[UpsertDecision],
) -> dict[str, int]:
    created = updated = skipped = 0
    for d in decisions:
        if d.action == "skip":
            skipped += 1
            continue
        if d.action == "create":
            client.create_record(target_base, target_table, d.feishu_fields)
            created += 1
        elif d.action == "update":
            assert d.record_id
            client.update_record(target_base, target_table, d.record_id, d.feishu_fields)
            updated += 1
        else:
            raise ValueError(f"unknown action {d.action}")
    return {"created": created, "updated": updated, "skipped": skipped}
