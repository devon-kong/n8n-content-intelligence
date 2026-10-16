"""SQLite call-log aligned with N8N summary_call_log / metrics_call_log."""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any


SCHEMA = """
CREATE TABLE IF NOT EXISTS summary_call_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id TEXT NOT NULL,
    task_key TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('processing','success','failed','uncertain','skipped')),
    provider TEXT NOT NULL DEFAULT 'deepseek',
    model TEXT,
    prompt_version TEXT,
    run_id TEXT,
    feishu_record_id TEXT,
    request_hash TEXT,
    result_json TEXT,
    error_code TEXT,
    error_msg TEXT,
    started_at INTEGER NOT NULL,
    finished_at INTEGER,
    lock_until INTEGER NOT NULL,
    synced_to_feishu INTEGER NOT NULL DEFAULT 0
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_summary_success_once ON summary_call_log(task_key) WHERE status = 'success';
CREATE UNIQUE INDEX IF NOT EXISTS ux_summary_processing_once ON summary_call_log(task_key) WHERE status = 'processing';
CREATE INDEX IF NOT EXISTS idx_summary_article ON summary_call_log(article_id, status);

CREATE TABLE IF NOT EXISTS metrics_call_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('processing','success','failed','uncertain','skipped')),
    provider TEXT NOT NULL DEFAULT 'jizhile',
    run_id TEXT,
    feishu_record_id TEXT,
    url TEXT NOT NULL,
    request_hash TEXT,
    result_json TEXT,
    read_count INTEGER,
    like_count INTEGER,
    wow_count INTEGER,
    share_count INTEGER,
    collect_count INTEGER,
    comment_count INTEGER,
    error_code TEXT,
    error_msg TEXT,
    started_at INTEGER NOT NULL,
    finished_at INTEGER,
    lock_until INTEGER NOT NULL,
    synced_to_feishu INTEGER NOT NULL DEFAULT 0
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_metrics_processing_once ON metrics_call_log(article_id) WHERE status = 'processing';
CREATE INDEX IF NOT EXISTS idx_metrics_article_status_time ON metrics_call_log(article_id, status, started_at);
CREATE INDEX IF NOT EXISTS idx_metrics_sync ON metrics_call_log(status, synced_to_feishu);
"""


class SqliteLog:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init = False

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.path), timeout=30)
        conn.row_factory = sqlite3.Row
        return conn

    def init_schema(self) -> None:
        if self._init:
            return
        with self._connect() as conn:
            conn.executescript(SCHEMA)
            conn.commit()
        self._init = True

    # --- summary ---
    def summary_get_success(self, task_key: str) -> dict[str, Any] | None:
        self.init_schema()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, result_json FROM summary_call_log WHERE task_key=? AND status='success' LIMIT 1",
                (task_key,),
            ).fetchone()
        if not row:
            return None
        try:
            payload = json.loads(row["result_json"] or "{}")
        except json.JSONDecodeError:
            payload = {}
        return {"id": row["id"], "result": payload}

    def summary_acquire_lock(
        self,
        *,
        task_key: str,
        article_id: str,
        run_id: str,
        record_id: str,
        model: str,
        prompt_version: str,
        lock_ttl_ms: int = 30 * 60 * 1000,
    ) -> str:
        """Return CLAIMED | ALREADY_SUCCESS | ALREADY_PROCESSING | LOCK_EXPIRED_REVIEW"""
        self.init_schema()
        now = int(time.time() * 1000)
        lock_until = now + lock_ttl_ms
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                sr = conn.execute(
                    "SELECT id FROM summary_call_log WHERE task_key=? AND status='success' LIMIT 1",
                    (task_key,),
                ).fetchone()
                if sr:
                    conn.commit()
                    return "ALREADY_SUCCESS"
                pr = conn.execute(
                    "SELECT id, lock_until as lu FROM summary_call_log WHERE task_key=? AND status='processing' LIMIT 1",
                    (task_key,),
                ).fetchone()
                if pr:
                    if pr["lu"] > now:
                        conn.commit()
                        return "ALREADY_PROCESSING"
                    conn.execute(
                        "UPDATE summary_call_log SET status='uncertain' WHERE id=?",
                        (pr["id"],),
                    )
                    conn.commit()
                    return "LOCK_EXPIRED_REVIEW"
                try:
                    conn.execute(
                        """INSERT INTO summary_call_log
                        (article_id,task_key,status,provider,model,prompt_version,run_id,feishu_record_id,started_at,lock_until,synced_to_feishu)
                        VALUES (?,?, 'processing','deepseek',?,?,?,?,?,?,0)""",
                        (article_id, task_key, model, prompt_version, run_id, record_id, now, lock_until),
                    )
                except sqlite3.IntegrityError:
                    conn.commit()
                    return "ALREADY_PROCESSING"
                conn.commit()
                return "CLAIMED"
            except Exception:
                conn.rollback()
                raise

    def summary_mark_success(self, task_key: str, run_id: str, summary: str) -> None:
        self.init_schema()
        finished = int(time.time() * 1000)
        result_json = json.dumps({"summary": summary}, ensure_ascii=False)
        with self._connect() as conn:
            cur = conn.execute(
                """UPDATE summary_call_log SET status='success', result_json=?, finished_at=?
                   WHERE task_key=? AND status='processing' AND run_id=?""",
                (result_json, finished, task_key, run_id),
            )
            if cur.rowcount != 1:
                existing = conn.execute(
                    "SELECT id FROM summary_call_log WHERE task_key=? AND status='success' LIMIT 1",
                    (task_key,),
                ).fetchone()
                if not existing:
                    raise RuntimeError(
                        f"SQLite success update failed changes={cur.rowcount} task_key={task_key}"
                    )
            conn.commit()

    def summary_mark_non_success(
        self, task_key: str, run_id: str, status: str, error_code: str | None, error_msg: str | None
    ) -> None:
        self.init_schema()
        finished = int(time.time() * 1000)
        with self._connect() as conn:
            conn.execute(
                """UPDATE summary_call_log SET status=?, error_code=?, error_msg=?, finished_at=?
                   WHERE task_key=? AND status='processing' AND run_id=?""",
                (status, error_code, error_msg, finished, task_key, run_id),
            )
            conn.commit()

    def summary_mark_synced(self, task_key: str) -> None:
        self.init_schema()
        with self._connect() as conn:
            conn.execute(
                "UPDATE summary_call_log SET synced_to_feishu=1 WHERE task_key=? AND status='success'",
                (task_key,),
            )
            conn.commit()

    # --- metrics ---
    def metrics_get_fresh_success(self, article_id: str, *, max_age_ms: int = 24 * 3600 * 1000) -> dict[str, Any] | None:
        self.init_schema()
        since = int(time.time() * 1000) - max_age_ms
        with self._connect() as conn:
            row = conn.execute(
                """SELECT result_json, read_count, like_count, wow_count, share_count, collect_count, comment_count, finished_at
                   FROM metrics_call_log WHERE article_id=? AND status='success' AND finished_at>=?
                   ORDER BY finished_at DESC LIMIT 1""",
                (article_id, since),
            ).fetchone()
        if not row:
            return None
        try:
            payload = json.loads(row["result_json"] or "{}")
        except json.JSONDecodeError:
            payload = {}
        return {
            "read_count": row["read_count"] if row["read_count"] is not None else payload.get("read_count", 0),
            "like_count": row["like_count"] if row["like_count"] is not None else payload.get("like_count", 0),
            "wow_count": row["wow_count"] if row["wow_count"] is not None else payload.get("wow_count", 0),
            "share_count": row["share_count"] if row["share_count"] is not None else payload.get("share_count", 0),
            "collect_count": row["collect_count"] if row["collect_count"] is not None else payload.get("collect_count", 0),
            "comment_count": row["comment_count"] if row["comment_count"] is not None else payload.get("comment_count", 0),
            "result": payload,
        }

    def metrics_acquire_lock(
        self,
        *,
        article_id: str,
        run_id: str,
        record_id: str,
        url: str,
        lock_ttl_ms: int = 30 * 60 * 1000,
    ) -> str:
        self.init_schema()
        now = int(time.time() * 1000)
        lock_until = now + lock_ttl_ms
        since = now - 24 * 3600 * 1000
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                sr = conn.execute(
                    """SELECT id FROM metrics_call_log WHERE article_id=? AND status='success' AND finished_at>=?
                       ORDER BY finished_at DESC LIMIT 1""",
                    (article_id, since),
                ).fetchone()
                if sr:
                    conn.commit()
                    return "RECENT_SUCCESS"
                pr = conn.execute(
                    "SELECT id, lock_until as lu FROM metrics_call_log WHERE article_id=? AND status='processing' LIMIT 1",
                    (article_id,),
                ).fetchone()
                if pr:
                    if pr["lu"] > now:
                        conn.commit()
                        return "ALREADY_PROCESSING"
                    conn.execute("UPDATE metrics_call_log SET status='uncertain' WHERE id=?", (pr["id"],))
                    conn.commit()
                    return "LOCK_EXPIRED_REVIEW"
                try:
                    conn.execute(
                        """INSERT INTO metrics_call_log
                        (article_id,status,provider,run_id,feishu_record_id,url,started_at,lock_until,synced_to_feishu)
                        VALUES (?,'processing','jizhile',?,?,?,?,?,0)""",
                        (article_id, run_id, record_id, url, now, lock_until),
                    )
                except sqlite3.IntegrityError:
                    conn.commit()
                    return "ALREADY_PROCESSING"
                conn.commit()
                return "CLAIMED"
            except Exception:
                conn.rollback()
                raise

    def metrics_mark_success(self, article_id: str, run_id: str, metrics: dict[str, Any]) -> None:
        self.init_schema()
        finished = int(time.time() * 1000)
        result_json = json.dumps(metrics, ensure_ascii=False)
        with self._connect() as conn:
            cur = conn.execute(
                """UPDATE metrics_call_log SET status='success', result_json=?,
                   read_count=?, like_count=?, wow_count=?, share_count=?, collect_count=?, comment_count=?, finished_at=?
                   WHERE article_id=? AND status='processing' AND run_id=?""",
                (
                    result_json,
                    metrics.get("read_count", 0),
                    metrics.get("like_count", 0),
                    metrics.get("wow_count", 0),
                    metrics.get("share_count", 0),
                    metrics.get("collect_count", 0),
                    metrics.get("comment_count", 0),
                    finished,
                    article_id,
                    run_id,
                ),
            )
            if cur.rowcount != 1:
                existing = conn.execute(
                    "SELECT id FROM metrics_call_log WHERE article_id=? AND status='success' AND run_id=? LIMIT 1",
                    (article_id, run_id),
                ).fetchone()
                if not existing:
                    raise RuntimeError(f"metrics success update failed article_id={article_id}")
            conn.commit()

    def metrics_mark_non_success(
        self, article_id: str, run_id: str, status: str, error_code: str | None, error_msg: str | None
    ) -> None:
        self.init_schema()
        finished = int(time.time() * 1000)
        with self._connect() as conn:
            conn.execute(
                """UPDATE metrics_call_log SET status=?, error_code=?, error_msg=?, finished_at=?
                   WHERE article_id=? AND status='processing' AND run_id=?""",
                (status, error_code, error_msg, finished, article_id, run_id),
            )
            conn.commit()

    def metrics_mark_synced(self, article_id: str) -> None:
        self.init_schema()
        with self._connect() as conn:
            conn.execute(
                "UPDATE metrics_call_log SET synced_to_feishu=1 WHERE article_id=? AND status='success'",
                (article_id,),
            )
            conn.commit()
