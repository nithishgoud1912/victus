import argparse
import json
from pathlib import Path

from victus.settings import Settings


def main() -> None:
    parser = argparse.ArgumentParser(prog="victus")
    parser.add_argument("command", choices=["doctor", "serve", "export-openapi"])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
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
        print(
            json.dumps(
                {
                    "data_dir": str(settings.data_dir),
                    "token_configured": len(settings.api_token) >= 32,
                    "mode": "foundation",
                    "ollama": "not_checked_in_this_stage",
                    "browser": "not_checked_in_this_stage",
                    "microphone": "not_checked_in_this_stage",
                },
                indent=2,
            )
        )
        return
    if len(settings.api_token) < 32:
        parser.error("Set VICTUS_API_TOKEN to a random value of at least 32 characters")
    import uvicorn

    from victus.api.app import create_app

    uvicorn.run(create_app(settings), host="127.0.0.1", port=8765, workers=1, access_log=False)
