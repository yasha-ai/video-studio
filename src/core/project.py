"""
Project Manager — управление множеством проектов Video Studio
"""

import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    from config.settings import Settings
except ImportError:
    Settings = None


# Default project state template
_DEFAULT_STATE = {
    "name": "",
    "video_path": None,
    "audio_path": None,
    "transcription": None,
    "titles": [],
    "selected_title": None,
    "thumbnail_path": None,
    "thumbnail_paths": [],
    "description": None,
    "intro_path": None,
    "outro_path": None,
    "completed_steps": [],
    "created": None,
    "updated": None,
}

STATE_FILENAME = "project_state.json"


class ProjectManager:
    """Менеджер проектов — создание, открытие, удаление, список."""

    def __init__(self, projects_dir: Optional[Path] = None):
        """
        Args:
            projects_dir: Корневая папка для проектов.
                          По умолчанию — Settings.ARTIFACTS_DIR.
        """
        if projects_dir is not None:
            self.projects_dir = Path(projects_dir)
        elif Settings is not None:
            self.projects_dir = Settings.ARTIFACTS_DIR
        else:
            self.projects_dir = Path("output/artifacts")

        self.projects_dir.mkdir(parents=True, exist_ok=True)

    # ── Public API ──────────────────────────────────────────────

    def list_projects(self) -> list[dict]:
        """
        Сканирует projects_dir и возвращает список проектов.

        Returns:
            Список словарей:
            {"name", "id", "created", "path", "completed_steps", "video_name"}
        """
        projects: list[dict] = []

        if not self.projects_dir.exists():
            return projects

        for entry in sorted(self.projects_dir.iterdir(), reverse=True):
            state_file = entry / STATE_FILENAME
            if not entry.is_dir() or not state_file.exists():
                continue

            try:
                state = self._read_state(state_file)
            except (json.JSONDecodeError, OSError):
                continue

            video_name = ""
            if state.get("video_path"):
                video_name = Path(state["video_path"]).name

            projects.append({
                "name": state.get("name", entry.name),
                "id": entry.name,
                "created": state.get("created", ""),
                "path": str(entry),
                "completed_steps": state.get("completed_steps", []),
                "video_name": video_name,
                "video_path": state.get("video_path", ""),
            })

        return projects

    def create_project(self, name: str, video_path: str) -> dict:
        """
        Создаёт новый проект.

        Args:
            name: Человекочитаемое имя проекта.
            video_path: Путь к исходному видеофайлу.

        Returns:
            project_state dict (уже сохранённый на диск).
        """
        sanitized = self._sanitize_name(name)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        folder_name = f"{sanitized}_{timestamp}"
        project_path = self.projects_dir / folder_name
        project_path.mkdir(parents=True, exist_ok=True)

        now_iso = datetime.now().isoformat()

        state: dict = {
            **_DEFAULT_STATE,
            "name": name,
            "video_path": str(video_path),
            "completed_steps": ["import"],
            "created": now_iso,
            "updated": now_iso,
        }

        self._write_state(project_path / STATE_FILENAME, state)
        return {**state, "path": str(project_path)}

    def open_project(self, project_path: Path) -> dict:
        """
        Загружает состояние существующего проекта.

        Args:
            project_path: Папка проекта (содержит project_state.json).

        Returns:
            project_state dict.

        Raises:
            FileNotFoundError: если project_state.json не найден.
        """
        project_path = Path(project_path)
        state_file = project_path / STATE_FILENAME
        if not state_file.exists():
            raise FileNotFoundError(
                f"Project state not found: {state_file}"
            )

        state = self._read_state(state_file)
        return {**state, "path": str(project_path)}

    def delete_project(self, project_path: Path) -> None:
        """
        Удаляет папку проекта со всем содержимым.

        Args:
            project_path: Папка проекта.
        """
        project_path = Path(project_path)
        if project_path.exists() and project_path.is_dir():
            shutil.rmtree(project_path)

    def save_project_state(self, project_path: Path, state: dict) -> None:
        """
        Сохраняет текущее состояние проекта.

        Args:
            project_path: Папка проекта.
            state: Словарь состояния (формат _DEFAULT_STATE).
        """
        project_path = Path(project_path)
        state["updated"] = datetime.now().isoformat()
        self._write_state(project_path / STATE_FILENAME, state)

    # ── Internal helpers ────────────────────────────────────────

    @staticmethod
    def _sanitize_name(name: str) -> str:
        """Очистка имени от спецсимволов."""
        sanitized = re.sub(r"[^\w\s-]", "", name)
        sanitized = re.sub(r"[-\s]+", "_", sanitized)
        return sanitized.strip("_")[:50]

    @staticmethod
    def _read_state(state_file: Path) -> dict:
        with open(state_file, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def _write_state(state_file: Path, state: dict) -> None:
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
