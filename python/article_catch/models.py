"""Typed intermediate models passed between stages."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class Account:
    biz_id: str
    name: str = ""
    pipeline_key: str = ""
    feed_json_url: str = ""
    account_index: int = 0
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class Article:
    article_id: str
    title: str = ""
    markdown: str = ""
    published_at: str = ""
    url: str = ""
    account: str = ""
    biz_id: str = ""
    publish_time_ms: int | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineConfig:
    pipeline_key: str
    enabled: bool = True
    summary_enabled: bool = False
    metric_enabled: bool = False
    process_mode: str = ""  # benchmark | news_digest
    target_base: str = ""
    target_table: str = ""
    window_days: int = 7
    summary_prompt: str = ""
    summary_version: str = ""
    model: str = ""


UpsertAction = Literal["create", "update", "skip"]


@dataclass
class UpsertDecision:
    action: UpsertAction
    article: Article
    record_id: str | None = None
    changed_fields: list[str] = field(default_factory=list)
    feishu_fields: dict[str, Any] = field(default_factory=dict)


@dataclass
class CatchReport:
    account_count: int = 0
    article_count: int = 0
    created: int = 0
    updated: int = 0
    skipped: int = 0
    failed_accounts: list[dict[str, Any]] = field(default_factory=list)
    visibility_ok: bool | None = None
    generated_at: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "account_count": self.account_count,
            "article_count": self.article_count,
            "created": self.created,
            "updated": self.updated,
            "skipped": self.skipped,
            "failed_accounts": self.failed_accounts,
            "visibility_ok": self.visibility_ok,
            "generated_at": self.generated_at,
        }


@dataclass
class SummaryReport:
    pending: int = 0
    summarized: int = 0
    skipped_cached: int = 0
    skipped_lock: int = 0
    failed: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "pending": self.pending,
            "summarized": self.summarized,
            "skipped_cached": self.skipped_cached,
            "skipped_lock": self.skipped_lock,
            "failed": self.failed,
        }


@dataclass
class MetricReport:
    pending: int = 0
    fetched: int = 0
    from_cache: int = 0
    skipped_lock: int = 0
    failed: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "pending": self.pending,
            "fetched": self.fetched,
            "from_cache": self.from_cache,
            "skipped_lock": self.skipped_lock,
            "failed": self.failed,
        }


@dataclass
class FlowReport:
    pipeline_key: str
    catch: CatchReport | None = None
    summary: SummaryReport | None = None
    metric: MetricReport | None = None
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "pipeline_key": self.pipeline_key,
            "catch": self.catch.as_dict() if self.catch else None,
            "summary": self.summary.as_dict() if self.summary else None,
            "metric": self.metric.as_dict() if self.metric else None,
            "error": self.error,
        }
