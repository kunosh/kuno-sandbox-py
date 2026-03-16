"""Shared test fixtures."""

from __future__ import annotations

import pytest

from kuno_sandbox import KunoClient


@pytest.fixture
def client(httpx_mock):  # type: ignore[no-untyped-def]
    """Create a KunoClient pointing at a mocked httpx backend."""
    return KunoClient(base_url="http://test:8080", token="test-token")
