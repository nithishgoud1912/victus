import argparse
import json
from pathlib import Path

from victus.settings import Settings


def main() -> None:
    parser = argparse.ArgumentParser(prog="victus")
    parser.add_argument("command", choices=["doctor", "serve", "export-openapi", "cloud-key",
                                            "backup", "restore", "migrate", "version",
                                            "qualify-fixture", "promote-fixture", "qualify-native",
                                            "prepare-native", "assemble-native", "promote-native",
                                            "readiness"])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--destination", type=Path)
    parser.add_argument("--profile")
    parser.add_argument("--model")
    parser.add_argument("--repetitions", type=int, choices=range(1, 21), default=20)
    args = parser.parse_args()
    if args.command == "qualify-fixture":
        if args.output is None:
            parser.error("qualify-fixture requires a new --output directory")
        from victus.workflows.fixture_qualification import main as qualify

        raise SystemExit(qualify(["--output", str(args.output), "--repetitions", str(args.repetitions)]))
    if args.command in {"promote-fixture", "promote-native"}:
        if args.source is None:
            parser.error("promotion requires --source report.json")
        from victus.workflows.qualification_records import promote_fixture, promote_native

        try:
            promote = promote_fixture if args.command == "promote-fixture" else promote_native
            destination = promote(args.source)
        except (OSError, ValueError, KeyError, TypeError):
            parser.error("Promotion refused: require complete matching reports, artifacts and no existing record")
        print(f"Qualification installed at {destination}. Restart to apply it.")
        return
    if args.command in {"prepare-native", "assemble-native", "qualify-native"}:
        if args.output is None:
            parser.error("native qualification requires a new --output")
        try:
            if args.command == "prepare-native":
                from victus.workflows.native_qualification import prepare_session

                result = prepare_session(args.output, args.profile)
            elif args.command == "assemble-native":
                if args.source is None:
                    parser.error("assemble-native requires --source session.json")
                from victus.workflows.native_qualification import assemble_session

                result = assemble_session(args.source, args.output)
            else:
                if args.source is None or not args.profile:
                    parser.error("qualify-native requires --source profiles.json and --profile ID")
                from victus.workflows.qualification import qualify

                result = qualify("notepad", args.output, profiles_file=args.source,
                                 profile=args.profile, repetitions=args.repetitions)
        except (OSError, ValueError, KeyError, TypeError):
            parser.error("Native qualification refused: check profile, fresh paths and current evidence")
        print(result)
        record = json.loads(result.read_text(encoding="utf-8"))
        if args.command == "assemble-native":
            raise SystemExit(0 if record["qualified"] else 2)
        if args.command == "qualify-native":
            raise SystemExit(0 if record["status"] == "succeeded" else 2)
        return
    if args.command == "readiness":
        if args.output is None:
            parser.error("readiness requires a new --output file with an existing parent")
        from victus.runtime.readiness import inventory

        try:
            result = inventory(args.output, model=args.model)
        except (OSError, ValueError):
            parser.error("Readiness report unavailable: check output and runtime inventory")
        print(json.dumps({"resource_ready": result["resource_ready"],
                          "model_service_available": result["model_service_available"],
                          "inference_qualified": False}))
        return
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
