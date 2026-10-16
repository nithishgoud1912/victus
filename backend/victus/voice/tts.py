"""Speech output contract and Windows SAPI implementation, with COM thread ownership."""

import threading
import time
from typing import Protocol


class SpeechOutput(Protocol):
    def speak(self, text: str, interrupted: threading.Event, deadline: float) -> None: ...


class SapiSpeechOutput:
    def speak(self, text: str, interrupted: threading.Event, deadline: float) -> None:
        import pythoncom
        from win32com.client import Dispatch

        pythoncom.CoInitialize()
        voice = None
        try:
            if interrupted.is_set():
                return
            voice = Dispatch("SAPI.SpVoice")
            # Async | purge prior speech | literal text (never interpret XML).
            voice.Speak(text[:240], 1 | 2 | 16)
            while not voice.WaitUntilDone(25):
                if interrupted.is_set() or time.monotonic() >= deadline:
                    voice.Speak("", 1 | 2)
                    return
        finally:
            if voice is not None:
                voice.Speak("", 1 | 2)
            voice = None
            pythoncom.CoUninitialize()
