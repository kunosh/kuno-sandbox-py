"""Sandbox bound model — exec, files, lifecycle."""

from __future__ import annotations

import base64
from collections.abc import AsyncIterator
from types import TracebackType

from .._http import HttpClient
from .._sse import iter_exec_sse
from ..errors import ExecError
from ..types import (
    DownloadResponse,
    ExecResponse,
    ExecStreamEvent,
    SandboxInfo,
)


class Sandbox:
    """A bound sandbox instance with convenience methods."""

    def __init__(self, info: SandboxInfo, http: HttpClient) -> None:
        self._http = http
        self._id = info.id
        self.id = info.id
        self.name = info.name
        self.state = info.state

    async def exec(
        self,
        cmd: str,
        *,
        args: list[str] | None = None,
        env: list[str] | None = None,
        working_dir: str | None = None,
    ) -> ExecResponse:
        body: dict[str, object] = {"cmd": cmd}
        if args:
            body["args"] = args
        if env:
            body["env"] = env
        if working_dir is not None:
            body["working_dir"] = working_dir
        data = await self._http.request(
            "POST", f"/api/v1/sandboxes/{self._id}/exec", json=body
        )
        return ExecResponse.model_validate(data)

    async def exec_stream(
        self,
        cmd: str,
        *,
        args: list[str] | None = None,
        env: list[str] | None = None,
        working_dir: str | None = None,
    ) -> AsyncIterator[ExecStreamEvent]:
        body: dict[str, object] = {"cmd": cmd}
        if args:
            body["args"] = args
        if env:
            body["env"] = env
        if working_dir is not None:
            body["working_dir"] = working_dir
        response = await self._http.stream_request(
            "POST", f"/api/v1/sandboxes/{self._id}/exec/stream", json=body
        )
        return iter_exec_sse(response)

    async def run(self, code: str, *, interpreter: str = "sh") -> str:
        """Execute *code* via the given interpreter and return stdout.

        Raises :class:`~kuno_sandbox.errors.ExecError` when the command exits
        with a non-zero exit code.
        """
        result = await self.exec(interpreter, args=["-c", code])
        if result.exit_code != 0:
            raise ExecError(
                exit_code=result.exit_code,
                stdout=result.stdout,
                stderr=result.stderr,
            )
        return result.stdout

    async def upload(self, guest_path: str, data: bytes | str) -> None:
        if isinstance(data, str):
            raw = data.encode()
        else:
            raw = data
        encoded = base64.b64encode(raw).decode()
        await self._http.request(
            "POST",
            f"/api/v1/sandboxes/{self._id}/upload",
            json={"guest_path": guest_path, "data": encoded},
        )

    async def download(self, guest_path: str) -> bytes:
        data = await self._http.request(
            "GET",
            f"/api/v1/sandboxes/{self._id}/download",
            params={"path": guest_path},
        )
        resp = DownloadResponse.model_validate(data)
        return base64.b64decode(resp.data)

    async def pause(self) -> None:
        await self._http.request_void(
            "POST", f"/api/v1/sandboxes/{self._id}/pause"
        )

    async def resume(self) -> None:
        await self._http.request_void(
            "POST", f"/api/v1/sandboxes/{self._id}/resume"
        )

    async def inspect(self) -> Sandbox:
        data = await self._http.request(
            "GET", f"/api/v1/sandboxes/{self._id}"
        )
        info = SandboxInfo.model_validate(data)
        self.name = info.name
        self.state = info.state
        return self

    async def destroy(self) -> None:
        await self._http.request_void(
            "DELETE", f"/api/v1/sandboxes/{self._id}"
        )

    async def __aenter__(self) -> Sandbox:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.destroy()
