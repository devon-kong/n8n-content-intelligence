"""CLI entry — parse args only; business lives in flows/stages."""

from __future__ import annotations

import argparse
import json
import sys


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="article_catch",
        description="WeChat2RSS central kitchen (catch → summary → metric) CLI",
    )
    sub = p.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Full central-kitchen flow for one or more pipelines")
    run_p.add_argument(
        "--pipeline",
        required=True,
        help="pipeline_key or comma-separated keys, e.g. industry_news,ai_news",
    )

    catch_p = sub.add_parser("catch", help="Run catch stage only")
    catch_p.add_argument("--pipeline", required=True)

    sum_p = sub.add_parser("summary", help="Run summary stage only")
    sum_p.add_argument("--target-base", required=True)
    sum_p.add_argument("--target-table", required=True)
    sum_p.add_argument("--model", required=True)
    sum_p.add_argument("--prompt-version", required=True, dest="summary_version")
    sum_p.add_argument("--prompt", required=True, dest="summary_prompt")

    met_p = sub.add_parser("metric", help="Run metric stage only")
    met_p.add_argument("--target-base", required=True)
    met_p.add_argument("--target-table", required=True)

    cfg_p = sub.add_parser("config-show", help="Read pipeline config (no writes)")
    cfg_p.add_argument("--pipeline", required=True)

    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.command == "run":
        from article_catch.flows.central_kitchen import run_pipelines

        keys = [k.strip() for k in args.pipeline.split(",") if k.strip()]
        return run_pipelines(keys)

    if args.command == "catch":
        from article_catch.flows.central_kitchen import run_catch_only

        return run_catch_only(args.pipeline)

    if args.command == "summary":
        from article_catch.logging_utils import setup_logging
        from article_catch.stages.summary import run_summary

        setup_logging()
        try:
            report = run_summary(
                target_base=args.target_base,
                target_table=args.target_table,
                summary_prompt=args.summary_prompt,
                summary_version=args.summary_version,
                model=args.model,
            )
            print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))
            return 0
        except Exception as e:
            print(str(e), file=sys.stderr)
            return 1

    if args.command == "metric":
        from article_catch.logging_utils import setup_logging
        from article_catch.stages.metric import run_metric

        setup_logging()
        try:
            report = run_metric(target_base=args.target_base, target_table=args.target_table)
            print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))
            return 0
        except Exception as e:
            print(str(e), file=sys.stderr)
            return 1

    if args.command == "config-show":
        from article_catch.flows.central_kitchen import show_config

        return show_config(args.pipeline)

    print(f"unknown command: {args.command}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
