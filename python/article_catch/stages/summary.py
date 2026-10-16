"""Summary stage — merged news summary + benchmark summary."""

from __future__ import annotations

import random
import time
from typing import Any

from article_catch.clients.feishu import FeishuClient
from article_catch.clients.llm import LlmClient, LlmError
from article_catch.config import Settings, get_settings
from article_catch.logging_utils import get_logger
from article_catch.models import SummaryReport
from article_catch.ops.pending_scan import SUMMARY_FILTER, parse_summary_pending, scan_pending
from article_catch.store.sqlite_log import SqliteLog

log = get_logger(__name__)


def run_summary(
    target_base: str,
    target_table: str,
    summary_prompt: str,
    summary_version: str,
    model: str,
    *,
    settings: Settings | None = None,
    feishu: FeishuClient | None = None,
    llm: LlmClient | None = None,
    store: SqliteLog | None = None,
) -> SummaryReport:
    settings = settings or get_settings()
    owns_feishu = feishu is None
    owns_llm = llm is None
    feishu = feishu or FeishuClient(settings.feishu_app_id, settings.feishu_app_secret)
    llm = llm or LlmClient(settings.llm_api_key, settings.llm_base_url)
    store = store or SqliteLog(settings.sqlite_path)
    store.init_schema()

    report = SummaryReport()
    try:
        records = scan_pending(
            feishu,
            target_base=target_base,
            target_table=target_table,
            filter=SUMMARY_FILTER,
            field_names=["article_id", "markdown", "摘要"],
            page_size=500,
        )
        pending = parse_summary_pending(records)
        report.pending = len(pending)
        if not summary_prompt.strip():
            raise RuntimeError("summary_prompt 为空")

        for item in pending:
            article_id = item["article_id"]
            record_id = item["record_id"]
            markdown = item["markdown"]
            task_key = f"{summary_version}:{model}:{article_id}"
            now = int(time.time() * 1000)
            run_id = f"s2-{now}-{random.randbytes(3).hex()}"

            cached = store.summary_get_success(task_key)
            if cached and str((cached.get("result") or {}).get("summary") or "").strip():
                summary_text = str(cached["result"]["summary"]).strip()
                feishu.update_record(
                    target_base,
                    target_table,
                    record_id,
                    {"摘要": summary_text, "summary_status": "summarized"},
                )
                store.summary_mark_synced(task_key)
                report.skipped_cached += 1
                report.summarized += 1
                continue

            lock = store.summary_acquire_lock(
                task_key=task_key,
                article_id=article_id,
                run_id=run_id,
                record_id=record_id,
                model=model,
                prompt_version=summary_version,
            )
            if lock in ("ALREADY_SUCCESS", "ALREADY_PROCESSING", "LOCK_EXPIRED_REVIEW"):
                report.skipped_lock += 1
                continue
            if lock != "CLAIMED":
                report.skipped_lock += 1
                continue

            try:
                prompt = summary_prompt + "\n\n" + markdown
                summary_text = llm.chat(model, [{"role": "user", "content": prompt}])
                store.summary_mark_success(task_key, run_id, summary_text)
                feishu.update_record(
                    target_base,
                    target_table,
                    record_id,
                    {"摘要": summary_text, "summary_status": "summarized"},
                )
                store.summary_mark_synced(task_key)
                report.summarized += 1
            except LlmError as e:
                status = "failed" if (e.status and 400 <= e.status < 500) else "uncertain"
                store.summary_mark_non_success(task_key, run_id, status, str(e.status or "API_ERROR"), str(e)[:500])
                report.failed += 1
                log.warning("summary llm fail article_id=%s: %s", article_id, e)
            except Exception as e:
                store.summary_mark_non_success(task_key, run_id, "uncertain", "ERROR", str(e)[:500])
                report.failed += 1
                log.warning("summary fail article_id=%s: %s", article_id, e)

        log.info("summary done %s", report.as_dict())
        return report
    finally:
        if owns_feishu:
            feishu.close()
        if owns_llm:
            llm.close()
