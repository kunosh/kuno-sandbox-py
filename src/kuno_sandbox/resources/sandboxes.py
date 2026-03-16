"""Sandbox CRUD resource."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .._http import HttpClient
from ..types import CreateSandboxRequest, SandboxInfo, SandboxState

if TYPE_CHECKING:
    from ..models.sandbox import Sandbox


class SandboxResource:
    """Create, list, get, and destroy sandboxes."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    async def create(
        self,
        image: str,
        *,
        name: str | None = None,
        cpus: int | None = None,
        memory_mb: int | None = None,
        env: dict[str, str] | None = None,
        workdir: str | None = None,
    ) -> Sandbox:
        from ..models.sandbox import Sandbox

        body = CreateSandboxRequest(
            image=image,
            name=name,
            cpus=cpus,
            memory_mb=memory_mb,
            env=env,
            workdir=workdir,
        )
        data = await self._http.request(
            "POST",
            "/api/v1/sandboxes",
            json=body.model_dump(exclude_none=True),
        )
        info = SandboxInfo.model_validate(data)
        return Sandbox(info=info, http=self._http)

    async def list(self, state: SandboxState | None = None) -> list[SandboxInfo]:
        params: dict[str, str] = {}
        if state is not None:
            params["state"] = state.value
        data = await self._http.request("GET", "/api/v1/sandboxes", params=params)
        return [SandboxInfo.model_validate(s) for s in data]

    async def get(self, sandbox_id: str) -> Sandbox:
        from ..models.sandbox import Sandbox

        data = await self._http.request("GET", f"/api/v1/sandboxes/{sandbox_id}")
        info = SandboxInfo.model_validate(data)
        return Sandbox(info=info, http=self._http)

    async def destroy(self, sandbox_id: str) -> None:
        await self._http.request_void("DELETE", f"/api/v1/sandboxes/{sandbox_id}")
