"""
Long-Running Service — start an HTTP server, send requests, stream logs.

Usage:
    KUNO_BASE_URL=http://localhost:8080 python examples/long_running_service.py
"""

import asyncio

from kuno_sandbox import ExecChunkEvent, ExecExitEvent, KunoClient


async def main() -> None:
    async with KunoClient() as client:
        sandbox = await client.sandboxes.python(name="http-server")

        try:
            print(f"Sandbox created: {sandbox.id}")

            # 1. Upload a small HTTP server script
            server_code = b"""\
from http.server import HTTPServer, BaseHTTPRequestHandler
import json, sys

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps({"path": self.path, "status": "ok"}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        # Log to stderr so we can see it
        print(f"GET {self.path} -> 200", file=sys.stderr, flush=True)

    def log_message(self, format, *args):
        pass  # suppress default logging

print("Starting server on :8000", flush=True)
HTTPServer(("", 8000), Handler).serve_forever()
"""
            await sandbox.upload("/tmp/server.py", server_code)
            print("Uploaded server script.")

            # 2. Start the server in the background (streaming its output)
            print("\n--- Starting server (streaming logs) ---")
            log_stream = await sandbox.exec_stream(
                "python3", args=["/tmp/server.py"]
            )

            # Read the first chunk to confirm startup
            first = await log_stream.__anext__()
            if isinstance(first, ExecChunkEvent):
                print(f"Server log: {first.data.strip()}")

            # 3. Send HTTP requests to the server from inside the sandbox
            print("\n--- Sending requests ---")
            for path in ["/", "/health", "/api/data"]:
                result = await sandbox.exec(
                    "python3",
                    args=[
                        "-c",
                        f"import urllib.request, json; "
                        f"r = urllib.request.urlopen('http://localhost:8000{path}'); "
                        f"print(json.loads(r.read()))",
                    ],
                )
                print(f"  GET {path} -> {result.stdout.strip()}")

            # 4. Stream remaining logs
            print("\n--- Remaining server logs ---")

            # Kill the server so the stream finishes
            await sandbox.exec("pkill", args=["-f", "server.py"])

            async for event in log_stream:
                match event:
                    case ExecChunkEvent(stream=stream, data=data):
                        label = "stdout" if stream == "Stdout" else "stderr"
                        print(f"  [{label}] {data}", end="")
                    case ExecExitEvent(exit_code=code):
                        print(f"\n  Server exited with code {code}")

        finally:
            await sandbox.destroy()
            print("Sandbox destroyed.")


if __name__ == "__main__":
    asyncio.run(main())
