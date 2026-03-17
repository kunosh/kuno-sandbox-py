"""Exception hierarchy for the Kuno Sandbox SDK."""

from __future__ import annotations

import json as _json
from collections.abc import Callable


class KunoError(Exception):
    """Base error for all Kuno SDK errors."""


class ApiError(KunoError):
    """HTTP API error with status code."""

    status: int

    def __init__(self, status: int, message: str, hint: str | None = None) -> None:
        self.status = status
        self.message = message
        self.hint = hint
        parts = [f"[{status}] {message}"]
        if hint:
            parts.append(f"Hint: {hint}")
        super().__init__(" — ".join(parts))


class BadRequestError(ApiError):
    """400 Bad Request."""

    def __init__(self, message: str, hint: str | None = None) -> None:
        super().__init__(400, message, hint)


class AuthError(ApiError):
    """401 Unauthorized."""

    def __init__(self, message: str, hint: str | None = None) -> None:
        super().__init__(401, message, hint)


class NotFoundError(ApiError):
    """404 Not Found."""

    def __init__(self, message: str, hint: str | None = None) -> None:
        super().__init__(404, message, hint)


class ConflictError(ApiError):
    """409 Conflict."""

    def __init__(self, message: str, hint: str | None = None) -> None:
        super().__init__(409, message, hint)


class GoneError(ApiError):
    """410 Gone."""

    def __init__(self, message: str, hint: str | None = None) -> None:
        super().__init__(410, message, hint)


class RateLimitError(ApiError):
    """429 Too Many Requests."""

    def __init__(self, message: str, hint: str | None = None) -> None:
        super().__init__(429, message, hint)


class ServerError(ApiError):
    """500+ Server Error."""

    def __init__(self, message: str, hint: str | None = None, status: int = 500) -> None:
        super().__init__(status, message, hint)


class NetworkError(KunoError):
    """Network / connection error."""


class TimeoutError(KunoError):  # noqa: A001
    """Request timeout."""


class StreamError(KunoError):
    """SSE streaming error."""


class ExecError(KunoError):
    """Command execution returned a non-zero exit code."""

    exit_code: int
    stdout: str
    stderr: str

    def __init__(self, exit_code: int, stdout: str, stderr: str) -> None:
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        message = f"Command failed with exit code {exit_code}"
        if stderr.strip():
            message += f": {stderr.strip()}"
        super().__init__(message)


_STATUS_MAP: dict[int, Callable[[str, str | None], ApiError]] = {
    400: BadRequestError,
    401: AuthError,
    404: NotFoundError,
    409: ConflictError,
    410: GoneError,
    429: RateLimitError,
}


def error_from_response(status: int, body: str) -> ApiError:
    """Map an HTTP status code + body to the appropriate error."""
    message = body
    hint: str | None = None
    try:
        parsed = _json.loads(body)
        if isinstance(parsed, dict):
            message = parsed.get("error", body)
            hint = parsed.get("hint")
    except (_json.JSONDecodeError, TypeError):
        pass

    factory = _STATUS_MAP.get(status)
    if factory is not None:
        return factory(message, hint)
    return ServerError(message, hint, status=status)
