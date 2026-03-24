"""
Project Manager Panel — CTkToplevel окно со списком проектов
"""

import customtkinter as ctk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Callable, Optional

try:
    from ..core.project import ProjectManager
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.project import ProjectManager


# --- Color palette ---
C = {
    "bg": "#0f0f0f",
    "surface": "#1a1a1a",
    "surface2": "#242424",
    "surface3": "#2e2e2e",
    "border": "#333333",
    "text": "#e8e8e8",
    "text2": "#999999",
    "text3": "#666666",
    "accent": "#6c5ce7",
    "accent_hover": "#5a4bd1",
    "green": "#00b894",
    "red": "#ff6b6b",
}


class ProjectManagerPanel(ctk.CTkToplevel):
    """Окно управления проектами — список, создание, удаление."""

    def __init__(
        self,
        master,
        project_manager: ProjectManager,
        on_project_open: Optional[Callable[[dict], None]] = None,
        on_project_create: Optional[Callable[[str], None]] = None,
        **kwargs,
    ):
        """
        Args:
            master: Родительское окно.
            project_manager: Экземпляр ProjectManager.
            on_project_open: Callback при открытии проекта (project_state dict).
            on_project_create: Callback при создании проекта (video_path str).
        """
        super().__init__(master, **kwargs)

        self.pm = project_manager
        self.on_project_open = on_project_open
        self.on_project_create = on_project_create
        self._selected_index: Optional[int] = None
        self._card_frames: list[ctk.CTkFrame] = []
        self._projects: list[dict] = []

        # Window setup
        self.title("Projects")
        self.geometry("720x560")
        self.configure(fg_color=C["bg"])
        self.resizable(True, True)
        self.minsize(500, 400)

        self._build_ui()
        self._refresh_list()

    # ── UI Construction ─────────────────────────────────────────

    def _build_ui(self):
        # Top bar
        top = ctk.CTkFrame(self, fg_color=C["surface"], corner_radius=0, height=56)
        top.pack(fill="x")
        top.pack_propagate(False)

        ctk.CTkLabel(
            top, text="Projects", font=ctk.CTkFont(size=18, weight="bold"),
            text_color=C["text"],
        ).pack(side="left", padx=20)

        btn_new = ctk.CTkButton(
            top,
            text="+ New Project",
            width=140,
            height=34,
            corner_radius=8,
            fg_color=C["accent"],
            hover_color=C["accent_hover"],
            text_color="#ffffff",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._on_new_project,
        )
        btn_new.pack(side="right", padx=20, pady=11)

        # Scrollable area
        self._scroll = ctk.CTkScrollableFrame(
            self,
            fg_color=C["bg"],
            scrollbar_button_color=C["surface3"],
            scrollbar_button_hover_color=C["accent"],
        )
        self._scroll.pack(fill="both", expand=True, padx=12, pady=(8, 4))

        # Bottom bar with Open / Delete
        bottom = ctk.CTkFrame(self, fg_color=C["surface"], corner_radius=0, height=52)
        bottom.pack(fill="x", side="bottom")
        bottom.pack_propagate(False)

        self._btn_open = ctk.CTkButton(
            bottom,
            text="Open",
            width=100,
            height=34,
            corner_radius=8,
            fg_color=C["accent"],
            hover_color=C["accent_hover"],
            text_color="#ffffff",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._on_open,
            state="disabled",
        )
        self._btn_open.pack(side="left", padx=20, pady=9)

        self._btn_delete = ctk.CTkButton(
            bottom,
            text="Delete",
            width=100,
            height=34,
            corner_radius=8,
            fg_color=C["red"],
            hover_color="#e05555",
            text_color="#ffffff",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._on_delete,
            state="disabled",
        )
        self._btn_delete.pack(side="right", padx=20, pady=9)

    # ── List Rendering ──────────────────────────────────────────

    def _refresh_list(self):
        """Перестраивает список карточек проектов."""
        for card in self._card_frames:
            card.destroy()
        self._card_frames.clear()
        self._selected_index = None
        self._update_buttons_state()

        self._projects = self.pm.list_projects()

        if not self._projects:
            placeholder = ctk.CTkLabel(
                self._scroll,
                text="No projects yet.\nClick  + New Project  to get started.",
                font=ctk.CTkFont(size=14),
                text_color=C["text3"],
                justify="center",
            )
            placeholder.pack(pady=80)
            self._card_frames.append(placeholder)  # so it gets cleaned up
            return

        for idx, proj in enumerate(self._projects):
            card = self._create_card(idx, proj)
            card.pack(fill="x", padx=4, pady=4)
            self._card_frames.append(card)

    def _create_card(self, index: int, project: dict) -> ctk.CTkFrame:
        """Создаёт карточку проекта."""
        card = ctk.CTkFrame(
            self._scroll,
            fg_color=C["surface"],
            corner_radius=10,
            height=72,
            border_width=1,
            border_color=C["border"],
        )
        card.pack_propagate(False)

        # Bind click / double-click on the card and all children
        def _select(e, i=index):
            self._select_card(i)

        def _dbl(e, i=index):
            self._select_card(i)
            self._on_open()

        card.bind("<Button-1>", _select)
        card.bind("<Double-Button-1>", _dbl)

        # Left: name + video filename
        left = ctk.CTkFrame(card, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True, padx=16, pady=10)
        left.bind("<Button-1>", _select)
        left.bind("<Double-Button-1>", _dbl)

        name_label = ctk.CTkLabel(
            left,
            text=project.get("name", "Untitled"),
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=C["text"],
            anchor="w",
        )
        name_label.pack(anchor="w")
        name_label.bind("<Button-1>", _select)
        name_label.bind("<Double-Button-1>", _dbl)

        video_name = project.get("video_name", "")
        sub_text = video_name if video_name else "no video"
        sub_label = ctk.CTkLabel(
            left,
            text=sub_text,
            font=ctk.CTkFont(size=11),
            text_color=C["text3"],
            anchor="w",
        )
        sub_label.pack(anchor="w")
        sub_label.bind("<Button-1>", _select)
        sub_label.bind("<Double-Button-1>", _dbl)

        # Right: steps badge + date
        right = ctk.CTkFrame(card, fg_color="transparent")
        right.pack(side="right", padx=16, pady=10)
        right.bind("<Button-1>", _select)
        right.bind("<Double-Button-1>", _dbl)

        steps = project.get("completed_steps", [])
        steps_text = f"{len(steps)} step{'s' if len(steps) != 1 else ''}"
        steps_color = C["green"] if len(steps) >= 4 else C["text2"]
        steps_label = ctk.CTkLabel(
            right,
            text=steps_text,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=steps_color,
            anchor="e",
        )
        steps_label.pack(anchor="e")
        steps_label.bind("<Button-1>", _select)
        steps_label.bind("<Double-Button-1>", _dbl)

        created_raw = project.get("created", "")
        date_str = ""
        if created_raw:
            try:
                dt = datetime.fromisoformat(created_raw)
                date_str = dt.strftime("%Y-%m-%d %H:%M")
            except (ValueError, TypeError):
                date_str = str(created_raw)[:16]
        date_label = ctk.CTkLabel(
            right,
            text=date_str,
            font=ctk.CTkFont(size=11),
            text_color=C["text3"],
            anchor="e",
        )
        date_label.pack(anchor="e")
        date_label.bind("<Button-1>", _select)
        date_label.bind("<Double-Button-1>", _dbl)

        return card

    # ── Selection ───────────────────────────────────────────────

    def _select_card(self, index: int):
        """Выделяет карточку по индексу."""
        # Reset previous
        if self._selected_index is not None and self._selected_index < len(self._card_frames):
            self._card_frames[self._selected_index].configure(
                border_color=C["border"]
            )

        self._selected_index = index
        self._card_frames[index].configure(border_color=C["accent"])
        self._update_buttons_state()

    def _update_buttons_state(self):
        has_selection = self._selected_index is not None
        state = "normal" if has_selection else "disabled"
        self._btn_open.configure(state=state)
        self._btn_delete.configure(state=state)

    # ── Actions ─────────────────────────────────────────────────

    def _on_new_project(self):
        """Диалог выбора видео -> создание проекта."""
        video_path = filedialog.askopenfilename(
            title="Select a video file",
            filetypes=[
                ("Video files", "*.mp4 *.mkv *.mov *.avi *.webm *.m4v"),
                ("All files", "*.*"),
            ],
            parent=self,
        )
        if not video_path:
            return

        # Derive project name from filename
        name = Path(video_path).stem.replace("_", " ").replace("-", " ")

        try:
            state = self.pm.create_project(name, video_path)
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to create project:\n{exc}", parent=self)
            return

        self._refresh_list()

        if self.on_project_create:
            self.on_project_create(video_path)

    def _on_open(self):
        """Открывает выбранный проект через callback."""
        if self._selected_index is None:
            return

        project = self._projects[self._selected_index]
        project_path = Path(project["path"])

        try:
            state = self.pm.open_project(project_path)
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to open project:\n{exc}", parent=self)
            return

        if self.on_project_open:
            self.on_project_open(state)

        self.destroy()

    def _on_delete(self):
        """Удаляет выбранный проект после подтверждения."""
        if self._selected_index is None:
            return

        project = self._projects[self._selected_index]
        name = project.get("name", "Untitled")

        confirmed = messagebox.askyesno(
            "Delete project",
            f"Delete \"{name}\" and all its files?\nThis cannot be undone.",
            parent=self,
        )
        if not confirmed:
            return

        try:
            self.pm.delete_project(Path(project["path"]))
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to delete project:\n{exc}", parent=self)
            return

        self._refresh_list()
