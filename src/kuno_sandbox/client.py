"""KunoClient — async-first client for the Kuno Sandbox API."""

from __future__ import annotations

from types import TracebackType

from ._config import resolve_config
from ._http import HttpClient
from .resources.agents import AgentResource
from .resources.health import HealthResource
from .resources.sandboxes import SandboxResource
from .types import PoolStatus


class KunoClient:
    """Async client for the Kuno Sandbox API.

    Example::

        async with KunoClient() as client:
            sandbox = await client.sandboxes.create("alpine:latest")
            result = await sandbox.exec("echo", args=["hello"])
            print(result.stdout)
    """

    def __init__(
        self,
        base_url: str | None = None,
        token: str | None = None,
        timeout: float | None = None,
    ) -> None:
        config = resolve_config(base_url, token, timeout)
        self._http = HttpClient(config)
        self._health = HealthResource(self._http)

        self.sandboxes = SandboxResource(self._http)
        self.agents = AgentResource(self._http)

    async def health(self) -> str:
        """Liveness probe. Returns 'ok'."""
        return await self._health.health()

    async def ready(self) -> str:
        """Readiness probe. Returns 'ready'."""
        return await self._health.ready()

    async def metrics(self) -> str:
        """Prometheus metrics."""
        return await self._health.metrics()

    async def pool(self) -> PoolStatus:
        """Warm pool status."""
        return await self._health.pool()

    async def aclose(self) -> None:
        """Close the underlying HTTP client."""
        await self._http.aclose()

    async def __aenter__(self) -> KunoClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.aclose()
