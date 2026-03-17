"""
Parallel Sandboxes — spin up multiple sandboxes concurrently with asyncio.gather.

Usage:
    KUNO_BASE_URL=http://localhost:8080 python examples/parallel_sandboxes.py
"""

import asyncio

from kuno_sandbox import KunoClient, Sandbox


async def run_task(sandbox: Sandbox, label: str, code: str) -> str:
    """Run code inside a sandbox and return the output."""
    result = await sandbox.run(code, interpreter="sh")
    return f"[{label}] {result.strip()}"


async def main() -> None:
    async with KunoClient() as client:
        # Create three sandboxes in parallel
        sandboxes = await asyncio.gather(
            client.sandboxes.python(name="worker-1"),
            client.sandboxes.node(name="worker-2"),
            client.sandboxes.ubuntu(name="worker-3"),
        )
        print(f"Created {len(sandboxes)} sandboxes")

        try:
            # Run tasks in parallel across all sandboxes
            results = await asyncio.gather(
                run_task(
                    sandboxes[0],
                    "python",
                    'python3 -c "print(sum(range(1_000_000)))"',
                ),
                run_task(
                    sandboxes[1],
                    "node",
                    'node -e "console.log(Array.from({length:10},(_,i)=>i*i).join(\',\'))"',
                ),
                run_task(
                    sandboxes[2],
                    "ubuntu",
                    "uname -a",
                ),
            )

            for line in results:
                print(line)

        finally:
            # Tear down all sandboxes in parallel
            await asyncio.gather(*(sb.destroy() for sb in sandboxes))
            print("All sandboxes destroyed.")


if __name__ == "__main__":
    asyncio.run(main())
