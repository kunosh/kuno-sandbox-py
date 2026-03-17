"""Synchronous wrapper around the async KunoClient."""

from __future__ import annotations

import asyncio
import concurrent.futures
import threading
from collections.abc import AsyncIterator, Awaitable, Iterator
from types import TracebackType
from typing import Any, TypeVar

from .client import KunoClient
from .resources.sandboxes import PRESET_IMAGES
from .types import (
    AgentConfig,
    AgentKind,
    ExecResponse,
    ExecStreamEvent,
    PoolStatus,
    SandboxInfo,
    SandboxState,
    SessionInfo,
    UniversalEvent,
)

T = TypeVar("T")


class _EventLoop:
    """Manages a dedicated asyncio event loop running in a background thread.

    Each :class:`SyncKunoClient` owns one instance so that synchronous callers
    can invoke async SDK methods safely — even from threads that already have a
    running event loop.
    """

    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._thread.start()

    def run(self, coro: Awaitable[T]) -> T:
        """Submit *coro* to the background loop and block until it completes."""
        future: concurrent.futures.Future[T] = asyncio.run_coroutine_threadsafe(
            coro,  # type: ignore[arg-type]
            self._loop,
        )
        return future.result()

    def close(self) -> None:
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join()
        self._loop.close()


def _sync_iter(loop: _EventLoop, async_iter: AsyncIterator[T]) -> Iterator[T]:
    """Adapt an async iterator into a synchronous one using *loop*."""
    while True:
        try:
            yield loop.run(async_iter.__anext__())
        except StopAsyncIteration:
            return


# ---------------------------------------------------------------------------
# SyncSandbox
# ---------------------------------------------------------------------------


class SyncSandbox:
    """Synchronous wrapper around :class:`~kuno_sandbox.models.sandbox.Sandbox`."""

    def __init__(self, _sandbox: Any, _loop: _EventLoop) -> None:
        from .models.sandbox import Sandbox

        self._sandbox: Sandbox = _sandbox
        self._loop = _loop
        self.id: str = _sandbox.id
        self.name: str | None = _sandbox.name
        self.state: str | None = _sandbox.state

    def exec(
        self,
        cmd: str,
        *,
        args: list[str] | None = None,
        env: list[str] | None = None,
        working_dir: str | None = None,
    ) -> ExecResponse:
        return self._loop.run(
            self._sandbox.exec(cmd, args=args, env=env, working_dir=working_dir)
        )

    def exec_stream(
        self,
        cmd: str,
        *,
        args: list[str] | None = None,
        env: list[str] | None = None,
        working_dir: str | None = None,
    ) -> Iterator[ExecStreamEvent]:
        async_iter: AsyncIterator[ExecStreamEvent] = self._loop.run(
            self._sandbox.exec_stream(cmd, args=args, env=env, working_dir=working_dir)
        )
        return _sync_iter(self._loop, async_iter)

    def run(self, code: str, *, interpreter: str = "sh") -> str:
        return self._loop.run(self._sandbox.run(code, interpreter=interpreter))

    def upload(self, guest_path: str, data: bytes | str) -> None:
        self._loop.run(self._sandbox.upload(guest_path, data))

    def download(self, guest_path: str) -> bytes:
        return self._loop.run(self._sandbox.download(guest_path))

    def pause(self) -> None:
        self._loop.run(self._sandbox.pause())

    def resume(self) -> None:
        self._loop.run(self._sandbox.resume())

    def inspect(self) -> SyncSandbox:
        self._loop.run(self._sandbox.inspect())
        self.name = self._sandbox.name
        self.state = self._sandbox.state
        return self

    def destroy(self) -> None:
        self._loop.run(self._sandbox.destroy())

    def __enter__(self) -> SyncSandbox:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.destroy()


# ---------------------------------------------------------------------------
# SyncAgentSession
# ---------------------------------------------------------------------------


class SyncAgentSession:
    """Synchronous wrapper around :class:`~kuno_sandbox.models.agent_session.AgentSession`."""

    def __init__(self, _session: Any, _loop: _EventLoop) -> None:
        from .models.agent_session import AgentSession

        self._session: AgentSession = _session
        self._loop = _loop
        self.id: str = _session.id
        self.agent_kind: str | None = _session.agent_kind
        self.label: str | None = _session.label
        self.state: str | None = _session.state

    def send_message(self, message: str) -> Iterator[UniversalEvent]:
        async_iter: AsyncIterator[UniversalEvent] = self._loop.run(
            self._session.send_message(message)
        )
        return _sync_iter(self._loop, async_iter)

    def subscribe_events(self) -> Iterator[UniversalEvent]:
        async_iter: AsyncIterator[UniversalEvent] = self._loop.run(
            self._session.subscribe_events()
        )
        return _sync_iter(self._loop, async_iter)

    def upload(self, guest_path: str, data: bytes | str) -> None:
        self._loop.run(self._session.upload(guest_path, data))

    def download(self, guest_path: str) -> bytes:
        return self._loop.run(self._session.download(guest_path))

    def inspect(self) -> SyncAgentSession:
        self._loop.run(self._session.inspect())
        self.state = self._session.state
        return self

    def destroy(self) -> None:
        self._loop.run(self._session.destroy())

    def __enter__(self) -> SyncAgentSession:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.destroy()


# ---------------------------------------------------------------------------
# Sync resource wrappers
# ---------------------------------------------------------------------------


class _SyncSandboxResource:
    """Synchronous wrapper for :class:`~kuno_sandbox.resources.sandboxes.SandboxResource`."""

    def __init__(self, _resource: Any, _loop: _EventLoop) -> None:
        from .resources.sandboxes import SandboxResource

        self._resource: SandboxResource = _resource
        self._loop = _loop

    def create(
        self,
        image: str,
        *,
        name: str | None = None,
        cpus: int | None = None,
        memory_mb: int | None = None,
        env: dict[str, str] | None = None,
        workdir: str | None = None,
        volumes: list[str] | None = None,
        ports: list[str] | None = None,
        shell: str | None = None,
        scripts: dict[str, str] | None = None,
    ) -> SyncSandbox:
        sb = self._loop.run(
            self._resource.create(
                image,
                name=name,
                cpus=cpus,
                memory_mb=memory_mb,
                env=env,
                workdir=workdir,
                volumes=volumes,
                ports=ports,
                shell=shell,
                scripts=scripts,
            )
        )
        return SyncSandbox(sb, self._loop)

    def python(self, **kwargs: object) -> SyncSandbox:
        """Create a sandbox with ``python:3.12-slim``."""
        return self.create(PRESET_IMAGES["python"], **kwargs)  # type: ignore[arg-type]

    def node(self, **kwargs: object) -> SyncSandbox:
        """Create a sandbox with ``node:22-slim``."""
        return self.create(PRESET_IMAGES["node"], **kwargs)  # type: ignore[arg-type]

    def ubuntu(self, **kwargs: object) -> SyncSandbox:
        """Create a sandbox with ``ubuntu:24.04``."""
        return self.create(PRESET_IMAGES["ubuntu"], **kwargs)  # type: ignore[arg-type]

    def list(self, state: SandboxState | None = None) -> list[SandboxInfo]:
        return self._loop.run(self._resource.list(state=state))

    def get(self, sandbox_id: str) -> SyncSandbox:
        sb = self._loop.run(self._resource.get(sandbox_id))
        return SyncSandbox(sb, self._loop)

    def destroy(self, sandbox_id: str) -> None:
        self._loop.run(self._resource.destroy(sandbox_id))


class _SyncAgentResource:
    """Synchronous wrapper for :class:`~kuno_sandbox.resources.agents.AgentResource`."""

    def __init__(self, _resource: Any, _loop: _EventLoop) -> None:
        from .resources.agents import AgentResource

        self._resource: AgentResource = _resource
        self._loop = _loop

    def create_session(
        self,
        agent: AgentKind,
        *,
        label: str | None = None,
        image: str | None = None,
        cpus: int | None = None,
        memory_mb: int | None = None,
        env: dict[str, str] | None = None,
        agent_config: AgentConfig | None = None,
    ) -> SyncAgentSession:
        session = self._loop.run(
            self._resource.create_session(
                agent,
                label=label,
                image=image,
                cpus=cpus,
                memory_mb=memory_mb,
                env=env,
                agent_config=agent_config,
            )
        )
        return SyncAgentSession(session, self._loop)

    def list_sessions(self) -> list[SessionInfo]:
        return self._loop.run(self._resource.list_sessions())

    def get_session(self, session_id: str) -> SyncAgentSession:
        session = self._loop.run(self._resource.get_session(session_id))
        return SyncAgentSession(session, self._loop)

    def destroy_session(self, session_id: str) -> None:
        self._loop.run(self._resource.destroy_session(session_id))


# ---------------------------------------------------------------------------
# SyncKunoClient
# ---------------------------------------------------------------------------


class SyncKunoClient:
    """Synchronous wrapper around :class:`~kuno_sandbox.client.KunoClient`.

    Uses a dedicated background event loop for thread-safety.

    Example::

        with SyncKunoClient() as client:
            sandbox = client.sandboxes.python()
            output = sandbox.run('print("hello")', interpreter="python3")
            sandbox.destroy()
    """

    def __init__(
        self,
        base_url: str | None = None,
        token: str | None = None,
        timeout: float | None = None,
    ) -> None:
        self._loop = _EventLoop()
        self._client = KunoClient(base_url=base_url, token=token, timeout=timeout)
        self.sandboxes = _SyncSandboxResource(self._client.sandboxes, self._loop)
        self.agents = _SyncAgentResource(self._client.agents, self._loop)

    def health(self) -> str:
        return self._loop.run(self._client.health())

    def ready(self) -> str:
        return self._loop.run(self._client.ready())

    def metrics(self) -> str:
        return self._loop.run(self._client.metrics())

    def pool(self) -> PoolStatus:
        return self._loop.run(self._client.pool())

    def close(self) -> None:
        """Close the underlying HTTP client and background event loop."""
        self._loop.run(self._client.aclose())
        self._loop.close()

    def __enter__(self) -> SyncKunoClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()
