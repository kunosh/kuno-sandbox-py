"""Tests for the SSE parser with synthetic streams."""

from __future__ import annotations

import json

import httpx

from kuno_sandbox._sse import iter_agent_sse, iter_exec_sse
from kuno_sandbox.types import (
    ErrorEvent,
    ExitEvent,
    TextEvent,
    ThinkingEvent,
    ToolUseEvent,
    TurnCompleteEvent,
)


def _make_sse_response(
    events: list[dict[str, str]], url: str = "http://test/sse"
) -> httpx.Response:
    """Build a fake httpx.Response with SSE content."""
    body = ""
    for evt in events:
        if "event" in evt:
            body += f"event: {evt['event']}\n"
        body += f"data: {evt['data']}\n\n"

    return httpx.Response(
        status_code=200,
        headers={"content-type": "text/event-stream"},
        content=body.encode(),
        request=httpx.Request("GET", url),
    )


def _agent_event(event_type: str, kind_data: dict[str, object]) -> dict[str, str]:
    kind_data["type"] = event_type
    return {
        "event": event_type,
        "data": json.dumps({
            "session_id": "s1",
            "kind": kind_data,
            "timestamp": "2025-01-01T00:00:00Z",
        }),
    }


async def test_agent_sse_text_events() -> None:
    events = [
        _agent_event("text", {"content": "Hello", "is_delta": True}),
        _agent_event("text", {"content": " world", "is_delta": True}),
        _agent_event("turn_complete", {"stop_reason": "end_turn"}),
    ]
    response = _make_sse_response(events)
    collected = [e async for e in iter_agent_sse(response)]
    assert len(collected) == 3
    assert isinstance(collected[0].kind, TextEvent)
    assert collected[0].kind.content == "Hello"
    assert isinstance(collected[2].kind, TurnCompleteEvent)


async def test_agent_sse_stops_on_terminal() -> None:
    events = [
        _agent_event("text", {"content": "hi"}),
        _agent_event("turn_complete", {}),
        _agent_event("text", {"content": "should not appear"}),
    ]
    response = _make_sse_response(events)
    collected = [e async for e in iter_agent_sse(response, stop_on_terminal=True)]
    assert len(collected) == 2


async def test_agent_sse_no_stop_on_terminal() -> None:
    events = [
        _agent_event("text", {"content": "hi"}),
        _agent_event("turn_complete", {}),
        _agent_event("text", {"content": "next turn"}),
    ]
    response = _make_sse_response(events)
    collected = [e async for e in iter_agent_sse(response, stop_on_terminal=False)]
    assert len(collected) == 3


async def test_agent_sse_thinking_event() -> None:
    events = [
        _agent_event("thinking", {}),
        _agent_event("turn_complete", {}),
    ]
    response = _make_sse_response(events)
    collected = [e async for e in iter_agent_sse(response)]
    assert isinstance(collected[0].kind, ThinkingEvent)


async def test_agent_sse_tool_use_event() -> None:
    events = [
        _agent_event("tool_use", {"tool": "bash", "input": {"cmd": "ls"}, "tool_use_id": "t1"}),
        _agent_event("turn_complete", {}),
    ]
    response = _make_sse_response(events)
    collected = [e async for e in iter_agent_sse(response)]
    assert isinstance(collected[0].kind, ToolUseEvent)
    assert collected[0].kind.tool == "bash"


async def test_agent_sse_error_event_is_terminal() -> None:
    events = [
        _agent_event("error", {"message": "something broke", "code": "INTERNAL"}),
    ]
    response = _make_sse_response(events)
    collected = [e async for e in iter_agent_sse(response)]
    assert len(collected) == 1
    assert isinstance(collected[0].kind, ErrorEvent)
    assert collected[0].kind.message == "something broke"


async def test_agent_sse_exit_event_is_terminal() -> None:
    events = [
        _agent_event("exit", {"exit_code": 1}),
    ]
    response = _make_sse_response(events)
    collected = [e async for e in iter_agent_sse(response)]
    assert len(collected) == 1
    assert isinstance(collected[0].kind, ExitEvent)
    assert collected[0].kind.exit_code == 1


async def test_agent_sse_skips_unknown_events() -> None:
    events = [
        {"event": "heartbeat", "data": "{}"},
        _agent_event("text", {"content": "hi"}),
        _agent_event("turn_complete", {}),
    ]
    response = _make_sse_response(events)
    collected = [e async for e in iter_agent_sse(response)]
    assert len(collected) == 2


async def test_exec_sse_chunks_and_exit() -> None:
    stdout_chunk = json.dumps(
        {"type": "chunk", "stream": "Stdout", "data": "line1\n"}
    )
    stderr_chunk = json.dumps(
        {"type": "chunk", "stream": "Stderr", "data": "warn\n"}
    )
    exit_evt = json.dumps({"type": "exit", "exit_code": 0})
    events = [
        {"event": "message", "data": stdout_chunk},
        {"event": "message", "data": stderr_chunk},
        {"event": "message", "data": exit_evt},
    ]
    response = _make_sse_response(events)
    collected = [e async for e in iter_exec_sse(response)]
    assert len(collected) == 3
    assert collected[0].type == "chunk"
    assert collected[2].type == "exit"


async def test_exec_sse_stops_on_exit() -> None:
    exit_evt = json.dumps({"type": "exit", "exit_code": 0})
    nope_chunk = json.dumps(
        {"type": "chunk", "stream": "Stdout", "data": "nope"}
    )
    events = [
        {"event": "message", "data": exit_evt},
        {"event": "message", "data": nope_chunk},
    ]
    response = _make_sse_response(events)
    collected = [e async for e in iter_exec_sse(response)]
    assert len(collected) == 1
