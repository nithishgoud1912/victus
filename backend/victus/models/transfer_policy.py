"""Ephemeral, exact-body, one-use consent. No consent survives a restart."""

import hashlib
import json
import threading
import time
from dataclasses import dataclass
from uuid import uuid4


def encode_transfer(body):
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    if len(raw) > 96000:
        raise ValueError("TRANSFER_TOO_LARGE")
    return raw


@dataclass(frozen=True)
class TransferPreview:
    id: str
    recipient: str
    body: str
    sha256: str
    expires_in_seconds: float


class ConsentRequired(PermissionError):
    def __init__(self):
        super().__init__("EXPLICIT_TRANSFER_CONSENT_REQUIRED")


class TransferPolicy:
    def __init__(self, *, clock=time.monotonic, lifetime=120):
        if not 0 < lifetime <= 300:
            raise ValueError("Invalid consent lifetime")
        self.clock, self.lifetime = clock, lifetime
        self._pending = {}
        self._lock = threading.Lock()

    def _purge(self):
        for key, entry in list(self._pending.items()):
            if entry[2] <= self.clock():
                del self._pending[key]

    def preview(self, recipient, body):
        raw = encode_transfer(body)
        digest = hashlib.sha256(raw).hexdigest()
        with self._lock:
            self._purge()
            if len(self._pending) >= 8:
                raise ValueError("Too many pending transfers")
            key = uuid4().hex
            self._pending[key] = (recipient, digest, self.clock() + self.lifetime, False)
        return TransferPreview(key, recipient, raw.decode(), digest, self.lifetime)

    def decide(self, key, *, approve, confirmation):
        if type(approve) is not bool or confirmation != "explicit_user_review":
            raise ConsentRequired()
        with self._lock:
            self._purge()
            entry = self._pending.pop(key, None)
            if entry is None or entry[3]:
                raise ConsentRequired()
            if approve:
                self._pending[key] = (*entry[:3], True)

    def consume(self, key, recipient, body):
        digest = hashlib.sha256(encode_transfer(body)).hexdigest()
        with self._lock:
            self._purge()
            entry = self._pending.pop(key, None)
            if entry is None or not entry[3] or entry[:2] != (recipient, digest):
                raise ConsentRequired()

    def clear(self):
        with self._lock:
            self._pending.clear()
