"""Tests for sandbox CRUD, exec, files, pause/resume, and error handling."""

from __future__ import annotations

import base64

import pytest
from pytest_httpx import HTTPXMock

from kuno_sandbox import (
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
