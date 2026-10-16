import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    api_token: str
    emergency_hotkey: bool = False
    dashboard_dev_origin: str | None = None
    dashboard_dir: Path | None = None
    voice_model_path: Path | None = None
    wake_manifest_path: Path | None = None
    mcp_notes: bool = False
    cloud_model: str | None = None
    cloud_upstream: str | None = None

    def __post_init__(self):
        if bool(self.cloud_model) != bool(self.cloud_upstream):
            raise ValueError("Configure both cloud model and upstream provider")
        if self.dashboard_dev_origin not in {None, "http://127.0.0.1:5173"}:
            raise ValueError(
                "Only http://127.0.0.1:5173 is an approved dashboard development origin"
            )

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
            wake_manifest_path=(Path(os.environ["VICTUS_WAKE_MANIFEST_PATH"]).expanduser().resolve()
                                if os.getenv("VICTUS_WAKE_MANIFEST_PATH") else None),
            mcp_notes=os.getenv("VICTUS_MCP_NOTES", "0") == "1",
            cloud_model=os.getenv("VICTUS_CLOUD_MODEL") or None,
            cloud_upstream=os.getenv("VICTUS_CLOUD_UPSTREAM") or None,
            voice_model_path=(
                Path(os.environ["VICTUS_VOICE_MODEL_PATH"]).expanduser().resolve()
                if os.getenv("VICTUS_VOICE_MODEL_PATH")
                else None
            ),
            emergency_hotkey=os.getenv("VICTUS_EMERGENCY_HOTKEY", "0") == "1",
            dashboard_dev_origin=os.getenv("VICTUS_DASHBOARD_DEV_ORIGIN") or None,
        )

    @property
    def workspace(self) -> Path:
        return self.data_dir / "workspace"

    def initialize(self) -> None:
        if len(self.api_token) < 32:
            raise ValueError("VICTUS_API_TOKEN must contain at least 32 characters")
        if (self.data_dir / "RESTORE_FAILED").exists():
            raise ValueError("Incomplete restore cannot be activated")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.workspace.mkdir(parents=True, exist_ok=True)
        if self.workspace.resolve().parent != self.data_dir.resolve():
            raise ValueError("Workspace must be a direct directory inside the data root")
