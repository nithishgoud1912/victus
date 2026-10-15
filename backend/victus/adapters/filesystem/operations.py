import os
from pathlib import Path

from victus.tools.contracts import NoteArguments


def create_note(workspace: Path, arguments: NoteArguments) -> Path:
    target = workspace / arguments.filename
    payload = arguments.text.encode("utf-8")
    # Exclusive creation also prevents overwriting a file created after the policy check.
    with target.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    return target