"""Hard process exit in real graph/dispatcher persistence windows. No model required."""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
from graph_support import Fixture

from victus.agent.graph import agent


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["effect", "journal", "resume"])
    parser.add_argument("--data-dir", type=Path, required=True)
    args = parser.parse_args()
    fixture = Fixture(args.data_dir, crash="effect" if args.mode == "effect" else None)
    if args.mode == "journal":
        complete = fixture.store.complete

        def crash_after_journal(task, sequence, result):
            complete(task, sequence, result)
            if result.get("execution_status") == "succeeded":
                os._exit(72)

        fixture.store.complete = crash_after_journal
    async with agent(fixture.services) as runner:
        result = (
            await runner.resume(fixture.task)
            if args.mode == "resume"
            else await runner.start(fixture.task, fixture.goal())
        )
    print(
        json.dumps(
            {
                "status": result["status"],
                "action_refs": result["action_ledger_refs"],
                "calls_this_process": fixture.calls,
                "error_code": result["error_code"],
            }
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
