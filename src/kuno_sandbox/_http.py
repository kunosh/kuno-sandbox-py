"""Internal HTTP client wrapper for the Kuno Sandbox SDK."""

from __future__ import annotations

from typing import Any

import httpx

from ._config import Config
from .errors import (
    NetworkError,
    TimeoutError,
    error_from_response,
)

SDK_VERSION = "0.1.0"


class HttpClient:
    """Thin wrapper around httpx.AsyncClient with auth, timeout, and error mapping."""

    def __init__(self, config: Config) -> None:
        headers: dict[str, str] = {
            "User-Agent": f"kuno-sandbox-py/{SDK_VERSION}",
        }
        if config.token:
            headers["Authorization"] = f"Bearer {config.token}"
        self._client = httpx.AsyncClient(
            base_url=config.base_url,
            headers=headers,
            timeout=config.timeout,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def request(self, method: str, path: str, **kwargs: Any) -> Any:
        """Send a JSON request, return parsed response body."""
        response = await self._send(method, path, **kwargs)
        if response.status_code == 204:
            return None
        return response.json()

    async def request_text(self, method: str, path: str) -> str:
        """Send a request, return plain text body."""
        response = await self._send(method, path)
        return response.text

    async def request_void(self, method: str, path: str, **kwargs: Any) -> None:
        """Send a request, expect no content."""
        await self._send(method, path, **kwargs)

    async def stream_request(
        self, method: str, path: str, **kwargs: Any
    ) -> httpx.Response:
        """Send a streaming request, return the raw response (caller must close)."""
        req = self._client.build_request(method, path, **kwargs)
        try:
            response = await self._client.send(req, stream=True)
        except httpx.ConnectError as e:
            raise NetworkError(f"Failed to connect: {e}") from e
        except httpx.TimeoutException as e:
            raise TimeoutError(f"Request timed out: {e}") from e
        if response.status_code >= 400:
            body = await response.aread()
            await response.aclose()
            raise error_from_response(response.status_code, body.decode())
        return response

    async def _send(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        try:
            response = await self._client.request(method, path, **kwargs)
        except httpx.ConnectError as e:
            raise NetworkError(f"Failed to connect: {e}") from e
        except httpx.TimeoutException as e:
            raise TimeoutError(f"Request timed out: {e}") from e
        if response.status_code >= 400:
            raise error_from_response(response.status_code, response.text)
        return response
