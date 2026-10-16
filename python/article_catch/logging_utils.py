"""Structured-ish logging for Hermes-friendly stdout."""

from __future__ import annotations

import logging
import sys

from article_catch.config import get_settings


def setup_logging(level: str | None = None) -> None:
    lvl = (level or get_settings().log_level or "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, lvl, logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        stream=sys.stdout,
        force=True,
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
