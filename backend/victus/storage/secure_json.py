"""DPAPI at rest on Windows; private-file semantics on POSIX, not forensic erasure."""

import base64
import json

from victus.safety.previews import protect, unprotect

PREFIX = "protected:v1:"


def encode_text(value: str) -> str:
    return PREFIX + base64.b64encode(protect(value.encode("utf-8"))).decode("ascii")


def decode_text(value: str) -> str:
    if value.startswith(PREFIX):
        return unprotect(base64.b64decode(value[len(PREFIX) :], validate=True)).decode("utf-8")
    return value  # Legacy migration reads only, never constructs Python objects.


def encode(value) -> str:
    return encode_text(json.dumps(value, ensure_ascii=False, allow_nan=False))


def decode(value: str):
    return json.loads(decode_text(value))
