"""Preview encryption on Windows; private-file storage on POSIX.

DPAPI is bound to the current Windows user. It does not protect against another
process running as that user. Retention is logical deletion, not forensic erase.
"""

import ctypes
import os
from ctypes import wintypes


class _Blob(ctypes.Structure):
    _fields_ = [("size", wintypes.DWORD), ("data", ctypes.POINTER(ctypes.c_ubyte))]


def _dpapi(data: bytes, *, decrypt: bool) -> bytes:
    crypt = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    buffer = ctypes.create_string_buffer(data)
    source = _Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    destination = _Blob()
    function = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    function.argtypes = [
        ctypes.POINTER(_Blob),
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(_Blob),
    ]
    function.restype = wintypes.BOOL
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    # CRYPTPROTECT_UI_FORBIDDEN: service code must never trigger a UI prompt.
    if not function(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(destination)):
        raise OSError("Preview protection unavailable")
    try:
        return ctypes.string_at(destination.data, destination.size)
    finally:
        kernel.LocalFree(destination.data)


def protect(data: bytes) -> bytes:
    return b"dpapi:" + _dpapi(data, decrypt=False) if os.name == "nt" else b"private:" + data


def unprotect(data: bytes) -> bytes:
    if data.startswith(b"dpapi:") and os.name == "nt":
        return _dpapi(data[6:], decrypt=True)
    if data.startswith(b"private:") and os.name != "nt":
        return data[8:]
    raise PermissionError("Preview protection identity unavailable")
