"""Catch stage — N8N wechat-catch-better equivalent."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

from article_catch.clients.feishu import FeishuClient
from article_catch.clients.wechat2rss import Wechat2RssClient, Wechat2RssError
from article_catch.config import Settings, get_settings
from article_catch.logging_utils import get_logger
from article_catch.models import Account, Article, CatchReport
from article_catch.ops.feishu_upsert import apply_upserts, build_existing_map, decide_actions
from article_catch.ops.visibility import verify_visibility
from article_catch.util.article import articles_from_feed
from article_catch.util.feishu_fields import as_bool, as_text

log = get_logger(__name__)


def load_accounts(
    client: FeishuClient,
    settings: Settings,
    pipeline_key: str,
) -> list[Account]:
    filt = {
        "conjunction": "and",
        "conditions": [
            {"field_name": "pipeline_key", "operator": "is", "value": [pipeline_key]},
            {"field_name": "是否启用", "operator": "is", "value": [True]},
        ],
    }
    data = client.search_records(
        settings.feishu_config_base,
        settings.feishu_list_table,
        filter=filt,
        field_names=["biz_id", "账号名称", "是否启用", "pipeline_key"],
        page_size=100,
    )
    if data.get("code") not in (0, None):
        raise RuntimeError(f"飞书公众号 List 查询失败：{data}")
    payload = data.get("data") or {}
    if payload.get("has_more"):
        raise RuntimeError(
            "公众号 List 查询结果超过 page_size=100，当前未启用分页。为避免漏账号，本次执行已中断。"
        )
    records = payload.get("items") or []
    if not records:
        raise RuntimeError(f"没有找到启用的公众号，pipeline_key={pipeline_key}")

    accounts: list[Account] = []
    base = settings.wechat2rss_base.rstrip("/")
    for i, rec in enumerate(records):
        fields = rec.get("fields") or {}
        if not as_bool(fields.get("是否启用", True)):
            continue
        biz = as_text(fields.get("biz_id"))
        if not biz:
            continue
        name = as_text(fields.get("账号名称"))
        accounts.append(
            Account(
                biz_id=biz,
                name=name,
                pipeline_key=pipeline_key,
                feed_json_url=f"{base}/feed/{quote(biz, safe='')}.json",
                account_index=i,
                raw=fields,
            )
        )
    if not accounts:
        raise RuntimeError(f"没有找到启用的公众号，pipeline_key={pipeline_key}")
    return accounts


def fetch_articles(
    w2r: Wechat2RssClient,
    accounts: list[Account],
    window_days: int,
) -> tuple[list[Article], list[dict[str, Any]]]:
    articles: list[Article] = []
    failed: list[dict[str, Any]] = []
    for acc in accounts:
        try:
            feed = w2r.fetch_feed(acc.biz_id)
            batch = articles_from_feed(
                feed,
                account_name=acc.name,
                account_biz_id=acc.biz_id,
                window_days=window_days,
            )
            articles.extend(batch)
        except (Wechat2RssError, Exception) as e:
            log.warning("feed failed biz_id=%s: %s", acc.biz_id, e)
            failed.append(
                {
                    "account_index": acc.account_index,
                    "biz_id": acc.biz_id,
                    "account_name": acc.name,
                    "feed_json_url": acc.feed_json_url,
                    "error": str(e)[:500],
                }
            )
    # dedupe across accounts
    seen: set[str] = set()
    deduped: list[Article] = []
    for a in articles:
        if a.article_id in seen:
            continue
        seen.add(a.article_id)
        deduped.append(a)
    return deduped, failed


def run_catch(
    pipeline_key: str,
    target_base: str,
    target_table: str,
    window_days: int,
    *,
    settings: Settings | None = None,
    feishu: FeishuClient | None = None,
    w2r: Wechat2RssClient | None = None,
    skip_visibility: bool = False,
) -> CatchReport:
    settings = settings or get_settings()
    owns_feishu = feishu is None
    owns_w2r = w2r is None
    feishu = feishu or FeishuClient(settings.feishu_app_id, settings.feishu_app_secret)
    w2r = w2r or Wechat2RssClient(settings.wechat2rss_base, settings.wechat2rss_token)
    try:
        accounts = load_accounts(feishu, settings, pipeline_key)
        articles, failed = fetch_articles(w2r, accounts, int(window_days) or 7)
        if not articles:
            report = CatchReport(
                account_count=len(accounts),
                article_count=0,
                failed_accounts=failed,
                visibility_ok=True if not articles else None,
                generated_at=datetime.now(tz=timezone.utc).isoformat(),
            )
            log.info("catch empty articles pipeline=%s accounts=%s failed=%s", pipeline_key, len(accounts), len(failed))
            return report

        existing = build_existing_map(
            feishu,
            target_base=target_base,
            target_table=target_table,
            article_ids=[a.article_id for a in articles],
        )
        decisions = decide_actions(articles, existing)
        counts = apply_upserts(
            feishu,
            target_base=target_base,
            target_table=target_table,
            decisions=decisions,
        )
        vis_ok = None
        if not skip_visibility:
            verify_visibility(
                feishu,
                target_base=target_base,
                target_table=target_table,
                article_ids=[a.article_id for a in articles],
            )
            vis_ok = True

        report = CatchReport(
            account_count=len(accounts),
            article_count=len(articles),
            created=counts["created"],
            updated=counts["updated"],
            skipped=counts["skipped"],
            failed_accounts=failed,
            visibility_ok=vis_ok,
            generated_at=datetime.now(tz=timezone.utc).isoformat(),
        )
        log.info("catch done %s", report.as_dict())
        return report
    finally:
        if owns_feishu:
            feishu.close()
        if owns_w2r:
            w2r.close()
