"""Lazy Windows bindings. This module is safe to import on non-Windows hosts."""

import ctypes
import os
import subprocess

from victus.adapters.uia.actions import PatternUnavailable
from victus.adapters.uia.applications import ProcessIdentity, UIABlocked


class WindowsBackend:
    def initialize(self):
        self._expected_foreground = None
        if os.name != "nt":
            raise UIABlocked("WINDOWS_UIA_UNAVAILABLE")
        from ctypes import wintypes

        self.w = wintypes
        self.ole = ctypes.WinDLL("ole32")
        self.ole.CoInitializeEx.argtypes = [ctypes.c_void_p, wintypes.DWORD]
        self.ole.CoInitializeEx.restype = ctypes.c_long
        result = self.ole.CoInitializeEx(None, 0)  # MTA, consistently on the worker thread.
        if result < 0:
            raise UIABlocked("COM_APARTMENT_UNAVAILABLE")
        try:
            # Import after apartment initialization; no UIA objects on the API thread.
            from pywinauto import Application
            from pywinauto.uia_defines import NoPatternInterfaceError

            self.Application = Application
            self.NoPattern = NoPatternInterfaceError
            self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            self.user = ctypes.WinDLL("user32", use_last_error=True)
            self.kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            self.kernel.OpenProcess.restype = wintypes.HANDLE
            self.kernel.CloseHandle.argtypes = [wintypes.HANDLE]
            self.kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [
                ctypes.POINTER(wintypes.FILETIME)
            ] * 4
            self.kernel.QueryFullProcessImageNameW.argtypes = [
                wintypes.HANDLE,
                wintypes.DWORD,
                wintypes.LPWSTR,
                ctypes.POINTER(wintypes.DWORD),
            ]
            self.user.GetForegroundWindow.restype = wintypes.HWND
            self.user.GetWindowThreadProcessId.argtypes = [
                wintypes.HWND,
                ctypes.POINTER(wintypes.DWORD),
            ]
        except BaseException:
            self.ole.CoUninitialize()
            raise

    def uninitialize(self):
        self.ole.CoUninitialize()

    def launch(self, executable, arguments):
        return subprocess.Popen(
            [str(executable), *arguments],
            shell=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )

    def terminate_owned(self, process):
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2)

    def identity(self, pid):
        handle = self.kernel.OpenProcess(0x1000, False, pid)  # QUERY_LIMITED_INFORMATION
        if not handle:
            raise UIABlocked("PROCESS_UNAVAILABLE")
        try:
            times = [self.w.FILETIME() for _ in range(4)]
            if not self.kernel.GetProcessTimes(handle, *(ctypes.byref(value) for value in times)):
                raise UIABlocked("PROCESS_IDENTITY_UNAVAILABLE")
            size = self.w.DWORD(32768)
            path = ctypes.create_unicode_buffer(size.value)
            if not self.kernel.QueryFullProcessImageNameW(handle, 0, path, ctypes.byref(size)):
                raise UIABlocked("PROCESS_IMAGE_UNAVAILABLE")
            created = (times[0].dwHighDateTime << 32) | times[0].dwLowDateTime
            return ProcessIdentity(pid, created, path.value)
        finally:
            self.kernel.CloseHandle(handle)

    def connect(self, pid):
        return self.Application(backend="uia").connect(process=pid, timeout=5)

    def set_value(self, control, text):
        try:
            interface = control.iface_value
        except self.NoPattern:
            raise PatternUnavailable from None
        if interface.CurrentIsReadOnly:
            raise UIABlocked("CONTROL_READONLY")
        interface.SetValue(text)

    def read_value(self, control):
        return control.iface_value.CurrentValue

    def read_text(self, control):
        return control.iface_text.DocumentRange.GetText(4097)

    def invoke(self, control):
        try:
            interface = control.iface_invoke
        except self.NoPattern:
            raise PatternUnavailable from None
        interface.Invoke()

    def is_foreground(self, root, pid):
        self._expected_foreground = None
        matched = self._foreground_matches(root.handle, pid)
        if matched:
            self._expected_foreground = (root.handle, pid)
        return matched

    def _foreground_matches(self, expected_handle, pid):
        hwnd = self.user.GetForegroundWindow()
        actual_pid = self.w.DWORD()
        self.user.GetWindowThreadProcessId(hwnd, ctypes.byref(actual_pid))
        return hwnd == expected_handle and actual_pid.value == pid

    def _send(self, scan, flags, vk=0):
        w = self.w

        class Keyboard(ctypes.Structure):
            _fields_ = [
                ("wVk", w.WORD),
                ("wScan", w.WORD),
                ("dwFlags", w.DWORD),
                ("time", w.DWORD),
                ("extra", ctypes.c_size_t),
            ]

        class Mouse(ctypes.Structure):
            _fields_ = [
                ("dx", w.LONG),
                ("dy", w.LONG),
                ("data", w.DWORD),
                ("flags", w.DWORD),
                ("time", w.DWORD),
                ("extra", ctypes.c_size_t),
            ]

        class Hardware(ctypes.Structure):
            _fields_ = [("message", w.DWORD), ("low", w.WORD), ("high", w.WORD)]

        class Value(ctypes.Union):
            _fields_ = [("keyboard", Keyboard), ("mouse", Mouse), ("hardware", Hardware)]

        class Input(ctypes.Structure):
            _fields_ = [("type", w.DWORD), ("value", Value)]

        inputs = (Input * 2)()
        for i, extra_flags in enumerate((0, 2)):
            inputs[i].type = 1
            inputs[i].value.keyboard = Keyboard(vk, scan, flags | extra_flags, 0, 0)
        self.user.SendInput.argtypes = [w.UINT, ctypes.POINTER(Input), ctypes.c_int]
        expected = self._expected_foreground
        self._expected_foreground = None  # Each key consumes a fresh foreground check.
        if expected is None or not self._foreground_matches(*expected):
            raise UIABlocked("FOREGROUND_CHANGED_BEFORE_SEND")
        if self.user.SendInput(2, inputs, ctypes.sizeof(Input)) != 2:
            raise UIABlocked("SEND_INPUT_FAILED")

    def send_unicode(self, unit):
        self._send(unit, 4)  # KEYEVENTF_UNICODE, paired keydown/keyup.

    def send_enter(self):
        self._send(0, 0, 13)
