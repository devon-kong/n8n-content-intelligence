"""Feishu bitable client (tenant token + records search/create/update).

Uses OpenAPI bitable/v1 (same family as N8N feishu-lite nodes).
"""

from __future__ import annotations

import time
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential


class FeishuError(RuntimeError):
    def __init__(self, message: str, *, code: Any = None, body: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.body = body


class FeishuClient:
    BASE = "https://open.feishu.cn/open-apis"

    def __init__(
        self,
        app_id: str,
        app_secret: str,
        *,
        timeout: float = 60.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.app_id = app_id
        self.app_secret = app_secret
        self._token: str | None = None
        self._token_expire_at: float = 0.0
        self._owns_client = client is None
        self._client = client or httpx.Client(timeout=timeout)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> FeishuClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=4), reraise=True)
    def tenant_token(self) -> str:
        now = time.time()
        if self._token and now < self._token_expire_at - 60:
            return self._token
        if not self.app_id or not self.app_secret:
            raise FeishuError("FEISHU_APP_ID / FEISHU_APP_SECRET missing")
        r = self._client.post(
            f"{self.BASE}/auth/v3/tenant_access_token/internal",
            json={"app_id": self.app_id, "app_secret": self.app_secret},
        )
        r.raise_for_status()
        data = r.json()
        if data.get("code") not in (0, None):
            raise FeishuError(f"tenant_access_token failed: {data}", code=data.get("code"), body=data)
        token = data.get("tenant_access_token") or data.get("app_access_token")
        if not token:
            raise FeishuError(f"no token in response: {data}", body=data)
        self._token = token
        self._token_expire_at = now + float(data.get("expire") or 7200)
        return token

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.tenant_token()}", "Content-Type": "application/json; charset=utf-8"}

    def _check(self, data: dict[str, Any], action: str) -> dict[str, Any]:
        if data.get("code") not in (0, None):
            raise FeishuError(f"{action} failed code={data.get('code')}: {data}", code=data.get("code"), body=data)
        return data

    def search_records(
        self,
        app_token: str,
        table_id: str,
        *,
        filter: dict[str, Any] | None = None,
        field_names: list[str] | None = None,
        page_size: int = 100,
        page_token: str | None = None,
        automatic_fields: bool = False,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"page_size": page_size, "automatic_fields": automatic_fields}
        if filter is not None:
            body["filter"] = filter
        if field_names is not None:
            body["field_names"] = field_names
        if page_token:
            body["page_token"] = page_token
        url = f"{self.BASE}/bitable/v1/apps/{app_token}/tables/{table_id}/records/search"
        r = self._client.post(url, headers=self._headers(), json=body)
        r.raise_for_status()
        return self._check(r.json(), "search_records")

    def search_all(
        self,
        app_token: str,
        table_id: str,
        *,
        filter: dict[str, Any] | None = None,
        field_names: list[str] | None = None,
        page_size: int = 500,
        max_pages: int = 50,
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        page_token: str | None = None
        for _ in range(max_pages):
            data = self.search_records(
                app_token,
                table_id,
                filter=filter,
                field_names=field_names,
                page_size=page_size,
                page_token=page_token,
            )
            payload = data.get("data") or {}
            batch = payload.get("items") or []
            items.extend(batch)
            if not payload.get("has_more"):
                break
            page_token = payload.get("page_token")
            if not page_token:
                break
        return items

    def create_record(
        self,
        app_token: str,
        table_id: str,
        fields: dict[str, Any],
    ) -> dict[str, Any]:
        url = f"{self.BASE}/bitable/v1/apps/{app_token}/tables/{table_id}/records"
        r = self._client.post(url, headers=self._headers(), json={"fields": fields})
        r.raise_for_status()
        return self._check(r.json(), "create_record")

    def update_record(
        self,
        app_token: str,
        table_id: str,
        record_id: str,
        fields: dict[str, Any],
    ) -> dict[str, Any]:
        url = f"{self.BASE}/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}"
        r = self._client.put(url, headers=self._headers(), json={"fields": fields})
        r.raise_for_status()
        return self._check(r.json(), "update_record")
