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
        session = await client.agents.create_session(
            agent=AgentKind.CLAUDE_CODE,
            env={"ANTHROPIC_API_KEY": "..."},
        )

        async for event in await session.send_message("Create a hello world HTTP server"):
            match event.kind:
                case TextEvent(content=text):
                    print(text, end="")
                case ToolUseEvent(tool=tool):
                    print(f"\nUsing tool: {tool}")
                case TurnCompleteEvent():
                    print("\nDone!")

        await session.destroy()

asyncio.run(main())
```

## Configuration

```python
client = KunoClient(
    base_url="http://localhost:8080",  # or KUNO_BASE_URL env var
    token="my-auth-token",             # or KUNO_AUTH_TOKEN env var
    timeout=30.0,                      # request timeout in seconds (default: 30)
)
```

| Parameter | Env Var | Default |
|-----------|---------|---------|
| `base_url` | `KUNO_BASE_URL` | `http://localhost:8080` |
| `token` | `KUNO_AUTH_TOKEN` | `None` (no auth) |
| `timeout` | — | `30.0` |

## API Reference

### KunoClient

The main entry point. Use as an async context manager.

```python
async with KunoClient() as client:
    client.sandboxes   # SandboxResource — CRUD operations
    client.agents      # AgentResource — session management

    await client.health()   # → 'ok'
    await client.ready()    # → 'ready'
    await client.metrics()  # → Prometheus text format
    await client.pool()     # → PoolStatus(available, message)
```

### Sandboxes

Create and manage isolated MicroVM sandboxes.

```python
# Create a sandbox
sandbox = await client.sandboxes.create(
    "python:3.12-slim",
    name="my-sandbox",          # optional
    cpus=2,                      # optional (default: 1)
    memory_mb=512,               # optional (default: 256)
    env={"PYTHONPATH": "/app"},  # optional
    workdir="/app",              # optional
)

# List / get / destroy
all_sandboxes = await client.sandboxes.list()
ready_only = await client.sandboxes.list(state=SandboxState.READY)
sandbox = await client.sandboxes.get("sandbox-id")
await client.sandboxes.destroy("sandbox-id")
```

### Sandbox Instance

Returned by `create()` and `get()`. Supports `async with` for auto-cleanup.

```python
# Execute commands
result = await sandbox.exec("python3", args=["-c", "print('hello')"])
print(result.stdout)      # "hello\n"
print(result.exit_code)   # 0
print(result.duration_ms) # execution time

# Stream command output
async for event in await sandbox.exec_stream("pip", args=["install", "flask"]):
    match event:
        case ExecChunkEvent(stream=stream, data=data):
            print(f"[{stream}] {data}", end="")
        case ExecExitEvent(exit_code=code):
            print(f"Exit: {code}")

# File operations
await sandbox.upload("/app/main.py", b'print("hello")')
await sandbox.upload("/app/main.py", 'print("hello")')  # str also accepted
data = await sandbox.download("/app/main.py")  # → bytes

# Lifecycle
await sandbox.pause()
await sandbox.resume()
await sandbox.inspect()  # re-fetch state
await sandbox.destroy()

# Auto-cleanup with async with
async with await client.sandboxes.create("alpine:latest") as sandbox:
    await sandbox.exec("echo", args=["hello"])
# sandbox destroyed automatically
```

### Agent Sessions

Create AI coding agent sessions with SSE streaming.

```python
# Create a session
session = await client.agents.create_session(
    agent=AgentKind.CLAUDE_CODE,
    label="my-session",                      # optional
    image="node:22-slim",                    # optional (adapter default)
    cpus=2,                                  # optional
    memory_mb=4096,                          # optional
    env={"ANTHROPIC_API_KEY": "..."},        # required for Claude Code
    agent_config=AgentConfig(                # optional
        model="claude-sonnet-4-20250514",
        extra_args=["--verbose"],
    ),
)

# List / get / destroy
sessions = await client.agents.list_sessions()
s = await client.agents.get_session("session-id")
await client.agents.destroy_session("session-id")
```

### AgentSession Instance

Returned by `create_session()` and `get_session()`. Supports `async with`.

```python
# Send a message — streams events until turn completes
async for event in await session.send_message("Fix the bug in auth.py"):
    match event.kind:
        case ThinkingEvent():
            pass  # agent is thinking
        case TextEvent(content=text, is_delta=delta):
            print(text, end="" if delta else "\n")
        case ToolUseEvent(tool=tool, tool_use_id=tid):
            print(f"Tool: {tool} (id: {tid})")
        case ToolResultEvent(success=ok, output=out):
            print(f"Result: {'ok' if ok else 'fail'}")
        case FileChangeEvent(path=path, operation=op):
            print(f"{op.value}: {path}")
        case TurnCompleteEvent(usage=usage):
            if usage:
                print(f"Tokens: {usage.input_tokens}in/{usage.output_tokens}out")
        case ErrorEvent(message=msg):
            print(f"Error: {msg}")
        case ExitEvent(exit_code=code):
            print(f"Agent exited: {code}")

# Subscribe to events across multiple turns (persistent connection)
events_stream = await session.subscribe_events()
# In parallel, send messages — events arrive on the subscription

# File operations (via the session's underlying sandbox)
await session.upload("/workspace/data.json", b'{"key": "value"}')
data = await session.download("/workspace/output.txt")

# Lifecycle
await session.inspect()
await session.destroy()
```

### Multi-Turn Conversations

Sessions maintain conversation context across multiple `send_message` calls:

```python
async with KunoClient() as client:
    session = await client.agents.create_session(
        agent=AgentKind.CLAUDE_CODE,
        env={"ANTHROPIC_API_KEY": os.environ["ANTHROPIC_API_KEY"]},
    )

    # Turn 1
    async for event in await session.send_message("Create a Flask app with /health endpoint"):
        if isinstance(event.kind, TextEvent):
            print(event.kind.content, end="")

    # Turn 2 — agent remembers the previous context
    async for event in await session.send_message("Add a /users endpoint with CRUD"):
        if isinstance(event.kind, TextEvent):
            print(event.kind.content, end="")

    # Turn 3
    async for event in await session.send_message("Write tests for all endpoints"):
        if isinstance(event.kind, TextEvent):
            print(event.kind.content, end="")

    await session.destroy()
```

## Event Types

All agent events are wrapped in `UniversalEvent`:

```python
class UniversalEvent:
    session_id: str
    kind: EventKind     # discriminated union
    timestamp: str      # ISO 8601
```

| Event Type | Fields | Terminal? |
|-----------|--------|-----------|
| `ThinkingEvent` | — | No |
| `TextEvent` | `content`, `is_delta` | No |
| `ToolUseEvent` | `tool`, `input`, `tool_use_id` | No |
| `ToolResultEvent` | `tool_use_id`, `output`, `success` | No |
| `FileChangeEvent` | `path`, `diff`, `operation` | No |
| `TurnCompleteEvent` | `stop_reason`, `usage` | Yes |
| `ErrorEvent` | `message`, `code` | Yes |
| `ExitEvent` | `exit_code` | Yes |
| `RawEvent` | `stream`, `content` | No |

`send_message()` automatically stops when a terminal event is received. `subscribe_events()` does not stop on `turn_complete`.

You can use either `match`/`case` (Python 3.10+) or `isinstance` checks:

```python
# Pattern matching (recommended)
match event.kind:
    case TextEvent(content=text):
        print(text)
    case TurnCompleteEvent():
        print("Done")

# isinstance checks
if isinstance(event.kind, TextEvent):
    print(event.kind.content)
```

## Error Handling

All errors extend `KunoError`:

```python
from kuno_sandbox import KunoError, ApiError, NotFoundError, ConflictError

try:
    async for event in await session.send_message("hello"):
        ...
except ConflictError:
    # 409 — session is busy (not in idle state)
    print("Session is still processing, wait for turn to complete")
except NotFoundError:
    # 404 — session doesn't exist
    pass
except ApiError as e:
    # Any HTTP error
    print(e.status, e.message, e.hint)
```

| Error Class | Status | When |
|------------|--------|------|
| `BadRequestError` | 400 | Invalid request body |
| `AuthError` | 401 | Missing/invalid token |
| `NotFoundError` | 404 | Resource doesn't exist |
| `ConflictError` | 409 | Session not idle |
| `GoneError` | 410 | Session already destroyed |
| `RateLimitError` | 429 | Session limit reached |
| `ServerError` | 500+ | Internal server error |
| `NetworkError` | — | Connection failure |
| `TimeoutError` | — | Request timed out |
| `StreamError` | — | SSE parsing failure |

## Supported Agents

| Agent | `AgentKind` | Required Env Vars |
|-------|------------|-------------------|
| Claude Code | `CLAUDE_CODE` | `ANTHROPIC_API_KEY` |
| Codex | `CODEX` | `OPENAI_API_KEY` |
| OpenCode | `OPEN_CODE` | `ANTHROPIC_API_KEY` |
| Aider | `AIDER` | `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` |
| Goose | `GOOSE` | `ANTHROPIC_API_KEY` |

## Type Safety

This package ships with full type annotations and a `py.typed` PEP 561 marker. Enable strict mypy:

```toml
# pyproject.toml
[tool.mypy]
strict = true
```

## License

MIT
