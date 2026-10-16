"""Immutable application resources and mutable user data have separate roots."""

import sys
from pathlib import Path


def dashboard_root():
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "dashboard"
    return Path(__file__).resolve().parents[3] / "dashboard" / "dist"
