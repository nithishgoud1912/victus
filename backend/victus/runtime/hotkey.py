"""Opt-in Ctrl+Alt+Pause emergency shortcut, registered on its own Windows thread."""

from __future__ import annotations

import ctypes
import os
import threading
from collections.abc import Callable
from ctypes import wintypes


class WindowsHotkey:
    HOTKEY_ID = 0x5649

    def __init__(self) -> None:
        if os.name != "nt":
            raise OSError("Windows hotkey unavailable")
        self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        self.user32.RegisterHotKey.argtypes = [
            wintypes.HWND,
            ctypes.c_int,
            wintypes.UINT,
            wintypes.UINT,
        ]
        self.user32.RegisterHotKey.restype = wintypes.BOOL
        self.user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
        self.user32.UnregisterHotKey.restype = wintypes.BOOL
        self.user32.PeekMessageW.argtypes = [
            ctypes.POINTER(wintypes.MSG),
            wintypes.HWND,
            wintypes.UINT,
            wintypes.UINT,
            wintypes.UINT,
        ]
        self.user32.PeekMessageW.restype = wintypes.BOOL

    def register(self) -> bool:
        # MOD_ALT | MOD_CONTROL | MOD_NOREPEAT; VK_PAUSE.
        return bool(self.user32.RegisterHotKey(None, self.HOTKEY_ID, 0x4003, 0x13))

    def pressed(self) -> bool:
        message = wintypes.MSG()
        pressed = False
        while self.user32.PeekMessageW(ctypes.byref(message), None, 0x0312, 0x0312, 1):
            pressed |= message.wParam == self.HOTKEY_ID
        return pressed

    def unregister(self) -> None:
        self.user32.UnregisterHotKey(None, self.HOTKEY_ID)


class EmergencyShortcut:
    def __init__(self, stop: Callable[[], None], backend_factory: Callable = WindowsHotkey) -> None:
        self._stop = stop
        self._backend_factory = backend_factory
        self._closing = threading.Event()
        self._ready = threading.Event()
        self.status = "starting"
        self._thread = threading.Thread(
            target=self._listen, name="victus-emergency-key", daemon=True
        )

    def start(self) -> None:
        self._thread.start()
        if not self._ready.wait(timeout=2):
            self.close()
            raise RuntimeError("Emergency shortcut startup timed out")

    def _listen(self) -> None:
        backend = None
        registered = False
        try:
            backend = self._backend_factory()
            registered = backend.register()
            self.status = "registered" if registered else "unavailable_or_in_use"
            self._ready.set()
            if not registered:
                return
            while not self._closing.wait(0.05):
                if backend.pressed():
                    self._stop()
        except Exception:
            self.status = "error"
            self._ready.set()
        finally:
            if registered and backend is not None:
                backend.unregister()

    def close(self) -> None:
        self._closing.set()
        self._thread.join(timeout=2)
        if self._thread.is_alive():
            raise RuntimeError("Emergency shortcut did not shut down")
