"""
File Workflow — upload source, exec build/run, download artifacts.

Usage:
    KUNO_BASE_URL=http://localhost:8080 python examples/file_workflow.py
"""

import asyncio

from kuno_sandbox import KunoClient


async def main() -> None:
    async with KunoClient() as client:
        sandbox = await client.sandboxes.python(name="file-workflow")

        try:
            print(f"Sandbox created: {sandbox.id}")

            # 1. Upload a Python source file
            source = b"""\
import json, sys

data = {"message": "Hello from sandbox!", "numbers": list(range(5))}
with open("/tmp/output.json", "w") as f:
    json.dump(data, f, indent=2)
print(f"Wrote {sys.getsizeof(data)} bytes", file=sys.stderr)
print("Done")
"""
            await sandbox.upload("/tmp/app.py", source)
            print("Uploaded /tmp/app.py")

            # 2. Execute the script
            result = await sandbox.exec("python3", args=["/tmp/app.py"])
            print(f"stdout: {result.stdout.strip()}")
            print(f"stderr: {result.stderr.strip()}")
            print(f"exit code: {result.exit_code}")

            # 3. Download the generated artifact
            artifact = await sandbox.download("/tmp/output.json")
            print(f"Downloaded artifact ({len(artifact)} bytes):")
            print(artifact.decode())

            # 4. Use the run() convenience method for a quick check
            output = await sandbox.run(
                'python3 -c "import json; print(json.load(open(\'/tmp/output.json\')))"',
            )
            print(f"Verified: {output.strip()}")

        finally:
            await sandbox.destroy()
            print("Sandbox destroyed.")


if __name__ == "__main__":
    asyncio.run(main())
