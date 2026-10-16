from dataclasses import dataclass

from victus.memory.retention import RetentionService
from victus.memory.service import MemoryService
from victus.models.cloud_service import CloudService
from victus.recovery.resume import ResumeManager
from victus.runtime.diagnostics import Diagnostics
from victus.runtime.hotkey import EmergencyShortcut
from victus.runtime.instance_lock import InstanceLock
from victus.runtime.maintenance import maintenance
from victus.runtime.resources import ResourceSupervisor, resources
from victus.safety.approvals import ApprovalStore
from victus.settings import Settings
from victus.storage.action_ledger import ActionLedger
from victus.storage.backups import Backups
from victus.storage.database import Database
from victus.storage.payloads import PayloadStore
from victus.tasks.events import EventManager
from victus.tasks.service import TaskService
from victus.tools.browser import BROWSER_TOOLS
from victus.tools.desktop import DESKTOP_TOOLS
from victus.tools.filesystem import FILESYSTEM_TOOLS
from victus.tools.registry import ToolRegistry
from victus.voice.service import VoiceService
from victus.voice.wake import WakeListener


@dataclass
class Services:
    settings: Settings
    tasks: TaskService
    ledger: ActionLedger
    payloads: PayloadStore
    lock: InstanceLock
    events: EventManager
    hotkey: EmergencyShortcut | None = None
    voice: VoiceService | None = None
    memory: MemoryService | None = None
    retention: RetentionService | None = None
    resources: ResourceSupervisor | None = None
    backups: Backups | None = None
    diagnostics: Diagnostics | None = None
    cloud: CloudService | None = None

    @property
    def approvals(self) -> ApprovalStore:
        return ApprovalStore(self.ledger.db_path)

    def stop(self) -> None:
        # Trip both independent cancellation paths before queue/storage cleanup.
        self.tasks.cancellation.stop()
        if self.cloud is not None:
            self.cloud.clear()
        if self.voice is not None:
            self.voice.stop()
        self.tasks.stop()

    def close(self) -> None:
        if self.cloud is not None:
            self.cloud.clear()
        if self.hotkey is not None:
            self.hotkey.close()
        if self.voice is not None:
            self.voice.close()
        if self.retention is not None:
            self.retention.close()
        self.tasks.close()
        try:
            if self.retention is not None:
                self.retention.cleanup(end_session=True)
        finally:
            if self.resources is not None:
                self.resources.close()
            self.lock.release()


def build_services(settings: Settings) -> Services:
    settings.initialize()
    lock = InstanceLock(settings.data_dir)
    lock.acquire()
    tasks = None
    hotkey = None
    voice = None
    resource_started = False
    retention = None
    try:
        registry = ToolRegistry()
        for spec in FILESYSTEM_TOOLS + BROWSER_TOOLS + DESKTOP_TOOLS:
            if settings.mcp_notes and spec.name == "fs.create_note":
                from victus.adapters.mcp.mapping import mcp_create_note

                spec = mcp_create_note()
            registry.register(spec)
        database = Database(settings.data_dir)
        db_path = database.path
        ledger = ActionLedger(db_path)
        approvals = ApprovalStore(db_path)
        # Crash/startup recovery retires previous authority. Ordinary live review
        # pauses resume separately through the graph's review interrupt.
        approvals.purge_expired()
        ResumeManager(ledger, approvals).recover(quiesced=True)
        payloads = PayloadStore(db_path)
        events = EventManager(db_path)
        tasks = TaskService(settings.workspace, database, registry, events)
        voice = VoiceService(tasks, settings.voice_model_path)
        voice.wake = WakeListener(voice, settings.wake_manifest_path)
        resources().start()
        resource_started = True

        def guard():
            return maintenance(tasks, settings.data_dir)

        memory = MemoryService(settings.data_dir, guard)
        retention = RetentionService(settings.data_dir, guard, memory)
        memory.finish_pending()
        retention.cleanup(end_session=True)
        services = Services(
            settings,
            tasks,
            ledger,
            payloads,
            lock,
            events,
            voice=voice,
            memory=memory,
            retention=retention,
            resources=resources(),
            backups=Backups(settings.data_dir, guard),
            diagnostics=Diagnostics(resources()),
            cloud=(CloudService(settings.cloud_model, settings.cloud_upstream, tasks.stopped)
                   if settings.cloud_model else None),
        )
        if settings.emergency_hotkey:
            hotkey = EmergencyShortcut(services.stop)
            hotkey.start()
        services.hotkey = hotkey
        retention.start()
        return services
    except Exception:
        if hotkey is not None:
            hotkey.close()
        if voice is not None:
            voice.close()
        if tasks is not None:
            tasks.close()
        if retention is not None:
            retention.close()
        if resource_started:
            resources().close()
        lock.release()
        raise
