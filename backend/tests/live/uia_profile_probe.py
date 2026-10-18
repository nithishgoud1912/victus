"""Explicit Windows qualification probe. No guessed executable, process or selector."""

import argparse
import json
import time
from dataclasses import asdict
from pathlib import Path

from victus.adapters.uia.actions import UIAActions
from victus.adapters.uia.applications import UIABlocked, UIAWorker, load_profiles
from victus.adapters.uia.selectors import SelectorResolver


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profiles", type=Path, required=True)
    parser.add_argument("--application", required=True)
    parser.add_argument("--control", required=True)
    operation = parser.add_mutually_exclusive_group()
    operation.add_argument("--text")
    operation.add_argument("--invoke", action="store_true")
    parser.add_argument("--allow-keyboard", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--prepare-control", action="append", default=[])
    args = parser.parse_args()
    report = {"status": "blocked", "keyboard_requested": args.allow_keyboard}
    if args.output and args.output.exists():
        parser.error("Output must be a new private report")
    try:
        with UIAWorker(load_profiles(args.profiles)) as worker:
            app = worker.launch(args.application)
            owned = worker._resolve_app(app)
            report["identity"] = asdict(owned.identity)
            if owned.launcher_identity:
                report["launcher_identity"] = asdict(owned.launcher_identity)
            resolver = SelectorResolver(worker)
            actions = UIAActions(resolver)

            def resolve_ready(key):
                deadline = time.monotonic() + 5
                while True:
                    try:
                        return resolver.resolve(app, key)
                    except UIABlocked:
                        if time.monotonic() >= deadline:
                            raise
                        time.sleep(0.05)

            for key in args.prepare_control:
                reference = resolve_ready(key)
                actions.invoke(reference, allow_keyboard=args.allow_keyboard)
                time.sleep(0.15)
            target = resolve_ready(args.control)
            if args.text is not None:
                result = actions.set_text(
                    target,
                    args.text,
                    allow_keyboard=args.allow_keyboard,
                    require_empty=args.control == "editor",
                )
                report.update(status=result.status, method=result.method)
            elif args.invoke:
                result = actions.invoke(target, allow_keyboard=args.allow_keyboard)
                report.update(status=result.status, method=result.method)
            else:
                report["status"] = "resolved"
    except UIABlocked as error:
        report.update(status="blocked", error_code=str(error))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))
    print("Application left open for manual inspection")


if __name__ == "__main__":
    main()
