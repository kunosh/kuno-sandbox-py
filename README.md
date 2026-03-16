# kuno-sandbox

Python SDK for the [Kuno Sandbox](https://github.com/kunosh/kuno-sandbox) API — run AI coding agents in secure, isolated microVMs.

## Install

```bash
pip install kuno-sandbox
```

## Quick Start

```python
import asyncio
from kuno_sandbox import KunoClient, AgentKind

async def main():
    async with KunoClient(base_url="http://localhost:8080") as client:
        # Create a sandbox
        sandbox = await client.sandboxes.create("alpine:latest")
        result = await sandbox.exec("echo", args=["hello"])
        print(result.stdout)
        await sandbox.destroy()

        # Or use an agent session
        session = await client.agents.create_session(
            agent=AgentKind.CLAUDE_CODE,
            env={"ANTHROPIC_API_KEY": "..."},
        )
        async for event in await session.send_message("Fix the bug"):
            print(event.kind)
        await session.destroy()

asyncio.run(main())
```

## License

MIT
