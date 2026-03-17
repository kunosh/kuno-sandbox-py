"""Snapshot CRUD resource."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .._http import HttpClient
from ..types import SnapshotInfo, SandboxInfo

if TYPE_CHECKING:
    from ..models.sandbox import Sandbox


class SnapshotResource:
    """List, get, restore, and delete snapshots."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    async def list(self) -> list[SnapshotInfo]:
        """List all snapshots."""
        data = await self._http.request("GET", "/api/v1/snapshots")
        return [SnapshotInfo.model_validate(s) for s in data]

    async def get(self, snapshot_id: str) -> SnapshotInfo:
        """Get snapshot metadata by ID."""
        data = await self._http.request(
            "GET", f"/api/v1/snapshots/{snapshot_id}"
        )
        return SnapshotInfo.model_validate(data)

    async def restore(self, snapshot_id: str) -> Sandbox:
        """Restore a sandbox from a snapshot. Returns a bound Sandbox instance."""
        from ..models.sandbox import Sandbox

        data = await self._http.request(
            "POST", f"/api/v1/snapshots/{snapshot_id}/restore"
        )
        info = SandboxInfo.model_validate(data)
        return Sandbox(info=info, http=self._http)

    async def delete(self, snapshot_id: str) -> None:
        """Delete a snapshot by ID."""
        await self._http.request_void(
            "DELETE", f"/api/v1/snapshots/{snapshot_id}"
        )
