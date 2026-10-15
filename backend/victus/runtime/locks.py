"""One mutation slot shared by browser, desktop and filesystem operations."""

from threading import Lock


class MutationLocks:
    def __init__(self) -> None:
        self.mutation = Lock()
