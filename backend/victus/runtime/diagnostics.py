"""Redacted diagnostics are frozen for review before explicit export."""

import hashlib
import json
import time
from uuid import uuid4


class Diagnostics:
    def __init__(self, resources):
        self.resources = resources
        self.previews = {}

    def preview(self):
        now = time.time()
        self.previews = {k: v for k, v in self.previews.items() if v[0] > now}
        if len(self.previews) >= 8:
            raise ValueError("Too many diagnostic previews")
        value = {
            "version": 1,
            "resources": self.resources.snapshot(),
            "redaction": "No logs, prompts, transcripts, paths, device identifiers, credentials or memory values included",
        }
        text = json.dumps(value, sort_keys=True, indent=2, allow_nan=False)
        key, digest = uuid4().hex, hashlib.sha256(text.encode()).hexdigest()
        self.previews[key] = (now + 300, digest, text)
        return {"preview_id": key, "sha256": digest, "contents": text, "expires_at": now + 300}

    def export(self, preview_id, sha256):
        value = self.previews.pop(preview_id, None)
        if value is None or value[0] <= time.time() or value[1] != sha256:
            raise ValueError("Diagnostic preview changed or expired; review again")
        return {"contents": value[2], "sha256": value[1]}
