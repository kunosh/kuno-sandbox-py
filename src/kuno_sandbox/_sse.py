"""SSE stream parsing for the Kuno Sandbox SDK."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import TypeVar

import httpx
import httpx_sse

from .errors import StreamError
from .types import (
    KNOWN_AGENT_EVENT_TYPES,
    TERMINAL_EVENT_TYPES,
    ExecChunkEvent,
    ExecExitEvent,
    ExecStreamEvent,
    UniversalEvent,
)

T = TypeVar("T")


async def iter_agent_sse(
    response: httpx.Response,
    *,
    stop_on_terminal: bool = True,
) -> AsyncIterator[UniversalEvent]:
    """Parse agent SSE events from an httpx streaming response.

    Args:
        response: An httpx response opened with stream=True.
        stop_on_terminal: If True, stop iteration on turn_complete/exit/error.
    """
    event_source = httpx_sse.EventSource(response)
    try:
        async for sse in event_source.aiter_sse():
            if sse.event not in KNOWN_AGENT_EVENT_TYPES:
                continue
            try:
                data = json.loads(sse.data)
            except (json.JSONDecodeError, TypeError) as e:
                raise StreamError(f"Invalid JSON in SSE data: {e}") from e

            event = UniversalEvent.model_validate(data)
            yield event

            if stop_on_terminal and event.kind.type in TERMINAL_EVENT_TYPES:
                return
    finally:
        await response.aclose()


async def iter_exec_sse(
    response: httpx.Response,
) -> AsyncIterator[ExecStreamEvent]:
    """Parse exec SSE events from an httpx streaming response."""
    event_source = httpx_sse.EventSource(response)
    try:
        async for sse in event_source.aiter_sse():
            try:
                data = json.loads(sse.data)
            except (json.JSONDecodeError, TypeError) as e:
                raise StreamError(f"Invalid JSON in SSE data: {e}") from e

            event_type = data.get("type")
            parsed: ExecChunkEvent | ExecExitEvent
            if event_type == "chunk":
                parsed = ExecChunkEvent.model_validate(data)
            elif event_type == "exit":
                parsed = ExecExitEvent.model_validate(data)
                yield parsed
                return
            else:
                continue
            yield parsed
    finally:
        await response.aclose()
