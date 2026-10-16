"""One mutation slot shared by browser, desktop and filesystem operations."""

from victus.runtime.resources import resources


class MutationLocks:
    def __init__(self) -> None:
        self.mutation = resources().mutation
