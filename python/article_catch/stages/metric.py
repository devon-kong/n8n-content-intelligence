"""Metric stage — N8N wechat-metric equivalent.

process_mode / metric_enabled are decided by flows/, not here.
"""

from __future__ import annotations

import random
import time

from article_catch.clients.feishu import FeishuClient
from article_catch.clients.jizhile import JizhileClient
from article_catch.config import Settings, get_settings
from article_catch.logging_utils import get_logger
from article_catch.models import MetricReport
from article_catch.ops.pending_scan import METRIC_FILTER, parse_metric_pending, scan_pending
from article_catch.store.sqlite_log import SqliteLog

log = get_logger(__name__)


def _metrics_fields(m: dict) -> dict:
    return {
        "阅读": m.get("read_count", 0),
        "点赞": m.get("like_count", 0),
        "在看": m.get("wow_count", 0),
        "转发": m.get("share_count", 0),
        "收藏": m.get("collect_count", 0),
        "评论数": m.get("comment_count", 0),
        "metric_status": "data_fetched",
    }


def run_metric(
    target_base: str,
    target_table: str,
    *,
    settings: Settings | None = None,
    feishu: FeishuClient | None = None,
    jizhile: JizhileClient | None = None,
    store: SqliteLog | None = None,
) -> MetricReport:
    settings = settings or get_settings()
    owns_feishu = feishu is None
    owns_j = jizhile is None
    feishu = feishu or FeishuClient(settings.feishu_app_id, settings.feishu_app_secret)
    jizhile = jizhile or JizhileClient(settings.jizhile_base_url, settings.jizhile_token)
    store = store or SqliteLog(settings.sqlite_path)
    store.init_schema()

    report = MetricReport()
    try:
        records = scan_pending(
            feishu,
            target_base=target_base,
            target_table=target_table,
            filter=METRIC_FILTER,
            field_names=["article_id", "地址", "metric_status", "发布时间"],
            page_size=500,
        )
        pending = parse_metric_pending(records)
        report.pending = len(pending)

        for item in pending:
            article_id = item["article_id"]
            record_id = item["record_id"]
            url = item["url"]

            cached = store.metrics_get_fresh_success(article_id)
            if cached:
                feishu.update_record(target_base, target_table, record_id, _metrics_fields(cached))
                store.metrics_mark_synced(article_id)
                report.from_cache += 1
                report.fetched += 1
                continue

            now = int(time.time() * 1000)
            run_id = f"s3-{now}-{random.randbytes(3).hex()}"
            lock = store.metrics_acquire_lock(
                article_id=article_id,
                run_id=run_id,
                record_id=record_id,
                url=url,
            )
            if lock in ("RECENT_SUCCESS", "ALREADY_PROCESSING", "LOCK_EXPIRED_REVIEW", "UNCERTAIN_REVIEW"):
                # RECENT_SUCCESS raced — try cache write once more
                if lock == "RECENT_SUCCESS":
                    cached2 = store.metrics_get_fresh_success(article_id)
                    if cached2:
                        feishu.update_record(target_base, target_table, record_id, _metrics_fields(cached2))
                        store.metrics_mark_synced(article_id)
                        report.from_cache += 1
                        report.fetched += 1
                        continue
                report.skipped_lock += 1
                continue
            if lock != "CLAIMED":
                report.skipped_lock += 1
                continue

            try:
                m = jizhile.fetch_metrics(url)
                if m.get("status") == "success":
                    metrics = {
                        "read_count": m["read_count"],
                        "like_count": m["like_count"],
                        "wow_count": m["wow_count"],
                        "share_count": m["share_count"],
                        "collect_count": m["collect_count"],
                        "comment_count": m["comment_count"],
                    }
                    store.metrics_mark_success(article_id, run_id, metrics)
                    feishu.update_record(target_base, target_table, record_id, _metrics_fields(metrics))
                    store.metrics_mark_synced(article_id)
                    report.fetched += 1
                else:
                    store.metrics_mark_non_success(
                        article_id,
                        run_id,
                        m.get("status") or "uncertain",
                        m.get("error_code"),
                        m.get("error_msg"),
                    )
                    report.failed += 1
            except Exception as e:
                store.metrics_mark_non_success(article_id, run_id, "uncertain", "ERROR", str(e)[:500])
                report.failed += 1
                log.warning("metric fail article_id=%s: %s", article_id, e)

        log.info("metric done %s", report.as_dict())
        return report
    finally:
        if owns_feishu:
            feishu.close()
        if owns_j:
            jizhile.close()
