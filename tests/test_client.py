"""Tests for KunoClient construction, auth, and health endpoints."""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

from kuno_sandbox import KunoClient


async def test_client_context_manager(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="http://test:8080/healthz", text="ok")
    async with KunoClient(base_url="http://test:8080") as client:
        result = await client.health()
    assert result == "ok"


async def test_health(httpx_mock: HTTPXMock, client: KunoClient) -> None:
    httpx_mock.add_response(url="http://test:8080/healthz", text="ok")
    assert await client.health() == "ok"


async def test_ready(httpx_mock: HTTPXMock, client: KunoClient) -> None:
    httpx_mock.add_response(url="http://test:8080/readyz", text="ready")
    assert await client.ready() == "ready"


async def test_metrics(httpx_mock: HTTPXMock, client: KunoClient) -> None:
    httpx_mock.add_response(url="http://test:8080/metrics", text="# HELP up\nup 1")
    result = await client.metrics()
    assert "up 1" in result


async def test_pool(httpx_mock: HTTPXMock, client: KunoClient) -> None:
    httpx_mock.add_response(
        url="http://test:8080/api/v1/pool/status",
        json={"available": True, "message": "5 warm VMs"},
    )
    pool = await client.pool()
    assert pool.available is True
    assert pool.message == "5 warm VMs"


async def test_auth_header_sent(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="http://test:8080/healthz", text="ok")
    client = KunoClient(base_url="http://test:8080", token="my-secret")
    await client.health()
    request = httpx_mock.get_requests()[0]
    assert request.headers["authorization"] == "Bearer my-secret"
    await client.aclose()


async def test_no_auth_header_when_no_token(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="http://test:8080/healthz", text="ok")
    client = KunoClient(base_url="http://test:8080")
    await client.health()
    request = httpx_mock.get_requests()[0]
    assert "authorization" not in request.headers
    await client.aclose()


async def test_env_var_config(httpx_mock: HTTPXMock, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KUNO_BASE_URL", "http://env:9090")
    monkeypatch.setenv("KUNO_AUTH_TOKEN", "env-token")
    httpx_mock.add_response(url="http://env:9090/healthz", text="ok")
    client = KunoClient()
    await client.health()
    request = httpx_mock.get_requests()[0]
    assert request.headers["authorization"] == "Bearer env-token"
    await client.aclose()
