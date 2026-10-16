"""Explicit Windows qualification probe. No guessed executable, process or selector."""

import argparse
from pathlib import Path

from victus.adapters.uia.actions import UIAActions
from victus.adapters.uia.applications import UIAWorker, load_profiles
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
    args = parser.parse_args()
    with UIAWorker(load_profiles(args.profiles)) as worker:
        app = worker.launch(args.application)
        resolver = SelectorResolver(worker)
        target = resolver.resolve(app, args.control)
        actions = UIAActions(resolver)
        if args.text is not None:
            result = actions.set_text(target, args.text, allow_keyboard=args.allow_keyboard)
            print(result.status, result.method)
        elif args.invoke:
            print(actions.invoke(target, allow_keyboard=args.allow_keyboard))
        else:
            print("Qualified one exact control under the owned process")
    print("Application left open for manual inspection")


if __name__ == "__main__":
    main()
