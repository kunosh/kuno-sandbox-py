"""
Agent Session — stream a multi-turn conversation with Claude Code.

Usage:
    KUNO_BASE_URL=http://localhost:8080 \
    ANTHROPIC_API_KEY=sk-ant-... \
    python examples/agent_session.py
"""

import asyncio
import os

from kuno_sandbox import (
    AgentKind,
    FileChangeEvent,
    KunoClient,
    TextEvent,
    ToolUseEvent,
    TurnCompleteEvent,
)


async def main() -> None:
    async with KunoClient() as client:
        session = await client.agents.create_session(
            agent=AgentKind.CLAUDE_CODE,
            env={"ANTHROPIC_API_KEY": os.environ["ANTHROPIC_API_KEY"]},
        )
        print(f"Session created: {session.id} ({session.state})")

        # Turn 1
        print("\n--- Turn 1 ---")
        async for event in await session.send_message(
            "Create a Python hello world script at /tmp/hello.py"
        ):
            match event.kind:
                case TextEvent(content=text):
                    print(text, end="")
                case ToolUseEvent(tool=tool):
                    print(f"\n[tool] {tool}")
                case FileChangeEvent(path=path, operation=op):
                    print(f"\n[file] {op.value}: {path}")
                case TurnCompleteEvent():
                    print("\n[turn complete]")

        # Turn 2 — agent remembers context
        print("\n--- Turn 2 ---")
        async for event in await session.send_message("Now add a unit test for it"):
            match event.kind:
                case TextEvent(content=text):
                    print(text, end="")
                case TurnCompleteEvent(usage=usage):
                    print("\n[turn complete]")
                    if usage:
                        print(
                            f"Tokens: {usage.input_tokens}in / "
                            f"{usage.output_tokens}out"
                        )

        await session.destroy()
        print("Session destroyed.")


if __name__ == "__main__":
    asyncio.run(main())
