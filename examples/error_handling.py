"""
Error Handling — demonstrates catching and handling SDK errors.

Usage:
    KUNO_BASE_URL=http://localhost:8080 python examples/error_handling.py
"""

import asyncio

from kuno_sandbox import (
    AgentKind,
    ApiError,
    ConflictError,
    KunoClient,
    NetworkError,
    NotFoundError,
    RateLimitError,
)


async def main() -> None:
    client = KunoClient()

    # 1. Handle connection errors
    try:
        bad_client = KunoClient(base_url="http://localhost:99999")
        await bad_client.health()
    except NetworkError as e:
        print(f"Network error (expected): {e}")

    # 2. Handle 404 — resource not found
    try:
        await client.sandboxes.get("nonexistent-id")
    except NotFoundError as e:
        print(f"Not found (expected): {e}")

    # 3. Handle 409 — conflict (session not idle)
    try:
        session = await client.agents.create_session(
            agent=AgentKind.CLAUDE_CODE,
            env={"ANTHROPIC_API_KEY": "test"},
        )
        await session.destroy()
    except ConflictError as e:
        print(f"Conflict: {e}")
    except RateLimitError as e:
        print(f"Rate limited: {e}")
    except ApiError as e:
        print(f"API error [{e.status}]: {e.message}")

    # 4. Catch-all with the error hierarchy
    try:
        await client.sandboxes.get("bad-id")
    except ApiError as e:
        # All HTTP errors have: status, message, hint
        print(f"Status: {e.status}, Message: {e.message}, Hint: {e.hint or 'none'}")

    await client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
