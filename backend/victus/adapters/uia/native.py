"""Lazy Windows bindings. This module is safe to import on non-Windows hosts."""

import ctypes
import os
import subprocess

from victus.adapters.uia.actions import PatternUnavailable
from victus.adapters.uia.applications import ProcessIdentity, UIABlocked


class OwnedChildHandle:
    """Read-only process lease; closing it never terminates an application."""

    def __init__(self, kernel, handle, pid):
        self.kernel, self.handle, self.pid = kernel, handle, pid

    def poll(self):
        result = self.kernel.WaitForSingleObject(self.handle, 0)
        if result == 258:  # WAIT_TIMEOUT: the exact process is still alive.
            return None
        if result == 0:
            return 0
        raise UIABlocked("PROCESS_LEASE_UNAVAILABLE")

    def close(self):
        if self.handle is not None:
            self.kernel.CloseHandle(self.handle)
            self.handle = None


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

    def _process_entries(self):
        """Bounded OS snapshot, never used alone to assert ownership."""
        w = self.w

        class ProcessEntry(ctypes.Structure):
            _fields_ = [
                ("size", w.DWORD),
                ("usage", w.DWORD),
                ("pid", w.DWORD),
                ("heap", ctypes.c_size_t),
                ("module", w.DWORD),
                ("threads", w.DWORD),
                ("parent", w.DWORD),
                ("priority", w.LONG),
                ("flags", w.DWORD),
                ("image", w.WCHAR * 260),
            ]

        self.kernel.CreateToolhelp32Snapshot.argtypes = [w.DWORD, w.DWORD]
        self.kernel.CreateToolhelp32Snapshot.restype = w.HANDLE
        self.kernel.Process32FirstW.argtypes = [w.HANDLE, ctypes.POINTER(ProcessEntry)]
        self.kernel.Process32NextW.argtypes = [w.HANDLE, ctypes.POINTER(ProcessEntry)]
        snapshot = self.kernel.CreateToolhelp32Snapshot(2, 0)  # TH32CS_SNAPPROCESS
        if snapshot == ctypes.c_void_p(-1).value:
            raise UIABlocked("PROCESS_ANCESTRY_UNAVAILABLE")
        entries = []
        try:
            entry = ProcessEntry()
            entry.size = ctypes.sizeof(entry)
            found = self.kernel.Process32FirstW(snapshot, ctypes.byref(entry))
            if not found:
                raise UIABlocked("PROCESS_ANCESTRY_UNAVAILABLE")
            while found:
                entries.append((entry.pid, entry.parent, entry.image))
                found = self.kernel.Process32NextW(snapshot, ctypes.byref(entry))
            if ctypes.get_last_error() != 18:  # ERROR_NO_MORE_FILES
                raise UIABlocked("PROCESS_ANCESTRY_UNAVAILABLE")
        finally:
            self.kernel.CloseHandle(snapshot)
        return entries

    def owned_children(self, parent):
        """Direct children only; pin the live launcher before and after snapshot."""
        if self.identity(parent.pid) != parent:
            raise UIABlocked("LAUNCHER_IDENTITY_CHANGED")
        children = []
        for pid, parent_pid, _ in self._process_entries():
            if parent_pid == parent.pid:
                try:
                    children.append(self.identity(pid))
                except UIABlocked:
                    raise UIABlocked("PROCESS_ANCESTRY_UNAVAILABLE") from None
        if self.identity(parent.pid) != parent:
            raise UIABlocked("LAUNCHER_IDENTITY_CHANGED")
        return children

    def launch_observations(self, executable):
        """Read identities/handles only; no window titles, document trees or text.

        An observed new window in an old process is diagnostic evidence of possible
        delegation, never authority to connect, edit, close or terminate that process.
        """
        identities = {}
        truncated = 0
        for pid, _, image in self._process_entries():
            if image.casefold() != executable.name.casefold():
                continue
            identity = self.identity(pid)
            if os.path.normcase(identity.executable) == os.path.normcase(str(executable)):
                if len(identities) >= 32:
                    truncated = 1
                    break
                identities[pid] = identity
        windows = []
        callback_type = ctypes.WINFUNCTYPE(self.w.BOOL, self.w.HWND, self.w.LPARAM)

        def observe(hwnd, _):
            nonlocal truncated
            pid = self.w.DWORD()
            self.user.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value in identities:
                if len(windows) >= 32:
                    truncated = 1
                else:
                    windows.append(
                        {
                            "owned_pid": pid.value,
                            "window_handle": int(hwnd),
                            "window_visible": int(bool(self.user.IsWindowVisible(hwnd))),
                        }
                    )
            return True

        self.user.EnumWindows.argtypes = [callback_type, self.w.LPARAM]
        self.user.EnumWindows.restype = self.w.BOOL
        self.user.IsWindowVisible.argtypes = [self.w.HWND]
        self.user.IsWindowVisible.restype = self.w.BOOL
        if not self.user.EnumWindows(callback_type(observe), 0):
            raise UIABlocked("WINDOW_INVENTORY_UNAVAILABLE")
        # Reject a torn process snapshot instead of associating handles with a reused PID.
        if any(self.identity(pid) != identity for pid, identity in identities.items()):
            raise UIABlocked("PROCESS_INVENTORY_CHANGED")
        return [
            {
                "matching_processes": len(identities),
                "matching_windows": len(windows),
                "inventory_truncated": truncated,
            },
            *[{"owned_pid": x.pid, "process_created": x.created} for x in identities.values()],
            *windows,
        ]

    def track_owned_child(self, parent, child):
        if child not in self.owned_children(parent):
            raise UIABlocked("OWNED_CHILD_IDENTITY_CHANGED")
        handle = self.kernel.OpenProcess(0x00101000, False, child.pid)  # SYNCHRONIZE | QUERY
        if not handle:
            raise UIABlocked("PROCESS_LEASE_UNAVAILABLE")
        self.kernel.WaitForSingleObject.argtypes = [self.w.HANDLE, self.w.DWORD]
        self.kernel.WaitForSingleObject.restype = self.w.DWORD
        lease = OwnedChildHandle(self.kernel, handle, child.pid)
        try:
            if lease.poll() is not None or self.identity(child.pid) != child:
                raise UIABlocked("OWNED_CHILD_IDENTITY_CHANGED")
        except BaseException:
            lease.close()
            raise
        return lease

    def set_value(self, control, text):
        try:
            interface = control.iface_value
        except self.NoPattern:
            raise PatternUnavailable from None
        if interface.CurrentIsReadOnly:
            raise UIABlocked("CONTROL_READONLY")
        interface.SetValue(text)

    def read_value(self, control):
        try:
            return control.iface_value.CurrentValue
        except self.NoPattern:
            raise PatternUnavailable from None

    def read_text(self, control):
        return control.iface_text.DocumentRange.GetText(4097)

    def window_dpi(self, root):
        getter = getattr(self.user, "GetDpiForWindow", None)
        if getter is None:
            return None
        getter.argtypes = [self.w.HWND]
        getter.restype = self.w.UINT
        return getter(root.handle) or None

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
