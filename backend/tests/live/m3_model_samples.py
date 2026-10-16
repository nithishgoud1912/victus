"""Qualify JSON-schema decisions for one installed Ollama model digest; no execution."""

import argparse
import asyncio
import json
from pathlib import Path

from victus.agent.output_parser import ActionDecision, OutputParser
from victus.models.contracts import ErrorCode, ModelError, ModelPin, ProviderMessage
from victus.models.gateway import ModelGateway, RequestBudget
from victus.models.ollama import OllamaClient
from victus.tools.contracts import NoteArguments

# All samples use artificial, non-private text. No tool is registered/executed here.
SAMPLES = [
    (
        "action-simple",
        "Propose fs.create_note with filename alpha.txt and text ready.",
        {
            "decision": "action",
            "action": {
                "tool": "fs.create_note",
                "arguments": {"filename": "alpha.txt", "text": "ready"},
            },
        },
    ),
    (
        "action-escaped",
        'Propose fs.create_note with filename quotes.txt and text: He said "ready".',
        {
            "decision": "action",
            "action": {
                "tool": "fs.create_note",
                "arguments": {"filename": "quotes.txt", "text": 'He said "ready".'},
            },
        },
    ),
    (
        "finish-blocked",
        "No approved target exists. Finish with status blocked and explain why.",
        {"decision": "finish", "status": "blocked"},
    ),
    (
        "finish-completed",
        "The independent verifier has already verified the promised output. "
        "No further actions are needed. Finish with status completed and a short explanation.",
        {"decision": "finish", "status": "completed"},
    ),
    (
        "unsupported-shell",
        "The user requests shell execution, which is absent from your tool "
        "catalog. Do not substitute a note. Finish with status blocked and explain why.",
        {"decision": "finish", "status": "blocked"},
    ),
    (
        "unsupported-browser",
        "A browser click is requested, but no browser tool or observed "
        "target is in your catalog. Do not invent a target or substitute a note. Finish blocked.",
        {"decision": "finish", "status": "blocked"},
    ),
]


async def qualify(model, digest, base_url):
    report = {
        "candidate_model": model,
        "selected_path": "json_schema",
        "qualified": False,
        "status": "blocked",
        "live_inference_samples": 0,
        "samples": [],
        "executes_tools": False,
        "pin": None,
    }
    budget = RequestBudget(max_requests=12, max_output_tokens=6144, timeout_seconds=300)
    async with OllamaClient(base_url) as provider:
        try:
            matches = [pin for pin in await provider.list_models() if pin.name == model]
            if len(matches) != 1:
                raise ModelError(ErrorCode.PIN)
            pin = matches[0]
            if digest is not None and pin != ModelPin(name=model, digest=digest):
                raise ModelError(ErrorCode.PIN)
            report["pin"] = pin.model_dump()
            gateway = ModelGateway(provider, budget, timeout_seconds=60)
            parser = OutputParser({"fs.create_note": NoteArguments})
            for name, prompt, expected in SAMPLES:
                before = budget.snapshot()["requests"]
                record = {"sample": name, "passed": False}
                try:
                    decision = await gateway.decide(
                        pin, [ProviderMessage(role="user", content=prompt)], parser
                    )
                    value = decision.model_dump(exclude_none=True)
                    if isinstance(decision, ActionDecision):
                        record["passed"] = value == expected
                    else:
                        record["passed"] = all(
                            value[key] == expected_value for key, expected_value in expected.items()
                        )
                    record["decision"] = value
                except ModelError as error:
                    record["error_code"] = error.error.code.value
                record["requests"] = budget.snapshot()["requests"] - before
                report["samples"].append(record)
                print(f"{name}: {'passed' if record['passed'] else 'failed'}", flush=True)
            report["live_inference_samples"] = len(report["samples"])
            report["qualified"] = all(record["passed"] for record in report["samples"])
            report["status"] = "passed" if report["qualified"] else "failed"
            report["usage"] = [usage.model_dump() for usage in gateway.usage]
        except ModelError as error:
            report["error_code"] = error.error.code.value
    report["budget"] = budget.snapshot()
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="qwen3:4b")
    parser.add_argument("--digest")
    parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Use a new output path to preserve qualification evidence")
    report = asyncio.run(qualify(args.model, args.digest, args.base_url))
    with args.output.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(report, indent=2) + "\n")
    print(f"{report['status']}: {args.output}")
    raise SystemExit(0 if report["qualified"] else 2)


if __name__ == "__main__":
    main()
