"""Concrete reviewed file snapshots and destination-bound file-input preparation."""

from __future__ import annotations

import hashlib
import mimetypes
import time
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from playwright.async_api import Error as PlaywrightError

from victus.adapters.playwright.downloads import TransferBlocked, read_reviewed_file
from victus.adapters.playwright.locators import origin_of


@dataclass(frozen=True)
class ReviewedFile:
    path: str
    size: int
    sha256: str


@dataclass(frozen=True)
class UploadReview:
    review_id: str
    task_id: str
    destination: str
    files: tuple[ReviewedFile, ...]


class UploadReviews:
    def __init__(self, task_id: str, *, source_roots: tuple[Path, ...], max_bytes=10_000_000):
        if not task_id or not 1 <= max_bytes <= 50_000_000:
            raise ValueError("Invalid upload limits")
        self.task_id = task_id
        self._roots = frozenset(path.resolve(strict=True) for path in source_roots)
        self._max_bytes = max_bytes
        self._reviews = {}
        self._permits = {}
        self._armed = {}

    def review(self, files: tuple[Path, ...], destination: str) -> UploadReview:
        """Build a concrete review; this alone does not authorize preparation or sending."""
        origin_of(destination)
        if not 1 <= len(files) <= 10 or len(self._reviews) >= 32:
            raise TransferBlocked("UPLOAD_LIST_LIMIT")
        reviewed = []
        for path in files:
            if path.is_symlink() or not path.is_absolute():
                raise TransferBlocked("UPLOAD_FILE_UNSAFE")
            resolved = path.resolve(strict=True)
            if resolved.parent not in self._roots:
                raise TransferBlocked("UPLOAD_FILE_OUTSIDE_SCOPE")
            data = read_reviewed_file(path, self._max_bytes)
            reviewed.append(
                ReviewedFile(str(resolved), len(data), hashlib.sha256(data).hexdigest())
            )
        if len({file.path for file in reviewed}) != len(reviewed):
            raise TransferBlocked("UPLOAD_DUPLICATE_FILE")
        if sum(file.size for file in reviewed) > self._max_bytes:
            raise TransferBlocked("UPLOAD_TOTAL_LIMIT")
        review = UploadReview(uuid4().hex, self.task_id, destination, tuple(reviewed))
        self._reviews[review.review_id] = review
        return review

    def approve(self, review: UploadReview) -> str:
        """Trusted policy entry point AFTER the exact file list/destination is reviewed."""
        if len(self._permits) >= 64:
            raise TransferBlocked("UPLOAD_PERMIT_LIMIT")
        if self._reviews.get(review.review_id) != review:
            raise TransferBlocked("UPLOAD_REVIEW_UNKNOWN")
        permit = uuid4().hex
        self._permits[permit] = (review, time.monotonic() + 60)
        return permit

    def _consume(self, permit, destination):
        approved = self._permits.pop(permit, None)
        if approved is None or time.monotonic() > approved[1]:
            raise TransferBlocked("UPLOAD_PERMIT_INVALID")
        review = approved[0]
        if review.destination != destination or self._reviews.pop(review.review_id, None) != review:
            raise TransferBlocked("UPLOAD_DESTINATION_CHANGED")
        payloads = []
        for file in review.files:
            data = read_reviewed_file(Path(file.path), self._max_bytes)
            if len(data) != file.size or hashlib.sha256(data).hexdigest() != file.sha256:
                raise TransferBlocked("UPLOAD_FILE_CHANGED")
            payloads.append(
                {
                    "name": Path(file.path).name,
                    "buffer": data,
                    "mimeType": mimetypes.guess_type(file.path)[0] or "application/octet-stream",
                }
            )
        return payloads

    async def prepare_input(self, resolver, ref, observation_id, permit, destination):
        """Worker-only preparation, never submit. Network authorization is still required."""
        if resolver._network_task_id != self.task_id or resolver._upload_reviews is not self:
            raise TransferBlocked("UPLOAD_TASK_MISMATCH")
        async with resolver._operation_lock:
            target = await resolver.resolve_target(ref, observation_id)
            try:
                if (target.binding.identity["tag"], target.binding.identity["type"]) != (
                    "input",
                    "file",
                ):
                    raise TransferBlocked("FILE_INPUT_REQUIRED")
                resolver._check_origin(destination)
                action = await target.element.evaluate("el => el.form ? el.form.action : null")
                if action != destination:
                    raise TransferBlocked("UPLOAD_DESTINATION_CHANGED")
                payloads = self._consume(permit, destination)
                await resolver._assert_fresh(target.observation)
                grant = self._arm(destination, payloads)
                try:
                    await target.element.set_input_files(payloads, timeout=5000)
                except BaseException as error:
                    self._armed.pop(grant, None)
                    if isinstance(error, PlaywrightError):
                        raise RuntimeError("UPLOAD_PREPARATION_UNCERTAIN") from None
                    raise
            finally:
                resolver.invalidate(observation_id)
                await target.element.dispose()

    def _arm(self, destination, payloads):
        if len(self._armed) >= 32:
            raise TransferBlocked("UPLOAD_SEND_LIMIT")
        files = tuple(
            (p["name"], len(p["buffer"]), hashlib.sha256(p["buffer"]).hexdigest()) for p in payloads
        )
        grant = uuid4().hex
        self._armed[grant] = (destination, files, time.monotonic() + 60)
        return grant

    def authorize_multipart(self, destination, files):
        for grant, (reviewed_destination, reviewed_files, expires) in list(self._armed.items()):
            if time.monotonic() > expires:
                del self._armed[grant]
                continue
            if destination == reviewed_destination and files == reviewed_files:
                del self._armed[grant]
                return
        raise TransferBlocked("UPLOAD_BODY_NOT_REVIEWED")


def multipart_files(content_type: str, body: bytes) -> tuple[tuple[str, int, str], ...]:
    """Describe exact multipart file parts, without exporting their bytes."""
    from email import policy
    from email.parser import BytesParser

    if any(c in content_type for c in "\r\n"):
        raise TransferBlocked("UPLOAD_MULTIPART_INVALID")
    message = BytesParser(policy=policy.default).parsebytes(
        ("Content-Type: " + content_type + "\r\nMIME-Version: 1.0\r\n\r\n").encode("ascii") + body
    )
    if not message.is_multipart() or message.defects:
        raise TransferBlocked("UPLOAD_MULTIPART_INVALID")
    files = []
    for index, part in enumerate(message.iter_parts()):
        if index >= 100 or part.is_multipart() or part.defects:
            raise TransferBlocked("UPLOAD_MULTIPART_INVALID")
        filename = part.get_filename()
        if filename is None:
            continue
        if part.get("Content-Transfer-Encoding", "").lower() not in {"", "binary", "8bit"}:
            raise TransferBlocked("UPLOAD_ENCODING_UNSUPPORTED")
        payload = part.get_payload(decode=True)
        if not isinstance(payload, bytes):
            raise TransferBlocked("UPLOAD_MULTIPART_INVALID")
        files.append((filename, len(payload), hashlib.sha256(payload).hexdigest()))
    return tuple(files)
