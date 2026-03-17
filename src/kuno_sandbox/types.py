"""Type definitions for the Kuno Sandbox SDK."""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class AgentKind(str, Enum):
    CLAUDE_CODE = "claude-code"
    CODEX = "codex"
    OPEN_CODE = "open-code"
    AIDER = "aider"
    GOOSE = "goose"


class SessionState(str, Enum):
    CREATING = "creating"
    IDLE = "idle"
    PROCESSING = "processing"
    ERROR = "error"
    DESTROYED = "destroyed"


class SandboxState(str, Enum):
    CREATED = "Created"
    READY = "Ready"
    BUSY = "Busy"
    COMPACTING = "Compacting"
    STOPPED = "Stopped"


class FileOperation(str, Enum):
    CREATE = "create"
    MODIFY = "modify"
    DELETE = "delete"


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class AgentConfig(BaseModel):
    model: str | None = None
    extra_args: list[str] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)


class CreateSandboxRequest(BaseModel):
    image: str
    name: str | None = None
    cpus: int | None = None
    memory_mb: int | None = None
    env: dict[str, str] | None = None
    workdir: str | None = None
    volumes: list[str] | None = None
    ports: list[str] | None = None
    shell: str | None = None
    scripts: dict[str, str] | None = None


class SandboxInfo(BaseModel):
    id: str
    name: str | None = None
    state: str | None = None


class ExecOptions(BaseModel):
    args: list[str] = Field(default_factory=list)
    env: list[str] = Field(default_factory=list)
    working_dir: str | None = None


class ExecResponse(BaseModel):
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    duration_ms: int = 0


class CreateSessionRequest(BaseModel):
    agent: AgentKind
    label: str | None = None
    image: str | None = None
    cpus: int | None = None
    memory_mb: int | None = None
    env: dict[str, str] | None = None
    agent_config: AgentConfig | None = None


class SessionUsage(BaseModel):
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    turn_count: int = 0


class SessionInfo(BaseModel):
    id: str
    agent_kind: str | None = None
    label: str | None = None
    state: str | None = None
    created_at: str | None = None
    agent_session_id: str | None = None
    usage: SessionUsage | None = None


class UsageInfo(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0


class PoolStatus(BaseModel):
    available: bool = False
    message: str = ""


class FileResponse(BaseModel):
    success: bool = True
    error: str | None = None


class DownloadResponse(BaseModel):
    data: str = ""


# ---------------------------------------------------------------------------
# Snapshot types
# ---------------------------------------------------------------------------


class SnapshotInfo(BaseModel):
    id: str
    name: str
    source_sandbox_id: str
    image: str
    size_bytes: int
    created_at: str
    description: str = ""


class CreateSnapshotRequest(BaseModel):
    name: str | None = None
    description: str | None = None


class HibernateResponse(BaseModel):
    session_id: str
    snapshot_id: str
    status: str


class ResumeResponse(BaseModel):
    session_id: str
    snapshot_id: str
    status: str


# ---------------------------------------------------------------------------
# REPL types
# ---------------------------------------------------------------------------


class ReplOutputChunk(BaseModel):
    stream: str
    text: str


class ReplResponse(BaseModel):
    output: list[ReplOutputChunk] = Field(default_factory=list)
    exit_code: int = 0
    duration_ms: int = 0


# ---------------------------------------------------------------------------
# Event kinds (discriminated union via "type" field)
# ---------------------------------------------------------------------------


class ThinkingEvent(BaseModel):
    type: Literal["thinking"] = "thinking"


class TextEvent(BaseModel):
    type: Literal["text"] = "text"
    content: str = ""
    is_delta: bool = False


class ToolUseEvent(BaseModel):
    type: Literal["tool_use"] = "tool_use"
    tool: str = ""
    input: Any = None
    tool_use_id: str | None = None


class ToolResultEvent(BaseModel):
    type: Literal["tool_result"] = "tool_result"
    tool_use_id: str = ""
    output: str = ""
    success: bool = True


class FileChangeEvent(BaseModel):
    type: Literal["file_change"] = "file_change"
    path: str = ""
    diff: str | None = None
    operation: FileOperation = FileOperation.MODIFY


class TurnCompleteEvent(BaseModel):
    type: Literal["turn_complete"] = "turn_complete"
    stop_reason: str | None = None
    usage: UsageInfo | None = None


class ErrorEvent(BaseModel):
    type: Literal["error"] = "error"
    message: str = ""
    code: str | None = None


class ExitEvent(BaseModel):
    type: Literal["exit"] = "exit"
    exit_code: int = 0


class RawEvent(BaseModel):
    type: Literal["raw"] = "raw"
    stream: str = ""
    content: str = ""


EventKind = Annotated[
    ThinkingEvent
    | TextEvent
    | ToolUseEvent
    | ToolResultEvent
    | FileChangeEvent
    | TurnCompleteEvent
    | ErrorEvent
    | ExitEvent
    | RawEvent,
    Field(discriminator="type"),
]

TERMINAL_EVENT_TYPES = frozenset({"turn_complete", "exit", "error"})

KNOWN_AGENT_EVENT_TYPES = frozenset({
    "thinking",
    "text",
    "tool_use",
    "tool_result",
    "file_change",
    "turn_complete",
    "error",
    "exit",
    "raw",
})


class UniversalEvent(BaseModel):
    session_id: str
    kind: EventKind
    timestamp: str


# ---------------------------------------------------------------------------
# Exec stream events (for sandbox exec streaming)
# ---------------------------------------------------------------------------


class ExecChunkEvent(BaseModel):
    type: Literal["chunk"] = "chunk"
    stream: str = ""
    data: str = ""


class ExecExitEvent(BaseModel):
    type: Literal["exit"] = "exit"
    exit_code: int = 0


ExecStreamEvent = Annotated[
    ExecChunkEvent | ExecExitEvent,
    Field(discriminator="type"),
]
