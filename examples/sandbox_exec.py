"""
Sandbox — create a sandbox, run commands, upload/download files.

Usage:
    KUNO_BASE_URL=http://localhost:8080 python examples/sandbox_exec.py
"""

import asyncio

from kuno_sandbox import ExecChunkEvent, ExecExitEvent, KunoClient


async def main() -> None:
    async with KunoClient() as client:
        sandbox = await client.sandboxes.create(
            "python:3.12-slim", name="demo-sandbox"
        )

        try:
            print(f"Sandbox created: {sandbox.id}")

            # Execute a command
            result = await sandbox.exec(
                "python3", args=["-c", "import sys; print(f'Python {sys.version}')"]
            )
            print(f"stdout: {result.stdout}")
            print(f"exit_code: {result.exit_code}")
            print(f"duration: {result.duration_ms}ms")

            # Upload a file
            await sandbox.upload("/tmp/hello.py", b'print("Hello from sandbox!")')
            print("File uploaded.")

            # Run the uploaded file
            run = await sandbox.exec("python3", args=["/tmp/hello.py"])
            print(f"Output: {run.stdout}")

            # Download it back
            downloaded = await sandbox.download("/tmp/hello.py")
            print(f"Downloaded: {downloaded.decode()}")

            # Stream a long-running command
            print("\n--- Streaming pip install ---")
            async for event in await sandbox.exec_stream(
                "pip", args=["install", "requests"]
            ):
                match event:
                    case ExecChunkEvent(data=data):
                        print(data, end="")
                    case ExecExitEvent(exit_code=code):
                        print(f"\nExit code: {code}")

            # Pause and resume
            await sandbox.pause()
            print("Sandbox paused.")
            await sandbox.resume()
            print("Sandbox resumed.")

        finally:
            await sandbox.destroy()
            print("Sandbox destroyed.")


if __name__ == "__main__":
    asyncio.run(main())
