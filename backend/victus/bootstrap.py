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
from victus.tools.filesystem import FILESYSTEM_TOOLS
from victus.tools.registry import ToolRegistry
from victus.voice.service import VoiceService
from victus.voice.wake import WakeListener


def _cleanup_all(operations):
    """Attempt independent cleanup even if an optional component fails."""
    errors = []
    for operation in operations:
        try:
            operation()
        except Exception as error:
            errors.append(error)
    return errors


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
    commands: object = None
    fixture_site: object = None

    @property
    def approvals(self) -> ApprovalStore:
        return ApprovalStore(self.ledger.db_path)

    def stop(self) -> None:
        # Trip both independent cancellation paths before queue/storage cleanup.
        self.tasks.cancellation.stop()
        operations = [self.tasks.stop]
        if self.cloud is not None:
            operations.append(self.cloud.clear)
        if self.voice is not None:
            operations.append(self.voice.stop)
        if _cleanup_all(operations):
            raise RuntimeError("Stop latched; component cleanup incomplete") from None

    def close(self) -> None:
        # Latch Stop before any optional cleanup can block or fail. Task close
        # signals, drains and joins its owned worker before other owners close.
        self.tasks.cancellation.stop()
        operations = [self.tasks.close]
        if self.fixture_site is not None:
            operations.append(self.fixture_site.close)
        if self.cloud is not None:
            operations.append(self.cloud.clear)
        if self.hotkey is not None:
            operations.append(self.hotkey.close)
        if self.voice is not None:
            operations.append(self.voice.close)
        if self.retention is not None:
            operations.append(self.retention.close)
        errors = _cleanup_all(operations)
        if errors:
            self.lock.retain()
            raise RuntimeError(
                "Service shutdown incomplete; data-directory ownership retained"
            ) from None
        try:
            if self.retention is not None:
                self.retention.cleanup(end_session=True)
            if self.resources is not None:
                self.resources.close()
        except Exception:
            self.lock.retain()
            raise RuntimeError(
                "Service cleanup incomplete; data-directory ownership retained"
            ) from None
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
    fixture_site = None
    try:
        registry = ToolRegistry()
        # Native workflow-local registries bind reviewed owners/targets separately.
        # Never advertise unimplemented browser or broad desktop stubs as runnable.
        # Only server-owned, exact-runtime qualification can enable native tools.
        for spec in FILESYSTEM_TOOLS:
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
        from victus.workflows.qualification_records import qualified_native

        native = qualified_native()
        if native is not None:
            from victus.workflows.native_review import native_checklist_spec

            registry.register(native_checklist_spec(native.profiles_file, native.profiles,
                native_qualified=True, review_qualified=True))
            tasks.qualified_notepad_profiles = native.profiles
            tasks.reviewed_notepad_profiles = native.profiles
        from victus.models.contracts import ModelPin
        from victus.tasks.commands import CommandService
        from victus.workflows.fixture_research import (
            FixtureSite,
            ResearchExecutor,
            qualified_browser,
        )

        browser = qualified_browser()
        if browser is not None:
            fixture_site = FixtureSite()
            tasks.research = ResearchExecutor(fixture_site.origin, str(browser))
            registry.register(tasks.research.spec())
        commands = CommandService(tasks, ModelPin(name=settings.command_model_name,
            digest=settings.command_model_digest) if settings.command_model_name else None)
        voice = VoiceService(tasks, settings.voice_model_path, commands=commands)
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
            cloud=(
                CloudService(settings.cloud_model, settings.cloud_upstream, tasks.stopped)
                if settings.cloud_model
                else None
            ),
            commands=commands, fixture_site=fixture_site,
        )
        if settings.emergency_hotkey:
            hotkey = EmergencyShortcut(services.stop)
            hotkey.start()
        services.hotkey = hotkey
        retention.start()
        return services
    except Exception:
        operations = []
        if fixture_site is not None:
            operations.append(fixture_site.close)
        if tasks is not None:
            operations.append(tasks.close)
        if hotkey is not None:
            operations.append(hotkey.close)
        if voice is not None:
            operations.append(voice.close)
        if retention is not None:
            operations.append(retention.close)
        if resource_started:
            operations.append(resources().close)
        if _cleanup_all(operations):
            lock.retain()
        else:
            lock.release()
        raise
