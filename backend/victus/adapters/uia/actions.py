"""UIA patterns first, explicit foreground-checked keyboard fallback second."""

from dataclasses import dataclass

from victus.adapters.uia.applications import UIABlocked, UIAUncertain
from victus.adapters.uia.selectors import ControlReference, SelectorResolver


class PatternUnavailable(Exception):
    """Only an absent pattern, not a failed native action, permits fallback."""


@dataclass(frozen=True)
class UIAResult:
    status: str
    method: str


class UIAActions:
    def __init__(self, resolver: SelectorResolver):
        self.resolver = resolver

    def _keyboard_ready(self, reference, *, allow_keyboard):
        app, root, control = self.resolver._reacquire(reference)
        if not allow_keyboard or not app.profile.allow_keyboard_fallback:
            raise UIABlocked("KEYBOARD_FALLBACK_NOT_REVIEWED")
        return app, root, control

    def _check_foreground(self, reference):
        app, root, control = self.resolver._reacquire(reference)
        backend = self.resolver.worker._backend
        if not control.has_keyboard_focus() or not backend.is_foreground(root, app.identity.pid):
            raise UIABlocked("FOREGROUND_OR_FOCUS_CHANGED")
        return control

    @staticmethod
    def _focus(control):
        try:
            control.set_focus()
        except Exception:
            raise UIABlocked("FOCUS_UNAVAILABLE") from None

    def set_text(
        self, reference: ControlReference, text: str, *, allow_keyboard=False
    ) -> UIAResult:
        if not isinstance(text, str) or len(text) > 4096:
            raise UIABlocked("TEXT_LIMIT")
        _, _, control = self.resolver._reacquire(reference)
        backend = self.resolver.worker._backend
        try:
            backend.set_value(control, text)
        except PatternUnavailable:
            _, _, control = self._keyboard_ready(reference, allow_keyboard=allow_keyboard)
            if control.element_info.control_type not in {"Edit", "Document"}:
                raise UIABlocked("KEYBOARD_EDITOR_UNSUPPORTED")
            try:
                if backend.read_text(control) != "":
                    raise UIABlocked("KEYBOARD_REPLACEMENT_UNSUPPORTED")
            except UIABlocked:
                raise
            except Exception:
                raise UIABlocked("EMPTY_EDITOR_NOT_PROVED") from None
            self._focus(control)
            # Native Unicode input does not interpret braces, Ctrl/Alt syntax or commands.
            # Empty text cannot erase a field without a qualified value pattern.
            if not text:
                raise UIABlocked("KEYBOARD_EMPTY_VALUE_UNSUPPORTED")
            encoded = text.encode("utf-16-le")
            for offset in range(0, len(encoded), 2):
                try:
                    self._check_foreground(reference)  # Immediately before EACH SendInput call.
                except UIABlocked:
                    if offset:
                        raise UIAUncertain("KEYBOARD_WRITE_INTERRUPTED") from None
                    raise
                unit = int.from_bytes(encoded[offset : offset + 2], "little")
                try:
                    backend.send_unicode(unit)
                except Exception:
                    raise UIAUncertain("KEYBOARD_WRITE_UNCERTAIN") from None
            return UIAResult("unverified", "keyboard_unicode")
        except UIABlocked:
            raise
        except Exception:
            raise UIAUncertain("VALUE_WRITE_UNCERTAIN") from None
        # Reacquire again and read independently; native SetValue returning is not proof.
        try:
            _, _, current = self.resolver._reacquire(reference)
            verified = backend.read_value(current) == text
        except Exception:
            verified = False
        return UIAResult("verified" if verified else "unverified", "value_pattern")

    def invoke(self, reference: ControlReference, *, allow_keyboard=False) -> UIAResult:
        _, _, control = self.resolver._reacquire(reference)
        backend = self.resolver.worker._backend
        try:
            backend.invoke(control)
        except PatternUnavailable:
            _, _, control = self._keyboard_ready(reference, allow_keyboard=allow_keyboard)
            if control.element_info.control_type not in {"Button", "Hyperlink", "MenuItem"}:
                raise UIABlocked("KEYBOARD_INVOKE_UNSUPPORTED")
            self._focus(control)
            self._check_foreground(reference)
            try:
                backend.send_enter()
            except Exception:
                raise UIAUncertain("KEYBOARD_INVOKE_UNCERTAIN") from None
            return UIAResult("unverified", "keyboard_enter")
        except Exception:
            raise UIAUncertain("INVOKE_UNCERTAIN") from None
        # Application-specific postconditions belong to workflow verifiers in 6E.
        return UIAResult("unverified", "invoke_pattern")
