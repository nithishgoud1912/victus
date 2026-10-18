import os
from pathlib import Path
from typing import BinaryIO

# Failed cleanup must not lose OS ownership merely because its caller unwinds.
_RETAINED_LOCKS = set()


class InstanceLock:
    def __init__(self, root: Path) -> None:
        self.path = root / "instance.lock"
        self.stream: BinaryIO | None = None

    def acquire(self) -> None:
        stream = self.path.open("a+b")
        stream.seek(0, 2)
        if stream.tell() == 0:
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            stream.close()
            raise RuntimeError("Another VICTUS process owns this data directory") from exc
        self.stream = stream

    def release(self) -> None:
        if self.stream is not None:
            # Closing the handle releases the OS lock; keep the file itself.
            self.stream.close()
            self.stream = None
        _RETAINED_LOCKS.discard(self)

    def retain(self) -> None:
        """Keep failed-shutdown ownership alive until explicit safe cleanup."""
        if self.stream is not None:
            _RETAINED_LOCKS.add(self)
