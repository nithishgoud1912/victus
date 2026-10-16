import argparse
import json
from pathlib import Path

from victus.settings import Settings


def main() -> None:
    parser = argparse.ArgumentParser(prog="victus")
    parser.add_argument("command", choices=["doctor", "serve", "export-openapi", "cloud-key",
                                            "backup", "restore", "migrate", "version"])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--destination", type=Path)
    args = parser.parse_args()
    if args.command == "version":
        from victus.runtime.release import version

        print(version())
        return
    if args.command in {"backup", "restore", "migrate"}:
        from victus.runtime.release import maintain, print_result

        try:
            print_result(maintain(args.command, Settings.from_env(), args.source, args.destination))
        except Exception:
            parser.error("Maintenance failed: stop all application processes, check compatible schema and new destination")
        return
    if args.command == "cloud-key":
        from getpass import getpass

        from victus.adapters.credentials import WindowsCredentials

        if not __import__("sys").stdin.isatty():
            parser.error("cloud-key requires an interactive terminal")
        try:
            WindowsCredentials().store(getpass("OpenRouter key (hidden): "))
        except (RuntimeError, ValueError):
            parser.error("Credential could not be stored")
        print("Cloud credential stored in Windows Credential Manager.")
        return
    if args.command == "export-openapi":
        from victus.api.app import create_app

        if args.output is None:
            parser.error("export-openapi requires --output")
        # No service startup, token loading, worker, data directory or public route.
        schema = create_app(
            Settings(Path(".schema-export"), "schema-export-placeholder-" + "x" * 32)
        ).openapi()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")
        print(f"Exported OpenAPI schema to {args.output}")
        return
    settings = Settings.from_env()
    if args.command == "doctor":
        from victus.runtime.release import prerequisites, print_result

        print_result(prerequisites(settings))
        return
    if len(settings.api_token) < 32:
        parser.error("Set VICTUS_API_TOKEN to a random value of at least 32 characters")
    import uvicorn

    from victus.api.app import create_app

    uvicorn.run(create_app(settings), host="127.0.0.1", port=8765, workers=1, access_log=False)
