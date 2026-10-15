from dataclasses import dataclass

from victus.runtime.hotkey import EmergencyShortcut
from victus.runtime.instance_lock import InstanceLock
from victus.settings import Settings
from victus.storage.action_ledger import ActionLedger
from victus.storage.database import Database
from victus.storage.payloads import PayloadStore
from victus.tasks.events import EventManager
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
    events: EventManager
    hotkey: EmergencyShortcut | None = None

    def close(self) -> None:
        if self.hotkey is not None:
            self.hotkey.close()
        self.tasks.close()
        self.lock.release()


def build_services(settings: Settings) -> Services:
    settings.initialize()
    lock = InstanceLock(settings.data_dir)
    lock.acquire()
    tasks = None
    hotkey = None
    try:
        registry = ToolRegistry()
        for spec in FILESYSTEM_TOOLS + BROWSER_TOOLS + DESKTOP_TOOLS:
            registry.register(spec)
        database = Database(settings.data_dir)
        db_path = database.path
        ledger = ActionLedger(db_path)
        for action in ledger.list_unfinished():
            if action.status == "prepared":
                ledger.mark_cancelled(action.action_id)
            else:
                ledger.mark_unknown(action.action_id, error_code="RESTART_REQUIRES_REVIEW")
        payloads = PayloadStore(db_path)
        events = EventManager(db_path)
        tasks = TaskService(settings.workspace, database, registry, events)
        if settings.emergency_hotkey:
            hotkey = EmergencyShortcut(tasks.stop)
            hotkey.start()
        return Services(settings, tasks, ledger, payloads, lock, events, hotkey)
    except Exception:
        if hotkey is not None:
            hotkey.close()
        if tasks is not None:
            tasks.close()
        lock.release()
        raise
