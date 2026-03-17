"""Tests for sandbox CRUD, exec, files, pause/resume, presets, run(), and error handling."""

from __future__ import annotations

import base64
import json

import pytest
from pytest_httpx import HTTPXMock

from kuno_sandbox import (
    PRESET_IMAGES,
    ExecError,
    KunoClient,
    NotFoundError,
    SandboxState,
)


async def test_create_sandbox(httpx_mock: HTTPXMock, client: KunoClient) -> None:
    httpx_mock.add_response(
        url="http://test:8080/api/v1/sandboxes",
        method="POST",
        json={"id": "abc-123", "name": "my-sb", "state": "Ready"},
        status_code=201,
    )
    sandbox = await client.sandboxes.create("alpine:latest", name="my-sb")
    assert sandbox.id == "abc-123"
    assert sandbox.name == "my-sb"
    assert sandbox.state == "Ready"


async def test_list_sandboxes(httpx_mock: HTTPXMock, client: KunoClient) -> None:
    httpx_mock.add_response(
        url="http://test:8080/api/v1/sandboxes",
        json=[
            {"id": "a", "name": "sb1", "state": "Ready"},
            {"id": "b", "name": "sb2", "state": "Stopped"},
        ],
    )
    sandboxes = await client.sandboxes.list()
    assert len(sandboxes) == 2
    assert sandboxes[0].id == "a"


async def test_list_sandboxes_with_state_filter(
    httpx_mock: HTTPXMock, client: KunoClient
) -> None:
    httpx_mock.add_response(
        url="http://test:8080/api/v1/sandboxes?state=Ready",
        json=[{"id": "a", "name": "sb1", "state": "Ready"}],
    )
    sandboxes = await client.sandboxes.list(state=SandboxState.READY)
    assert len(sandboxes) == 1


async def test_get_sandbox(httpx_mock: HTTPXMock, client: KunoClient) -> None:
    httpx_mock.add_response(
        url="http://test:8080/api/v1/sandboxes/abc-123",
        json={"id": "abc-123", "name": "sb1", "state": "Ready"},
    )
    sandbox = await client.sandboxes.get("abc-123")
    assert sandbox.id == "abc-123"


async def test_destroy_sandbox(httpx_mock: HTTPXMock, client: KunoClient) -> None:
    httpx_mock.add_response(
        url="http://test:8080/api/v1/sandboxes/abc-123",
        method="DELETE",
        status_code=204,
    )
    await client.sandboxes.destroy("abc-123")


async def test_exec_command(httpx_mock: HTTPXMock, client: KunoClient) -> None:
    httpx_mock.add_response(
        url="http://test:8080/api/v1/sandboxes",
        method="POST",
        json={"id": "sb1", "state": "Ready"},
        status_code=201,
    )
    httpx_mock.add_response(
        url="http://test:8080/api/v1/sandboxes/sb1/exec",
        method="POST",
        json={"stdout": "hello world\n", "stderr": "", "exit_code": 0, "duration_ms": 5},
    )
    sandbox = await client.sandboxes.create("alpine:latest")
    result = await sandbox.exec("echo", args=["hello", "world"])
    assert result.stdout == "hello world\n"
    assert result.exit_code == 0


async def test_upload_and_download(httpx_mock: HTTPXMock, client: KunoClient) -> None:
    httpx_mock.add_response(
        url="http://test:8080/api/v1/sandboxes",
        method="POST",
        json={"id": "sb1", "state": "Ready"},
        status_code=201,
    )
    httpx_mock.add_response(
        url="http://test:8080/api/v1/sandboxes/sb1/upload",
        method="POST",
        json={"success": True},
    )
    content = b"#!/bin/sh\necho hello"
    encoded = base64.b64encode(content).decode()
    httpx_mock.add_response(
        url="http://test:8080/api/v1/sandboxes/sb1/download?path=%2Ftmp%2Fscript.sh",
        json={"data": encoded},
    )
    sandbox = await client.sandboxes.create("alpine:latest")
    await sandbox.upload("/tmp/script.sh", content)
    downloaded = await sandbox.download("/tmp/script.sh")
    assert downloaded == content


async def test_pause_resume(httpx_mock: HTTPXMock, client: KunoClient) -> None:
    httpx_mock.add_response(
        url="http://test:8080/api/v1/sandboxes",
        method="POST",
        json={"id": "sb1", "state": "Ready"},
        status_code=201,
    )
    httpx_mock.add_response(
        url="http://test:8080/api/v1/sandboxes/sb1/pause",
        method="POST",
        status_code=204,
    )
    httpx_mock.add_response(
        url="http://test:8080/api/v1/sandboxes/sb1/resume",
        method="POST",
        status_code=204,
    )
    sandbox = await client.sandboxes.create("alpine:latest")
    await sandbox.pause()
    await sandbox.resume()


async def test_inspect_refreshes_state(httpx_mock: HTTPXMock, client: KunoClient) -> None:
    httpx_mock.add_response(
        url="http://test:8080/api/v1/sandboxes",
        method="POST",
        json={"id": "sb1", "state": "Created"},
        status_code=201,
    )
    httpx_mock.add_response(
        url="http://test:8080/api/v1/sandboxes/sb1",
        json={"id": "sb1", "state": "Ready"},
    )
    sandbox = await client.sandboxes.create("alpine:latest")
    assert sandbox.state == "Created"
    await sandbox.inspect()
    assert sandbox.state == "Ready"


async def test_sandbox_context_manager(httpx_mock: HTTPXMock, client: KunoClient) -> None:
    httpx_mock.add_response(
        url="http://test:8080/api/v1/sandboxes",
        method="POST",
        json={"id": "sb1", "state": "Ready"},
        status_code=201,
    )
    httpx_mock.add_response(
        url="http://test:8080/api/v1/sandboxes/sb1",
        method="DELETE",
        status_code=204,
    )
    sandbox = await client.sandboxes.create("alpine:latest")
    async with sandbox:
        assert sandbox.id == "sb1"
    # destroy was called via __aexit__


async def test_not_found_error(httpx_mock: HTTPXMock, client: KunoClient) -> None:
    httpx_mock.add_response(
        url="http://test:8080/api/v1/sandboxes/bad-id",
        json={"error": "sandbox not found"},
        status_code=404,
    )
    with pytest.raises(NotFoundError, match="sandbox not found"):
        await client.sandboxes.get("bad-id")


# ---------------------------------------------------------------------------
# Issue #1: Preset factory methods
# ---------------------------------------------------------------------------


def test_preset_images_dict() -> None:
    assert PRESET_IMAGES["python"] == "python:3.12-slim"
    assert PRESET_IMAGES["node"] == "node:22-slim"
    assert PRESET_IMAGES["ubuntu"] == "ubuntu:24.04"


async def test_preset_python(httpx_mock: HTTPXMock, client: KunoClient) -> None:
    httpx_mock.add_response(
        url="http://test:8080/api/v1/sandboxes",
        method="POST",
        json={"id": "py-1", "state": "Ready"},
        status_code=201,
    )
    sandbox = await client.sandboxes.python()
    assert sandbox.id == "py-1"
    request = httpx_mock.get_requests()[0]
    body = json.loads(request.content)
    assert body["image"] == "python:3.12-slim"


async def test_preset_node(httpx_mock: HTTPXMock, client: KunoClient) -> None:
    httpx_mock.add_response(
        url="http://test:8080/api/v1/sandboxes",
        method="POST",
        json={"id": "node-1", "state": "Ready"},
        status_code=201,
    )
    sandbox = await client.sandboxes.node()
    assert sandbox.id == "node-1"
    request = httpx_mock.get_requests()[0]
    body = json.loads(request.content)
    assert body["image"] == "node:22-slim"


async def test_preset_ubuntu(httpx_mock: HTTPXMock, client: KunoClient) -> None:
    httpx_mock.add_response(
        url="http://test:8080/api/v1/sandboxes",
        method="POST",
        json={"id": "ubu-1", "state": "Ready"},
        status_code=201,
    )
    sandbox = await client.sandboxes.ubuntu()
    assert sandbox.id == "ubu-1"
    request = httpx_mock.get_requests()[0]
    body = json.loads(request.content)
    assert body["image"] == "ubuntu:24.04"


async def test_preset_with_kwargs(httpx_mock: HTTPXMock, client: KunoClient) -> None:
    httpx_mock.add_response(
        url="http://test:8080/api/v1/sandboxes",
        method="POST",
        json={"id": "py-2", "state": "Ready"},
        status_code=201,
    )
    sandbox = await client.sandboxes.python(cpus=4, memory_mb=2048)
    assert sandbox.id == "py-2"
    request = httpx_mock.get_requests()[0]
    body = json.loads(request.content)
    assert body["image"] == "python:3.12-slim"
    assert body["cpus"] == 4
    assert body["memory_mb"] == 2048


# ---------------------------------------------------------------------------
# Issue #2: sandbox.run() convenience method
# ---------------------------------------------------------------------------


async def test_run_success(httpx_mock: HTTPXMock, client: KunoClient) -> None:
    httpx_mock.add_response(
        url="http://test:8080/api/v1/sandboxes",
        method="POST",
        json={"id": "sb1", "state": "Ready"},
        status_code=201,
    )
    httpx_mock.add_response(
        url="http://test:8080/api/v1/sandboxes/sb1/exec",
        method="POST",
        json={"stdout": "hello\n", "stderr": "", "exit_code": 0, "duration_ms": 3},
    )
    sandbox = await client.sandboxes.create("alpine:latest")
    output = await sandbox.run('echo "hello"')
    assert output == "hello\n"


async def test_run_with_interpreter(httpx_mock: HTTPXMock, client: KunoClient) -> None:
    httpx_mock.add_response(
        url="http://test:8080/api/v1/sandboxes",
        method="POST",
        json={"id": "sb1", "state": "Ready"},
        status_code=201,
    )
    httpx_mock.add_response(
        url="http://test:8080/api/v1/sandboxes/sb1/exec",
        method="POST",
        json={"stdout": "hello\n", "stderr": "", "exit_code": 0, "duration_ms": 3},
    )
    sandbox = await client.sandboxes.create("alpine:latest")
    output = await sandbox.run('print("hello")', interpreter="python3")
    assert output == "hello\n"
    # Verify the interpreter was sent as the command
    request = httpx_mock.get_requests()[1]
    body = json.loads(request.content)
    assert body["cmd"] == "python3"
    assert body["args"] == ["-c", 'print("hello")']


async def test_run_raises_exec_error(httpx_mock: HTTPXMock, client: KunoClient) -> None:
    httpx_mock.add_response(
        url="http://test:8080/api/v1/sandboxes",
        method="POST",
        json={"id": "sb1", "state": "Ready"},
        status_code=201,
    )
    httpx_mock.add_response(
        url="http://test:8080/api/v1/sandboxes/sb1/exec",
        method="POST",
        json={"stdout": "", "stderr": "command not found\n", "exit_code": 127, "duration_ms": 1},
    )
    sandbox = await client.sandboxes.create("alpine:latest")
    with pytest.raises(ExecError, match="command not found") as exc_info:
        await sandbox.run("badcmd")
    assert exc_info.value.exit_code == 127
    assert exc_info.value.stderr == "command not found\n"
    assert exc_info.value.stdout == ""


# ---------------------------------------------------------------------------
# Issue #5: Future-proof CreateSandboxRequest fields
# ---------------------------------------------------------------------------


async def test_create_with_new_fields(httpx_mock: HTTPXMock, client: KunoClient) -> None:
    httpx_mock.add_response(
        url="http://test:8080/api/v1/sandboxes",
        method="POST",
        json={"id": "sb1", "state": "Ready"},
        status_code=201,
    )
    sandbox = await client.sandboxes.create(
        "alpine:latest",
        volumes=["/data:/data"],
        ports=["8080:80"],
        shell="/bin/zsh",
        scripts={"setup": "apt-get update"},
    )
    assert sandbox.id == "sb1"
    request = httpx_mock.get_requests()[0]
    body = json.loads(request.content)
    assert body["volumes"] == ["/data:/data"]
    assert body["ports"] == ["8080:80"]
    assert body["shell"] == "/bin/zsh"
    assert body["scripts"] == {"setup": "apt-get update"}


async def test_new_fields_excluded_when_none(
    httpx_mock: HTTPXMock, client: KunoClient
) -> None:
    httpx_mock.add_response(
        url="http://test:8080/api/v1/sandboxes",
        method="POST",
        json={"id": "sb1", "state": "Ready"},
        status_code=201,
    )
    await client.sandboxes.create("alpine:latest")
    request = httpx_mock.get_requests()[0]
    body = json.loads(request.content)
    assert "volumes" not in body
    assert "ports" not in body
    assert "shell" not in body
    assert "scripts" not in body
