"""wechat2rss feed client (read-only). Do not restart/modify the container."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx


class Wechat2RssError(RuntimeError):
    pass


class Wechat2RssClient:
    def __init__(
        self,
        base_url: str,
        token: str = "",
        *,
        timeout: float = 60.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self._owns = client is None
        self._client = client or httpx.Client(timeout=timeout)

    def close(self) -> None:
        if self._owns:
            self._client.close()

    def feed_url(self, biz_id: str) -> str:
        return f"{self.base_url}/feed/{quote(str(biz_id), safe='')}.json"

    def fetch_feed(self, biz_id: str) -> dict[str, Any] | list[Any]:
        url = self.feed_url(biz_id)
        params = {}
        if self.token:
            # Match the n8n HTTP Query Auth credential's parameter name.
            params["k"] = self.token
        r = self._client.get(url, params=params or None)
        if r.status_code >= 400:
            raise Wechat2RssError(f"feed HTTP {r.status_code} for biz_id={biz_id}: {r.text[:300]}")
        try:
            return r.json()
        except Exception as e:
            raise Wechat2RssError(f"invalid JSON feed for biz_id={biz_id}: {e}") from e
