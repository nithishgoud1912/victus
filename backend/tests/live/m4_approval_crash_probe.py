"""Kill the process after permit commit or a partial write, then resume safely."""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
from graph_support import Fixture

from victus.agent.graph import agent
from victus.safety.permits import PermitStore


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["consume", "effect", "resume"])
    parser.add_argument("--data-dir", type=Path, required=True)
    args = parser.parse_args()
    fixture = Fixture(args.data_dir, crash="effect" if args.mode == "effect" else None)
    if args.mode == "consume":
        consume = PermitStore.consume_permit

        def crash(self, *args, **kwargs):
            consume(self, *args, **kwargs)
            os._exit(73)

        PermitStore.consume_permit = crash
    async with agent(fixture.services) as runner:
        result = (
            await runner.resume(fixture.task)
            if args.mode == "resume"
            else await runner.start(fixture.task, fixture.goal())
        )
    ledger = fixture.context(result).ledger
    records = ledger.list_for_task(fixture.task)
    with fixture.services.approvals(result).connect() as db:
        approvals = [r[0] for r in db.execute("SELECT state FROM approvals")]
    print(
        json.dumps(
            {
                "status": result["status"],
                "calls": fixture.calls,
                "approvals": approvals,
                "attempts": [r.status for r in records],
            }
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
