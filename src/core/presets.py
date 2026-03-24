"""
Workflow Preset System for Video Studio

Presets store reusable pipeline configurations (intro/outro paths,
whisper model, thumbnail styles, enabled steps, etc.) as JSON files
in the ``presets/`` directory under PROJECT_ROOT.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config.settings import Settings


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Preset dataclass ────────────────────────────────────────────────

@dataclass
class Preset:
    """A single workflow preset."""

    name: str
    description: str = ""
    settings: dict[str, Any] = field(default_factory=dict)
    created: str = field(default_factory=lambda: _now_iso())
    updated: str = field(default_factory=lambda: _now_iso())

    # -- serialisation helpers --

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Preset:
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            settings=data.get("settings", {}),
            created=data.get("created", _now_iso()),
            updated=data.get("updated", _now_iso()),
        )


# ── Default preset ──────────────────────────────────────────────────

DEFAULT_PRESET = Preset(
    name="default",
    description="Sensible defaults for a standard YouTube workflow",
    settings={
        "intro_path": "",
        "outro_path": "",
        "subscribe_overlay_path": "",
        "whisper_model": "base",
        "whisper_device": "cpu",
        "transcription_engine": "whisper",
        "audio_cleanup_mode": "builtin",
        "audio_cleanup_preset": "medium",
        "title_style": "engaging",
        "title_count": 5,
        "thumbnail_styles": ["modern", "vibrant", "tech"],
        "thumbnail_count": 3,
        "enabled_steps": [
            "import",
            "edit",
            "transcribe",
            "audio",
            "titles",
            "thumbnail",
            "preview",
            "upload",
        ],
    },
)


# ── PresetManager ───────────────────────────────────────────────────

class PresetManager:
    """CRUD manager for workflow presets stored as JSON files."""

    def __init__(self, presets_dir: Path | None = None) -> None:
        self.presets_dir = presets_dir or (Settings.PROJECT_ROOT / "presets")
        self.presets_dir.mkdir(parents=True, exist_ok=True)

    # -- helpers --

    @staticmethod
    def _safe_filename(name: str) -> str:
        """Convert a preset name into a filesystem-safe filename (without extension)."""
        slug = name.strip().lower()
        slug = re.sub(r"[^\w\s-]", "", slug)
        slug = re.sub(r"[\s_-]+", "_", slug).strip("_")
        return slug or "preset"

    def _path_for(self, name: str) -> Path:
        return self.presets_dir / f"{self._safe_filename(name)}.json"

    # -- public API --

    def list_presets(self) -> list[Preset]:
        """Return all presets found in the presets directory."""
        presets: list[Preset] = []
        for fp in sorted(self.presets_dir.glob("*.json")):
            try:
                data = json.loads(fp.read_text(encoding="utf-8"))
                presets.append(Preset.from_dict(data))
            except (json.JSONDecodeError, KeyError):
                # skip malformed files
                continue
        return presets

    def save_preset(self, preset: Preset) -> None:
        """Save (create or overwrite) a preset to disk."""
        preset.updated = _now_iso()
        path = self._path_for(preset.name)
        path.write_text(
            json.dumps(preset.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def load_preset(self, name: str) -> Preset:
        """Load a preset by name. Raises ``FileNotFoundError`` if missing."""
        path = self._path_for(name)
        if not path.exists():
            raise FileNotFoundError(f"Preset not found: {name} (expected {path})")
        data = json.loads(path.read_text(encoding="utf-8"))
        return Preset.from_dict(data)

    def delete_preset(self, name: str) -> None:
        """Delete a preset file. Raises ``FileNotFoundError`` if missing."""
        path = self._path_for(name)
        if not path.exists():
            raise FileNotFoundError(f"Preset not found: {name} (expected {path})")
        path.unlink()

    def apply_preset(self, preset: Preset, project: dict[str, Any]) -> dict[str, Any]:
        """Merge *preset.settings* into *project* and return the updated dict.

        Only keys present in the preset are overwritten; the rest of the
        project dict is left untouched.
        """
        project.update(preset.settings)
        return project


