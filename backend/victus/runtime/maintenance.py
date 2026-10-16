"""Short maintenance windows block mutations/admission, never read-only health."""

from contextlib import contextmanager

from victus.runtime.instance_lock import InstanceLock


class MaintenanceBusy(RuntimeError):
    pass


@contextmanager
def maintenance(tasks, root):
    with tasks.queue._admission_lock:
        if tasks.queue.active_task_id is not None or tasks.queue.queued_count:
            raise MaintenanceBusy("Finish or stop active tasks before maintenance")
        if not tasks.mutation_lock.acquire(blocking=False):
            raise MaintenanceBusy("Mutation worker is active")
        checkpoint_lock = None
        try:
            if (root / "agent").exists():
                checkpoint_lock = InstanceLock(root / "agent")
                checkpoint_lock.acquire()
            yield
        finally:
            if checkpoint_lock is not None:
                checkpoint_lock.release()
            tasks.mutation_lock.release()
