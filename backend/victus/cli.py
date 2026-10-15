import argparse
import json

from victus.settings import Settings


def main() -> None:
    parser = argparse.ArgumentParser(prog="victus")
    parser.add_argument("command", choices=["doctor", "serve"])
    args = parser.parse_args()
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