"""OpenAI-compatible chat client (DeepSeek etc.)."""

from __future__ import annotations

from typing import Any

import httpx


class LlmError(RuntimeError):
    def __init__(self, message: str, *, status: int | None = None, body: Any = None) -> None:
        super().__init__(message)
        self.status = status
        self.body = body


class LlmClient:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        *,
        timeout: float = 120.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._owns = client is None
        self._client = client or httpx.Client(timeout=timeout)

    def close(self) -> None:
        if self._owns:
            self._client.close()

    def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 1500,
        **kwargs: Any,
    ) -> str:
        if not self.api_key:
            raise LlmError("LLM_API_KEY missing")
        url = f"{self.base_url}/v1/chat/completions"
        # some providers already include /v1 in base
        if self.base_url.endswith("/v1"):
            url = f"{self.base_url}/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs,
        }
        r = self._client.post(
            url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        if r.status_code >= 400:
            raise LlmError(f"LLM HTTP {r.status_code}: {r.text[:500]}", status=r.status_code, body=r.text)
        data = r.json()
        content = (
            (data.get("choices") or [{}])[0].get("message", {}).get("content")
            or data.get("message", {}).get("content")
            or data.get("text")
            or data.get("output")
            or ""
        )
        if not str(content).strip():
            raise LlmError("EMPTY_RESPONSE", body=data)
        return str(content).strip()
