"""Agent session CRUD resource."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .._http import HttpClient
from ..types import AgentConfig, AgentKind, CreateSessionRequest, SessionInfo

if TYPE_CHECKING:
    from ..models.agent_session import AgentSession


class AgentResource:
    """Create, list, get, and destroy agent sessions."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    async def create_session(
        self,
        agent: AgentKind,
        *,
        label: str | None = None,
        image: str | None = None,
        cpus: int | None = None,
        memory_mb: int | None = None,
        env: dict[str, str] | None = None,
        agent_config: AgentConfig | None = None,
    ) -> AgentSession:
        from ..models.agent_session import AgentSession

        body = CreateSessionRequest(
            agent=agent,
            label=label,
            image=image,
            cpus=cpus,
            memory_mb=memory_mb,
            env=env,
            agent_config=agent_config,
        )
        data = await self._http.request(
            "POST",
            "/api/v1/agents/sessions",
            json=body.model_dump(exclude_none=True),
        )
        info = SessionInfo.model_validate(data)
        return AgentSession(info=info, http=self._http)

    async def list_sessions(self) -> list[SessionInfo]:
        data = await self._http.request("GET", "/api/v1/agents/sessions")
        return [SessionInfo.model_validate(s) for s in data]

    async def get_session(self, session_id: str) -> AgentSession:
        from ..models.agent_session import AgentSession

        data = await self._http.request(
            "GET", f"/api/v1/agents/sessions/{session_id}"
        )
        info = SessionInfo.model_validate(data)
        return AgentSession(info=info, http=self._http)

    async def destroy_session(self, session_id: str) -> None:
        await self._http.request_void(
            "DELETE", f"/api/v1/agents/sessions/{session_id}"
        )

    async def _send_message_raw(
        self, session_id: str, message: str
    ) -> Any:
        """Send a message, return raw streaming response for SSE parsing."""
        return await self._http.stream_request(
            "POST",
            f"/api/v1/agents/sessions/{session_id}/messages",
            json={"message": message},
        )

    async def _subscribe_events_raw(self, session_id: str) -> Any:
        """Subscribe to session events, return raw streaming response."""
        return await self._http.stream_request(
            "GET",
            f"/api/v1/agents/sessions/{session_id}/events",
        )
