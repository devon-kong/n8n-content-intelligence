"""Unpack Feishu rich text / link / array field values."""

from __future__ import annotations

from typing import Any


def as_text(value: Any) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value).strip()
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, dict):
                parts.append(str(item.get("text") or item.get("name") or item.get("link") or ""))
            else:
                parts.append(str(item))
        return "".join(parts).strip()
    if isinstance(value, dict):
        return str(value.get("text") or value.get("link") or value.get("name") or value.get("value") or "").strip()
    return str(value).strip()


def as_link(value: Any) -> str:
    if not value:
        return ""
    if isinstance(value, list):
        return "".join(
            str(x.get("link") or x.get("text") or "") if isinstance(x, dict) else str(x) for x in value
        ).strip()
    if isinstance(value, dict):
        return str(value.get("link") or value.get("text") or "").strip()
    return as_text(value)


def as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value in (1, "1", "true", "True", "TRUE"):
        return True
    return bool(value)


def make_url_field(url: str, text: str | None = None) -> dict[str, str]:
    u = (url or "").strip()
    return {"text": (text or u).strip() or u, "link": u, "type": "url"}
