"""Tests for agent session lifecycle, send_message SSE, and error cases."""

from __future__ import annotations

import json

import pytest
from pytest_httpx import HTTPXMock

from kuno_sandbox import (
    AgentKind,
    ConflictError,
    GoneError,
    KunoClient,
    RateLimitError,
    TextEvent,
    TurnCompleteEvent,
)


async def test_create_session(httpx_mock: HTTPXMock, client: KunoClient) -> None:
    httpx_mock.add_response(
        url="http://test:8080/api/v1/agents/sessions",
        method="POST",
        json={
            "id": "sess-1",
            "agent_kind": "claude-code",
            "state": "idle",
            "created_at": "2025-01-01T00:00:00Z",
        },
        status_code=201,
    )
    session = await client.agents.create_session(agent=AgentKind.CLAUDE_CODE)
    assert session.id == "sess-1"
    assert session.agent_kind == "claude-code"
    assert session.state == "idle"


async def test_list_sessions(httpx_mock: HTTPXMock, client: KunoClient) -> None:
    httpx_mock.add_response(
        url="http://test:8080/api/v1/agents/sessions",
        json=[
            {"id": "s1", "agent_kind": "claude-code", "state": "idle"},
            {"id": "s2", "agent_kind": "codex", "state": "processing"},
        ],
    )
    sessions = await client.agents.list_sessions()
    assert len(sessions) == 2
    assert sessions[0].id == "s1"


async def test_get_session(httpx_mock: HTTPXMock, client: KunoClient) -> None:
    httpx_mock.add_response(
        url="http://test:8080/api/v1/agents/sessions/sess-1",
        json={"id": "sess-1", "agent_kind": "claude-code", "state": "idle"},
    )
    session = await client.agents.get_session("sess-1")
    assert session.id == "sess-1"


async def test_destroy_session(httpx_mock: HTTPXMock, client: KunoClient) -> None:
    httpx_mock.add_response(
        url="http://test:8080/api/v1/agents/sessions/sess-1",
        method="DELETE",
        status_code=204,
    )
    await client.agents.destroy_session("sess-1")


async def test_send_message_sse(httpx_mock: HTTPXMock, client: KunoClient) -> None:
    events = [
        {"event": "text", "data": json.dumps({
            "session_id": "sess-1",
            "kind": {"type": "text", "content": "Hello ", "is_delta": True},
            "timestamp": "2025-01-01T00:00:00Z",
        })},
        {"event": "text", "data": json.dumps({
            "session_id": "sess-1",
            "kind": {"type": "text", "content": "world!", "is_delta": True},
            "timestamp": "2025-01-01T00:00:01Z",
        })},
        {"event": "turn_complete", "data": json.dumps({
            "session_id": "sess-1",
            "kind": {"type": "turn_complete", "stop_reason": "end_turn"},
            "timestamp": "2025-01-01T00:00:02Z",
        })},
    ]
    sse_body = ""
    for evt in events:
        sse_body += f"event: {evt['event']}\ndata: {evt['data']}\n\n"

    httpx_mock.add_response(
        url="http://test:8080/api/v1/agents/sessions/sess-1/messages",
        method="POST",
        content=sse_body.encode(),
        headers={"content-type": "text/event-stream"},
    )

    # Get session
    httpx_mock.add_response(
        url="http://test:8080/api/v1/agents/sessions",
        method="POST",
        json={"id": "sess-1", "agent_kind": "claude-code", "state": "idle"},
        status_code=201,
    )

    session = await client.agents.create_session(agent=AgentKind.CLAUDE_CODE)

    collected = []
    async for event in await session.send_message("Hello"):
        collected.append(event)

    assert len(collected) == 3
    assert isinstance(collected[0].kind, TextEvent)
    assert collected[0].kind.content == "Hello "
    assert isinstance(collected[2].kind, TurnCompleteEvent)


async def test_session_context_manager(httpx_mock: HTTPXMock, client: KunoClient) -> None:
    httpx_mock.add_response(
        url="http://test:8080/api/v1/agents/sessions",
        method="POST",
        json={"id": "sess-1", "agent_kind": "claude-code", "state": "idle"},
        status_code=201,
    )
    httpx_mock.add_response(
        url="http://test:8080/api/v1/agents/sessions/sess-1",
        method="DELETE",
        status_code=204,
    )
    session = await client.agents.create_session(agent=AgentKind.CLAUDE_CODE)
    async with session:
        assert session.id == "sess-1"
    # destroy called via __aexit__


async def test_conflict_error_409(httpx_mock: HTTPXMock, client: KunoClient) -> None:
    httpx_mock.add_response(
        url="http://test:8080/api/v1/agents/sessions/sess-1/messages",
        method="POST",
        json={"error": "session is not in idle state"},
        status_code=409,
    )
    with pytest.raises(ConflictError, match="not in idle state"):
        await client.agents._send_message_raw("sess-1", "test")


async def test_gone_error_410(httpx_mock: HTTPXMock, client: KunoClient) -> None:
    httpx_mock.add_response(
        url="http://test:8080/api/v1/agents/sessions/sess-1",
        method="DELETE",
        json={"error": "session already destroyed"},
        status_code=410,
    )
    with pytest.raises(GoneError, match="already destroyed"):
        await client.agents.destroy_session("sess-1")


async def test_rate_limit_error_429(httpx_mock: HTTPXMock, client: KunoClient) -> None:
    httpx_mock.add_response(
        url="http://test:8080/api/v1/agents/sessions",
        method="POST",
        json={"error": "session limit reached", "hint": "max 10 sessions"},
        status_code=429,
    )
    with pytest.raises(RateLimitError, match="session limit reached"):
        await client.agents.create_session(agent=AgentKind.CLAUDE_CODE)
