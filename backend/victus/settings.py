import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    api_token: str
    emergency_hotkey: bool = False

    @classmethod
    def from_env(cls) -> "Settings":
        configured = os.getenv("VICTUS_DATA_DIR")
        if configured:
            root = Path(configured).expanduser().resolve()
        else:
            local = os.getenv("LOCALAPPDATA")
            if not local:
                raise ValueError("Set VICTUS_DATA_DIR when LOCALAPPDATA is unavailable")
            root = Path(local).resolve() / "VICTUS"
        return cls(
            data_dir=root,
            api_token=os.getenv("VICTUS_API_TOKEN", ""),
            emergency_hotkey=os.getenv("VICTUS_EMERGENCY_HOTKEY", "0") == "1",
        )

    @property
    def workspace(self) -> Path:
        return self.data_dir / "workspace"

    def initialize(self) -> None:
        if len(self.api_token) < 32:
            raise ValueError("VICTUS_API_TOKEN must contain at least 32 characters")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.workspace.mkdir(parents=True, exist_ok=True)
        if self.workspace.resolve().parent != self.data_dir.resolve():
            raise ValueError("Workspace must be a direct directory inside the data root")
