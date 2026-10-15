from pathlib import Path

from victus.tools.contracts import NoteArguments


def verify_note(target: Path, arguments: NoteArguments) -> bool:
    return target.is_file() and target.read_bytes() == arguments.text.encode("utf-8")