"""Health, readiness, metrics, and pool resources."""

from __future__ import annotations

from .._http import HttpClient
from ..types import PoolStatus


class HealthResource:
    """Health / readiness / metrics / pool endpoints."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    async def health(self) -> str:
        return await self._http.request_text("GET", "/healthz")

    async def ready(self) -> str:
        return await self._http.request_text("GET", "/readyz")

    async def metrics(self) -> str:
        return await self._http.request_text("GET", "/metrics")

    async def pool(self) -> PoolStatus:
        data = await self._http.request("GET", "/api/v1/pool/status")
        return PoolStatus.model_validate(data)
