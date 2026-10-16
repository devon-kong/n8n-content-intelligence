"""Jizhile (dajiala) engagement metrics API."""

from __future__ import annotations

import re
from typing import Any

import httpx


class JizhileError(RuntimeError):
    def __init__(self, message: str, *, code: Any = None, status: str = "uncertain") -> None:
        super().__init__(message)
        self.code = code
        self.status = status  # success | failed | uncertain


def to_number(value: Any) -> int:
    if value is None or value == "":
        return 0
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return int(value) if value == value else 0
    s = str(value).strip().replace(",", "")
    if re.search(r"万\+?$", s):
        base = re.sub(r"万\+?$", "", s)
        try:
            return int(round(float(base) * 10000))
        except ValueError:
            return 0
    if s.endswith("+"):
        s = s[:-1]
    try:
        return int(float(s))
    except ValueError:
        return 0


class JizhileClient:
    DEFAULT_URL = "https://www.dajiala.com/fbmain/monitor/v3/read_zan_pro"

    def __init__(
        self,
        base_url: str = "",
        token: str = "",
        *,
        timeout: float = 60.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = (base_url or self.DEFAULT_URL).rstrip("/")
        self.token = token
        self._owns = client is None
        self._client = client or httpx.Client(timeout=timeout)

    def close(self) -> None:
        if self._owns:
            self._client.close()

    def fetch_metrics(self, article_url: str) -> dict[str, Any]:
        payload = {"url": article_url, "verifycode": self.token or ""}
        r = self._client.post(
            self.base_url,
            headers={"Content-Type": "application/json; charset=utf-8"},
            json=payload,
        )
        try:
            data = r.json()
        except Exception as e:
            raise JizhileError(f"invalid JSON: {e}", status="uncertain") from e

        if data.get("code") == 0:
            d = data.get("data") or {}
            return {
                "status": "success",
                "read_count": to_number(d.get("read")),
                "like_count": to_number(d.get("zan")),
                "wow_count": to_number(d.get("looking")),
                "share_count": to_number(d.get("share_num")),
                "collect_count": to_number(d.get("collect_num")),
                "comment_count": to_number(d.get("comment_count")),
                "error_code": None,
                "error_msg": None,
            }

        err_code = data.get("code", data.get("status", "unknown"))
        err_msg = data.get("msg") or data.get("message") or data
        if not isinstance(err_msg, str):
            err_msg = str(err_msg)
        fatal = err_code in (20002, 20003)
        status = "failed" if fatal else "uncertain"
        return {
            "status": status,
            "read_count": 0,
            "like_count": 0,
            "wow_count": 0,
            "share_count": 0,
            "collect_count": 0,
            "comment_count": 0,
            "error_code": str(err_code)[:64],
            "error_msg": str(err_msg)[:500],
        }
