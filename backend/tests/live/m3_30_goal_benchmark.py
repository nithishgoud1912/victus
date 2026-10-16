"""Explicit local benchmark. Never discovered as an ordinary pytest test."""

import argparse
import asyncio
from pathlib import Path

from victus.agent.benchmark import benchmark


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--suite", type=Path, default=Path(__file__).parents[3] / "evaluation/m3-30-goals-v1.json"
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default="qwen3:4b")
    parser.add_argument("--digest")
    args = parser.parse_args()
    result = asyncio.run(benchmark(args.suite, args.output, model=args.model, digest=args.digest))
    print(f"Verified {result.get('verified_successes', 0)}/30; qualified={result['qualified']}")
    raise SystemExit(0 if result["qualified"] else 2)


if __name__ == "__main__":
    main()
