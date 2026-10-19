"""Explicit local inventory. Never downloads, starts a model or grants capability."""

import asyncio
import json
import shutil
from pathlib import Path

from victus.models.contracts import ModelError
from victus.models.ollama import OllamaClient
from victus.runtime.resources import ResourcePressure, gpu_memory, resources, system_memory
from victus.workflows.qualification_records import runtime_identity


def inventory(output, *, model=None):
    report = {
        "schema_version": 1,
        "runtime_sha256": runtime_identity(),
        "inference_qualified": False,
        "model_downloaded": False,
        "cloud_used": False,
        "models": [],
        "selected_pin": None,
        "model_service_available": False,
    }
    try:
        report["memory"] = resources().check_current()
        report["resource_ready"] = True
    except ResourcePressure as error:
        report.update(resource_ready=False, resource_error=str(error))
        try:
            report["memory"] = system_memory()
        except Exception:
            report["memory"] = None
    try:
        report["gpu_memory"] = gpu_memory()
    except Exception:
        report["gpu_memory"] = None
    report["disk_free_bytes"] = shutil.disk_usage(Path(output).absolute().parent).free

    async def installed():
        async with OllamaClient() as client:
            return await client.list_models()

    try:
        pins = asyncio.run(installed())
        report["models"] = [pin.model_dump() for pin in pins]
        if model is not None:
            selected = [pin for pin in pins if pin.name == model]
            if len(selected) == 1:
                report["selected_pin"] = selected[0].model_dump()
            else:
                report["model_error"] = "EXACT_INSTALLED_MODEL_REQUIRED"
        report["model_service_available"] = True
    except ModelError as error:
        report.update(model_service_available=False, model_error=error.error.code.value)
    report["selection_is_not_reasoning_qualification"] = True
    report["runtime_end_sha256"] = runtime_identity()
    with Path(output).open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(report, indent=2) + "\n")
    return report
