"""Exact profile selectors, restricted to one live process and window identity."""

from dataclasses import dataclass
from uuid import uuid4

from victus.adapters.uia.applications import ApplicationReference, UIABlocked, UIAWorker


@dataclass(frozen=True)
class ControlReference:
    ref: str


def _matches(control, selector, pid):
    info = control.element_info
    return (
        info.process_id == pid
        and info.control_type == selector.control_type
        and (selector.automation_id is None or info.automation_id == selector.automation_id)
        and (selector.name is None or info.name == selector.name)
    )


class SelectorResolver:
    def __init__(self, worker: UIAWorker):
        self.worker = worker

    def _find(self, application, key):
        app = self.worker._resolve_app(application)
        selector = app.profile.controls.get(key)
        if selector is None:
            raise UIABlocked("CONTROL_NOT_IN_PROFILE")
        windows = [
            window
            for window in app.connection.windows()
            if _matches(window, app.profile.window, app.identity.pid)
        ]
        if len(windows) != 1:
            raise UIABlocked("WINDOW_MISSING_OR_AMBIGUOUS")
        root = windows[0]
        if not root.is_visible() or not root.is_enabled():
            raise UIABlocked("WINDOW_NOT_ACTIONABLE")
        controls = [
            control
            for control in root.descendants(control_type=selector.control_type)
            if _matches(control, selector, app.identity.pid)
        ]
        if len(controls) != 1:
            raise UIABlocked("CONTROL_MISSING_OR_AMBIGUOUS")
        control = controls[0]
        if not control.is_visible() or not control.is_enabled():
            raise UIABlocked("CONTROL_NOT_ACTIONABLE")
        return app, root, control

    def resolve(self, application: ApplicationReference, key: str) -> ControlReference:
        _, root, control = self._find(application, key)
        if len(self.worker._controls) >= 128:
            raise UIABlocked("CONTROL_REFERENCE_LIMIT")
        ref = uuid4().hex
        self.worker._controls[ref] = (
            application,
            key,
            tuple(root.element_info.runtime_id),
            tuple(control.element_info.runtime_id),
        )
        return ControlReference(ref)

    def _reacquire(self, reference: ControlReference):
        self.worker._check_owner()
        record = self.worker._controls.get(reference.ref)
        if record is None:
            raise UIABlocked("CONTROL_REFERENCE_UNKNOWN")
        application, key, root_id, control_id = record
        app, root, control = self._find(application, key)
        if (tuple(root.element_info.runtime_id), tuple(control.element_info.runtime_id)) != (
            root_id,
            control_id,
        ):
            raise UIABlocked("CONTROL_REPLACED_REACQUIRE")
        return app, root, control
