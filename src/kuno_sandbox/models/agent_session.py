"""AgentSession bound model — send_message streaming, subscribe, files."""

from __future__ import annotations

import base64
from collections.abc import AsyncIterator
from types import TracebackType

from .._http import HttpClient
from .._sse import iter_agent_sse
from ..types import (
    DownloadResponse,
    HibernateResponse,
    ResumeResponse,
    SessionInfo,
    UniversalEvent,
)


class AgentSession:
    """A bound agent session with streaming and file operations."""

    def __init__(self, info: SessionInfo, http: HttpClient) -> None:
        self._http = http
        self._id = info.id
        self.id = info.id
        self.agent_kind = info.agent_kind
        self.label = info.label
        self.state = info.state
        self.created_at = info.created_at
        self.agent_session_id = info.agent_session_id
        self.usage = info.usage
        self._sandbox_id: str | None = None

    async def send_message(self, message: str) -> AsyncIterator[UniversalEvent]:
        """Send a message to the agent and stream back events.

        Stops iteration on turn_complete, exit, or error events.
        """
        response = await self._http.stream_request(
            "POST",
            f"/api/v1/agents/sessions/{self._id}/messages",
            json={"message": message},
        )
        return iter_agent_sse(response, stop_on_terminal=True)

    async def subscribe_events(self) -> AsyncIterator[UniversalEvent]:
        """Subscribe to all session events across multiple turns.

        The connection stays open until the client disconnects or the session
        is destroyed. Does NOT stop on turn_complete.
        """
        response = await self._http.stream_request(
            "GET",
            f"/api/v1/agents/sessions/{self._id}/events",
        )
        return iter_agent_sse(response, stop_on_terminal=False)

    async def upload(self, guest_path: str, data: bytes | str) -> None:
        """Upload a file into the agent session's sandbox."""
        sandbox_id = await self._resolve_sandbox_id()
        if isinstance(data, str):
            raw = data.encode()
        else:
            raw = data
        encoded = base64.b64encode(raw).decode()
        await self._http.request(
            "POST",
            f"/api/v1/sandboxes/{sandbox_id}/upload",
            json={"guest_path": guest_path, "data": encoded},
        )

    async def download(self, guest_path: str) -> bytes:
        """Download a file from the agent session's sandbox."""
        sandbox_id = await self._resolve_sandbox_id()
        data = await self._http.request(
            "GET",
            f"/api/v1/sandboxes/{sandbox_id}/download",
            params={"path": guest_path},
        )
        resp = DownloadResponse.model_validate(data)
        return base64.b64decode(resp.data)

    async def hibernate(self) -> HibernateResponse:
        """Hibernate this session, creating a snapshot of its state."""
        data = await self._http.request(
            "POST", f"/api/v1/agents/sessions/{self._id}/hibernate"
        )
        return HibernateResponse.model_validate(data)

    async def resume(self) -> ResumeResponse:
        """Resume a previously hibernated session."""
        data = await self._http.request(
            "POST", f"/api/v1/agents/sessions/{self._id}/resume"
        )
        return ResumeResponse.model_validate(data)

    async def inspect(self) -> AgentSession:
        data = await self._http.request(
            "GET", f"/api/v1/agents/sessions/{self._id}"
        )
        info = SessionInfo.model_validate(data)
        self.state = info.state
        self.agent_session_id = info.agent_session_id
        self.usage = info.usage
        return self

    async def destroy(self) -> None:
        await self._http.request_void(
            "DELETE", f"/api/v1/agents/sessions/{self._id}"
        )

    async def _resolve_sandbox_id(self) -> str:
        """Resolve sandbox ID for file operations. Session ID == sandbox ID in current API."""
        if self._sandbox_id is None:
            self._sandbox_id = self._id
        return self._sandbox_id

    async def __aenter__(self) -> AgentSession:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.destroy()
