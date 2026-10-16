"""Central kitchen flow — N8N Entry shared logic."""

from __future__ import annotations

import json
import sys
from typing import Sequence

from article_catch.clients.feishu import FeishuClient
from article_catch.config import Settings, get_settings
from article_catch.logging_utils import get_logger, setup_logging
from article_catch.models import FlowReport, PipelineConfig
from article_catch.stages.catch import run_catch
from article_catch.stages.metric import run_metric
from article_catch.stages.summary import run_summary
from article_catch.util.feishu_fields import as_bool, as_text

log = get_logger(__name__)


def load_pipeline_config(
    pipeline_key: str,
    *,
    settings: Settings | None = None,
    feishu: FeishuClient | None = None,
) -> PipelineConfig:
    settings = settings or get_settings()
    owns = feishu is None
    feishu = feishu or FeishuClient(settings.feishu_app_id, settings.feishu_app_secret)
    try:
        filt = {
            "conjunction": "and",
            "conditions": [
                {"field_name": "pipeline_key", "operator": "is", "value": [pipeline_key]},
                {"field_name": "是否启用", "operator": "is", "value": [True]},
            ],
        }
        data = feishu.search_records(
            settings.feishu_config_base,
            settings.feishu_config_table,
            filter=filt,
            field_names=[
                "pipeline_key",
                "是否启用",
                "summary_enabled",
                "metric_enabled",
                "process_mode",
                "target_base",
                "target_table",
                "window_days",
                "summary_prompt",
                "summary_version",
                "model",
            ],
            page_size=20,
        )
        records = (data.get("data") or {}).get("items") or []
        if len(records) == 0:
            raise RuntimeError(f"pipeline_key={pipeline_key} 未找到启用的配置（0 条记录）")
        if len(records) > 1:
            raise RuntimeError(f"pipeline_key={pipeline_key} 配置存在多条记录（{len(records)}），应唯一")
        fields = records[0].get("fields") or {}
        cfg = PipelineConfig(
            pipeline_key=pipeline_key,
            enabled=as_bool(fields.get("是否启用", True)),
            summary_enabled=as_bool(fields.get("summary_enabled")),
            metric_enabled=as_bool(fields.get("metric_enabled")),
            process_mode=as_text(fields.get("process_mode")),
            target_base=as_text(fields.get("target_base")),
            target_table=as_text(fields.get("target_table")),
            window_days=int(as_text(fields.get("window_days")) or 7),
            summary_prompt=as_text(fields.get("summary_prompt")),
            summary_version=as_text(fields.get("summary_version")),
            model=as_text(fields.get("model")),
        )
        if not cfg.target_base:
            raise RuntimeError("target_base 为空，请检查飞书配置")
        if not cfg.target_table:
            raise RuntimeError("target_table 为空，请检查飞书配置")
        return cfg
    finally:
        if owns:
            feishu.close()


def run_one(
    pipeline_key: str,
    *,
    settings: Settings | None = None,
    feishu: FeishuClient | None = None,
) -> FlowReport:
    settings = settings or get_settings()
    report = FlowReport(pipeline_key=pipeline_key)
    try:
        cfg = load_pipeline_config(pipeline_key, settings=settings, feishu=feishu)
        log.info(
            "pipeline %s config: summary=%s metric=%s mode=%s window=%s",
            pipeline_key,
            cfg.summary_enabled,
            cfg.metric_enabled,
            cfg.process_mode,
            cfg.window_days,
        )
        report.catch = run_catch(
            cfg.pipeline_key,
            cfg.target_base,
            cfg.target_table,
            cfg.window_days,
            settings=settings,
            feishu=feishu,
        )
        if cfg.summary_enabled:
            report.summary = run_summary(
                cfg.target_base,
                cfg.target_table,
                cfg.summary_prompt,
                cfg.summary_version,
                cfg.model,
                settings=settings,
                feishu=feishu,
            )
        if cfg.summary_enabled and cfg.process_mode == "benchmark" and cfg.metric_enabled:
            report.metric = run_metric(
                cfg.target_base,
                cfg.target_table,
                settings=settings,
                feishu=feishu,
            )
        return report
    except Exception as e:
        report.error = str(e)
        log.exception("pipeline %s failed: %s", pipeline_key, e)
        return report


def run_pipelines(pipeline_keys: Sequence[str]) -> int:
    setup_logging()
    if not pipeline_keys:
        print("no pipeline keys", file=sys.stderr)
        return 2
    exit_code = 0
    settings = get_settings()
    for key in pipeline_keys:
        report = run_one(key, settings=settings)
        print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))
        if report.error:
            exit_code = 1
    return exit_code


def run_catch_only(pipeline_key: str) -> int:
    setup_logging()
    try:
        settings = get_settings()
        cfg = load_pipeline_config(pipeline_key, settings=settings)
        report = run_catch(
            cfg.pipeline_key,
            cfg.target_base,
            cfg.target_table,
            cfg.window_days,
            settings=settings,
        )
        print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))
        return 0
    except Exception as e:
        log.exception("catch-only failed: %s", e)
        print(str(e), file=sys.stderr)
        return 1


def show_config(pipeline_key: str) -> int:
    setup_logging()
    try:
        cfg = load_pipeline_config(pipeline_key)
        # do not print secrets
        print(
            json.dumps(
                {
                    "pipeline_key": cfg.pipeline_key,
                    "enabled": cfg.enabled,
                    "summary_enabled": cfg.summary_enabled,
                    "metric_enabled": cfg.metric_enabled,
                    "process_mode": cfg.process_mode,
                    "target_base": cfg.target_base,
                    "target_table": cfg.target_table,
                    "window_days": cfg.window_days,
                    "summary_version": cfg.summary_version,
                    "model": cfg.model,
                    "summary_prompt_len": len(cfg.summary_prompt or ""),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    except Exception as e:
        print(str(e), file=sys.stderr)
        return 1
