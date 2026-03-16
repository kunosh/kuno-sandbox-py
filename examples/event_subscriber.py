"""
Event Subscriber — persistent SSE connection across multiple turns.

This demonstrates using subscribe_events() to receive all events from a
session, even across multiple send_message() calls. Useful for building
UIs that need a single event stream.

Usage:
    KUNO_BASE_URL=http://localhost:8080 \
    ANTHROPIC_API_KEY=sk-ant-... \
    python examples/event_subscriber.py
"""

import asyncio
import os

from kuno_sandbox import (
    AgentKind,
    ErrorEvent,
    KunoClient,
    TextEvent,
    TurnCompleteEvent,
)


async def main() -> None:
    async with KunoClient() as client:
        session = await client.agents.create_session(
            agent=AgentKind.CLAUDE_CODE,
            env={"ANTHROPIC_API_KEY": os.environ["ANTHROPIC_API_KEY"]},
        )

        # Start a persistent event subscription in the background
        turn_count = 0

        async def subscriber() -> None:
            nonlocal turn_count
            async for event in await session.subscribe_events():
                match event.kind:
                    case TextEvent(content=text):
                        print(text, end="")
                    case TurnCompleteEvent():
                        turn_count += 1
                        print(f"\n--- Turn {turn_count} complete ---")
                    case ErrorEvent(message=msg):
                        print(f"Error: {msg}")

        # Run subscriber in background
        sub_task = asyncio.create_task(subscriber())

        # Send multiple messages — all events arrive on the subscriber
        # (Using raw HTTP here since send_message would also stream)
        import httpx

        base = os.environ.get("KUNO_BASE_URL", "http://localhost:8080")
        async with httpx.AsyncClient() as http:
            await http.post(
                f"{base}/api/v1/agents/sessions/{session.id}/messages",
                json={"message": "What is 2 + 2?"},
            )
            await asyncio.sleep(5)

            await http.post(
                f"{base}/api/v1/agents/sessions/{session.id}/messages",
                json={"message": "Now multiply that by 10"},
            )
            await asyncio.sleep(5)

        sub_task.cancel()
        await session.destroy()
        print("\nSession destroyed.")


if __name__ == "__main__":
    asyncio.run(main())
