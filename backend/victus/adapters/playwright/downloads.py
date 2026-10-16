"""Private staging and single-use, content/destination-bound release permits."""

from __future__ import annotations

import hashlib
import os
import stat
import time
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4


class TransferBlocked(ValueError):
    pass


@dataclass(frozen=True)
class DownloadReceipt:
    download_id: str
    task_id: str
    size: int
    sha256: str


def read_reviewed_file(path: Path, limit: int) -> bytes:
    if path.is_symlink():
        raise TransferBlocked("LINKED_FILE_NOT_ALLOWED")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise TransferBlocked("REGULAR_FILE_REQUIRED")
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise TransferBlocked("FILE_TOO_LARGE")
    return data


class DownloadStaging:
    def __init__(
        self,
        data_dir: Path,
        task_id: str,
        *,
        destination_roots: tuple[Path, ...],
        max_bytes: int = 10_000_000,
        max_files: int = 32,
    ):
        if not task_id or not 1 <= max_bytes <= 50_000_000 or not 1 <= max_files <= 100:
            raise ValueError("Invalid staging limits")
        root = data_dir.resolve()
        self._root = root / "download-staging"
        self._root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self._root.is_symlink() or self._root.resolve().parent != root:
            raise TransferBlocked("STAGING_ROOT_UNSAFE")
        self.task_id = task_id
        self._destinations = frozenset(path.resolve(strict=True) for path in destination_roots)
        self._max_bytes = max_bytes
        self._max_files = max_files
        self._records = {}
        self._permits = {}

    def stage_bytes(self, data: bytes) -> DownloadReceipt:
        if len(data) > self._max_bytes or len(self._records) >= self._max_files:
            raise TransferBlocked("STAGING_LIMIT")
        ref = uuid4().hex
        path = self._root / ref
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
        except BaseException:
            path.unlink(missing_ok=True)
            raise
        receipt = DownloadReceipt(ref, self.task_id, len(data), hashlib.sha256(data).hexdigest())
        self._records[ref] = receipt
        return receipt

    def _destination(self, destination: Path) -> Path:
        if not destination.is_absolute() or destination.parent.resolve() not in self._destinations:
            raise TransferBlocked("DESTINATION_OUTSIDE_SCOPE")
        name = destination.name
        if (
            not name
            or name.endswith((".", " "))
            or any(c in name for c in ':<>"|?*\\')
            or any(ord(c) < 32 for c in name)
            or name.split(".")[0].rstrip(" .").upper()
            in {
                "CON",
                "PRN",
                "AUX",
                "NUL",
                "CONIN$",
                "CONOUT$",
                *(f"{prefix}{n}" for prefix in ("COM", "LPT") for n in range(1, 10)),
                *(f"{prefix}{n}" for prefix in ("COM", "LPT") for n in "¹²³"),
            }
        ):
            raise TransferBlocked("DESTINATION_NAME_UNSAFE")
        destination = destination.parent.resolve() / name
        if destination.exists() or destination.is_symlink():
            raise TransferBlocked("DESTINATION_EXISTS")
        return destination

    def approve_release(self, receipt: DownloadReceipt, destination: Path) -> str:
        """Trusted policy entry point AFTER explicit review; never a model tool."""
        if len(self._permits) >= 64:
            raise TransferBlocked("RELEASE_PERMIT_LIMIT")
        if self._records.get(receipt.download_id) != receipt:
            raise TransferBlocked("DOWNLOAD_UNKNOWN_OR_FOREIGN")
        dest = self._destination(destination)
        permit = uuid4().hex
        self._permits[permit] = (receipt, dest, time.monotonic() + 60)
        return permit

    def release(self, permit: str) -> Path:
        approved = self._permits.pop(permit, None)
        if approved is None or time.monotonic() > approved[2]:
            raise TransferBlocked("RELEASE_PERMIT_INVALID")
        receipt, destination, _ = approved
        if self._records.get(receipt.download_id) != receipt:
            raise TransferBlocked("DOWNLOAD_UNKNOWN_OR_FOREIGN")
        destination = self._destination(destination)
        source = self._root / receipt.download_id
        data = read_reviewed_file(source, self._max_bytes)
        if hashlib.sha256(data).hexdigest() != receipt.sha256 or len(data) != receipt.size:
            raise TransferBlocked("STAGED_CONTENT_CHANGED")
        fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
        except BaseException:
            destination.unlink(missing_ok=True)
            raise
        self._records.pop(receipt.download_id)
        source.unlink()
        return destination

    def discard(self, receipt: DownloadReceipt):
        if self._records.get(receipt.download_id) != receipt:
            raise TransferBlocked("DOWNLOAD_UNKNOWN_OR_FOREIGN")
        (self._root / receipt.download_id).unlink(missing_ok=True)
        del self._records[receipt.download_id]
