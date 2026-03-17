"""Tests for the synchronous client wrapper."""

from __future__ import annotations

import json

import pytest
from pytest_httpx import HTTPXMock

from kuno_sandbox import ExecError, SyncKunoClient
from kuno_sandbox.sync import SyncSandbox


@pytest.fixture
def sync_client(httpx_mock: HTTPXMock) -> SyncKunoClient:  # type: ignore[no-untyped-def]
    """Create a SyncKunoClient pointing at a mocked httpx backend."""
    return SyncKunoClient(base_url="http://test:8080", token="test-token")


def test_sync_client_context_manager(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="http://test:8080/healthz", text="ok")
    with SyncKunoClient(base_url="http://test:8080") as client:
        result = client.health()
    assert result == "ok"


def test_sync_health(httpx_mock: HTTPXMock, sync_client: SyncKunoClient) -> None:
    httpx_mock.add_response(url="http://test:8080/healthz", text="ok")
    assert sync_client.health() == "ok"
    sync_client.close()


def test_sync_create_sandbox(httpx_mock: HTTPXMock, sync_client: SyncKunoClient) -> None:
    httpx_mock.add_response(
        url="http://test:8080/api/v1/sandboxes",
        method="POST",
        json={"id": "sb1", "name": "test", "state": "Ready"},
        status_code=201,
    )
    sandbox = sync_client.sandboxes.create("alpine:latest", name="test")
    assert isinstance(sandbox, SyncSandbox)
    assert sandbox.id == "sb1"
    assert sandbox.name == "test"
    sync_client.close()


def test_sync_sandbox_exec(httpx_mock: HTTPXMock, sync_client: SyncKunoClient) -> None:
    httpx_mock.add_response(
        url="http://test:8080/api/v1/sandboxes",
        method="POST",
        json={"id": "sb1", "state": "Ready"},
        status_code=201,
    )
    httpx_mock.add_response(
        url="http://test:8080/api/v1/sandboxes/sb1/exec",
        method="POST",
        json={"stdout": "hello\n", "stderr": "", "exit_code": 0, "duration_ms": 2},
    )
    sandbox = sync_client.sandboxes.create("alpine:latest")
    result = sandbox.exec("echo", args=["hello"])
    assert result.stdout == "hello\n"
    assert result.exit_code == 0
    sync_client.close()


def test_sync_sandbox_run(httpx_mock: HTTPXMock, sync_client: SyncKunoClient) -> None:
    httpx_mock.add_response(
        url="http://test:8080/api/v1/sandboxes",
        method="POST",
        json={"id": "sb1", "state": "Ready"},
        status_code=201,
    )
    httpx_mock.add_response(
        url="http://test:8080/api/v1/sandboxes/sb1/exec",
        method="POST",
        json={"stdout": "42\n", "stderr": "", "exit_code": 0, "duration_ms": 1},
    )
    sandbox = sync_client.sandboxes.create("alpine:latest")
    output = sandbox.run('echo "42"')
    assert output == "42\n"
    sync_client.close()


def test_sync_sandbox_run_raises_exec_error(
    httpx_mock: HTTPXMock, sync_client: SyncKunoClient
) -> None:
    httpx_mock.add_response(
        url="http://test:8080/api/v1/sandboxes",
        method="POST",
        json={"id": "sb1", "state": "Ready"},
        status_code=201,
    )
    httpx_mock.add_response(
        url="http://test:8080/api/v1/sandboxes/sb1/exec",
        method="POST",
        json={"stdout": "", "stderr": "fail\n", "exit_code": 1, "duration_ms": 1},
    )
    sandbox = sync_client.sandboxes.create("alpine:latest")
    with pytest.raises(ExecError, match="fail"):
        sandbox.run("bad")
    sync_client.close()


def test_sync_preset_python(httpx_mock: HTTPXMock, sync_client: SyncKunoClient) -> None:
    httpx_mock.add_response(
        url="http://test:8080/api/v1/sandboxes",
        method="POST",
        json={"id": "py-1", "state": "Ready"},
        status_code=201,
    )
    sandbox = sync_client.sandboxes.python()
    assert sandbox.id == "py-1"
    request = httpx_mock.get_requests()[0]
    body = json.loads(request.content)
    assert body["image"] == "python:3.12-slim"
    sync_client.close()


def test_sync_sandbox_context_manager(
    httpx_mock: HTTPXMock, sync_client: SyncKunoClient
) -> None:
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
    sandbox = sync_client.sandboxes.create("alpine:latest")
    with sandbox:
        assert sandbox.id == "sb1"
    # destroy called via __exit__
    sync_client.close()


def test_sync_list_sandboxes(httpx_mock: HTTPXMock, sync_client: SyncKunoClient) -> None:
    httpx_mock.add_response(
        url="http://test:8080/api/v1/sandboxes",
        json=[
            {"id": "a", "name": "sb1", "state": "Ready"},
            {"id": "b", "name": "sb2", "state": "Stopped"},
        ],
    )
    result = sync_client.sandboxes.list()
    assert len(result) == 2
    sync_client.close()


def test_sync_get_sandbox(httpx_mock: HTTPXMock, sync_client: SyncKunoClient) -> None:
    httpx_mock.add_response(
        url="http://test:8080/api/v1/sandboxes/sb1",
        json={"id": "sb1", "state": "Ready"},
    )
    sandbox = sync_client.sandboxes.get("sb1")
    assert isinstance(sandbox, SyncSandbox)
    assert sandbox.id == "sb1"
    sync_client.close()


def test_sync_destroy_sandbox(httpx_mock: HTTPXMock, sync_client: SyncKunoClient) -> None:
    httpx_mock.add_response(
        url="http://test:8080/api/v1/sandboxes/sb1",
        method="DELETE",
        status_code=204,
    )
    sync_client.sandboxes.destroy("sb1")
    sync_client.close()
