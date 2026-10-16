"""Conservative transcript parsing; no fuzzy target selection or permission inference."""

import re
from dataclasses import dataclass

from pydantic import ValidationError

from victus.tools.contracts import ActionRequest, NoteArguments


@dataclass(frozen=True)
class Review:
    accepted: bool
    action: ActionRequest | None = None
    clarification: str | None = None


NON_SPEECH = frozenset(
    {
        "",
        "[silence]",
        "[music]",
        "(music)",
        "music",
        "[noise]",
        "[inaudible]",
        "[blank_audio]",
        "thank you for watching",
        "thanks for watching",
        "you",
        "uh",
        "um",
        "hmm",
    }
)


def review_transcript(text: str) -> Review:
    normalized = text.strip()
    if (
        not normalized
        or len(text) > 8192
        or normalized.strip(".!?").strip().casefold() in NON_SPEECH
        or not any(c.isalnum() for c in normalized)
    ):
        return Review(False, clarification="No clear speech. Record a new command.")
    match = re.fullmatch(
        r"create note ([A-Za-z0-9][A-Za-z0-9_-]{0,63}\.txt) with text (.+)",
        normalized,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return Review(
            True,
            clarification=(
                "Specify the exact filename and note text. "
                "Supported command: create note filename.txt with text your message. "
                "Review and correct both fields before submitting."
            ),
        )
    try:
        action = ActionRequest(
            tool="fs.create_note", arguments=NoteArguments(filename=match[1], text=match[2])
        )
    except ValidationError:
        return Review(True, clarification="The filename or note text needs correction.")
    return Review(True, action)
