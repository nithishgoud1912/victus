from dataclasses import dataclass

from victus.runtime.instance_lock import InstanceLock
from victus.settings import Settings
from victus.storage.action_ledger import ActionLedger
from victus.storage.database import Database
from victus.storage.payloads import PayloadStore
from victus.tasks.service import TaskService
from victus.tools.browser import BROWSER_TOOLS
from victus.tools.desktop import DESKTOP_TOOLS
from victus.tools.filesystem import FILESYSTEM_TOOLS
from victus.tools.registry import ToolRegistry


@dataclass
class Services:
    settings: Settings
    tasks: TaskService
    ledger: ActionLedger
    payloads: PayloadStore
    lock: InstanceLock

    def close(self) -> None:
        self.tasks.stop()
        self.lock.release()


def build_services(settings: Settings) -> Services:
    settings.initialize()
    lock = InstanceLock(settings.data_dir)
    lock.acquire()
    try:
        registry = ToolRegistry()
        for spec in FILESYSTEM_TOOLS + BROWSER_TOOLS + DESKTOP_TOOLS:
            registry.register(spec)
        database = Database(settings.data_dir)
        db_path = database.path
        ledger = ActionLedger(db_path)
        payloads = PayloadStore(db_path)
        tasks = TaskService(settings.workspace, database, registry)
        return Services(settings, tasks, ledger, payloads, lock)
    except Exception:
        lock.release()
        raise