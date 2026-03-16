"""Tests for error mapping from HTTP status codes."""

from __future__ import annotations

from kuno_sandbox.errors import (
    ApiError,
    AuthError,
    BadRequestError,
    ConflictError,
    GoneError,
    KunoError,
    RateLimitError,
    ServerError,
    error_from_response,
)


def test_400_bad_request() -> None:
    err = error_from_response(400, '{"error": "invalid image"}')
    assert isinstance(err, BadRequestError)
    assert err.status == 400
    assert "invalid image" in str(err)


def test_401_auth_error() -> None:
    err = error_from_response(401, '{"error": "missing token"}')
    assert isinstance(err, AuthError)
    assert err.status == 401


def test_404_not_found() -> None:
    err = error_from_response(404, '{"error": "sandbox not found"}')
    from kuno_sandbox.errors import NotFoundError

    assert isinstance(err, NotFoundError)
    assert err.status == 404


def test_409_conflict() -> None:
    err = error_from_response(409, '{"error": "session busy"}')
    assert isinstance(err, ConflictError)
    assert err.status == 409


def test_410_gone() -> None:
    err = error_from_response(410, '{"error": "session destroyed"}')
    assert isinstance(err, GoneError)
    assert err.status == 410


def test_429_rate_limit() -> None:
    err = error_from_response(429, '{"error": "too many sessions", "hint": "max 10"}')
    assert isinstance(err, RateLimitError)
    assert err.status == 429
    assert err.hint == "max 10"


def test_500_server_error() -> None:
    err = error_from_response(500, '{"error": "internal error"}')
    assert isinstance(err, ServerError)
    assert err.status == 500


def test_502_maps_to_server_error() -> None:
    err = error_from_response(502, '{"error": "bad gateway"}')
    assert isinstance(err, ServerError)
    assert err.status == 502


def test_plain_text_body() -> None:
    err = error_from_response(500, "plain text error")
    assert isinstance(err, ServerError)
    assert "plain text error" in str(err)


def test_error_hierarchy() -> None:
    err = error_from_response(400, '{"error": "bad"}')
    assert isinstance(err, BadRequestError)
    assert isinstance(err, ApiError)
    assert isinstance(err, KunoError)
    assert isinstance(err, Exception)


def test_hint_in_message() -> None:
    err = error_from_response(429, '{"error": "limit", "hint": "try later"}')
    assert "try later" in str(err)
