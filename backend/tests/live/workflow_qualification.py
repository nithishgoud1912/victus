"""Run real, independently supervised M2 workflows; never simulate native success."""

import argparse
import json
from pathlib import Path

from victus.workflows.qualification import qualify


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=["browser", "notepad"])
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--repetitions", type=int, default=20)
    parser.add_argument("--profiles", type=Path)
    parser.add_argument("--profile")
    parser.add_argument("--browser-executable", type=Path)
    parser.add_argument("--encoding", choices=["utf-8", "utf-8-sig", "utf-16"], default="utf-8")
    args = parser.parse_args()
    if args.kind == "notepad" and (args.profiles is None or not args.profile):
        parser.error(
            "Notepad qualification requires an explicitly reviewed --profiles and --profile"
        )
    result = qualify(
        args.kind,
        args.data_dir,
        repetitions=args.repetitions,
        profiles_file=args.profiles,
        profile=args.profile,
        browser_executable=args.browser_executable,
        encoding=args.encoding,
        fixture_root=Path(__file__).parents[1] / "fixtures" / "m2",
    )
    print(result)
    report = json.loads(result.read_text())
    raise SystemExit(0 if report["status"] == "succeeded" else 2)


if __name__ == "__main__":
    main()
