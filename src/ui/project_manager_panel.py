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


try:
    from .theme import C, L
except ImportError:
    from ui.theme import C, L


class ProjectManagerPanel(ctk.CTkToplevel):
    """Окно управления проектами — список, создание, удаление."""

    def __init__(
        self,
        master,
        project_manager: ProjectManager,
        on_project_open: Optional[Callable[[dict], None]] = None,
        on_project_create: Optional[Callable[[str], None]] = None,
        current_video_path: Optional[str] = None,
        on_current_deleted: Optional[Callable[[], None]] = None,
        **kwargs,
    ):
        """
        Args:
            master: Родительское окно.
            project_manager: Экземпляр ProjectManager.
            on_project_open: Callback при открытии проекта.
            on_project_create: Callback при создании проекта.
            current_video_path: Path to currently active video (to detect "delete current").
            on_current_deleted: Callback when the current project is deleted.
        """
        super().__init__(master, **kwargs)

        self.pm = project_manager
        self.on_project_open = on_project_open
        self.on_project_create = on_project_create
        self._current_video_path = current_video_path
        self._on_current_deleted = on_current_deleted
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

        # Check if this is the active project
        is_current = False
        if self._current_video_path:
            proj_video = project.get("video_name", "")
            current_name = Path(self._current_video_path).name if self._current_video_path else ""
            is_current = proj_video == current_name

        display_name = project.get("name", "Untitled")
        if is_current:
            display_name = f"{display_name}  (current)"
            card.configure(border_color=C["green"])

        name_label = ctk.CTkLabel(
            left,
            text=display_name,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=C["green"] if is_current else C["text"],
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
        """Show delete dialog with cleanup options."""
        if self._selected_index is None:
            return

        project = self._projects[self._selected_index]
        name = project.get("name", "Untitled")

        is_current = False
        if self._current_video_path:
            proj_video = project.get("video_name", "")
            current_name = Path(self._current_video_path).name if self._current_video_path else ""
            is_current = proj_video == current_name

        # Show delete options dialog
        dlg = ctk.CTkToplevel(self)
        dlg.title("Delete Project")
        dlg.geometry("460x380")
        dlg.transient(self)
        dlg.grab_set()
        dlg.configure(fg_color=C["bg"])

        inner = ctk.CTkFrame(dlg, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=24, pady=20)

        ctk.CTkLabel(
            inner, text=f'Delete "{name}"?',
            font=ctk.CTkFont(size=16, weight="bold"), text_color=C["text"],
        ).pack(anchor="w", pady=(0, 4))

        if is_current:
            ctk.CTkLabel(
                inner, text="This is your current project. The app will reset.",
                font=ctk.CTkFont(size=12), text_color=C["red"],
            ).pack(anchor="w", pady=(0, 8))

        ctk.CTkLabel(
            inner, text="Choose what to delete:",
            font=ctk.CTkFont(size=13), text_color=C["text2"],
        ).pack(anchor="w", pady=(8, 8))

        # Checkboxes
        del_project = ctk.BooleanVar(value=True)
        del_generated = ctk.BooleanVar(value=True)
        del_thumbnails = ctk.BooleanVar(value=True)
        del_audio = ctk.BooleanVar(value=True)
        del_transcripts = ctk.BooleanVar(value=False)

        ctk.CTkCheckBox(inner, text="Project data (artifacts folder)", variable=del_project,
                         font=ctk.CTkFont(size=12), fg_color=C["accent"], text_color=C["text"],
                         state="disabled").pack(anchor="w", pady=2)

        ctk.CTkCheckBox(inner, text="Generated thumbnails", variable=del_thumbnails,
                         font=ctk.CTkFont(size=12), fg_color=C["accent"], text_color=C["text"]).pack(anchor="w", pady=2)

        ctk.CTkCheckBox(inner, text="Cleaned audio files", variable=del_audio,
                         font=ctk.CTkFont(size=12), fg_color=C["accent"], text_color=C["text"]).pack(anchor="w", pady=2)

        ctk.CTkCheckBox(inner, text="Assembled / rendered videos", variable=del_generated,
                         font=ctk.CTkFont(size=12), fg_color=C["accent"], text_color=C["text"]).pack(anchor="w", pady=2)

        ctk.CTkCheckBox(inner, text="Transcription files", variable=del_transcripts,
                         font=ctk.CTkFont(size=12), fg_color=C["accent"], text_color=C["text"]).pack(anchor="w", pady=2)

        ctk.CTkLabel(
            inner, text="Original video file is NEVER deleted.",
            font=ctk.CTkFont(size=11), text_color=C["text3"],
        ).pack(anchor="w", pady=(12, 0))

        # Buttons
        btn_row = ctk.CTkFrame(inner, fg_color="transparent")
        btn_row.pack(fill="x", pady=(16, 0))

        def do_delete():
            import shutil

            # Get video path and find work_dir (video_studio_*)
            video_path = project.get("video_path") or ""
            video_parent = Path(video_path).parent if video_path else None
            video_stem = Path(video_path).stem if video_path else ""

            # Find work directory: video_studio_{stem} or video_studio_{stem} (N)
            work_dirs = []
            if video_parent and video_parent.exists():
                for d in video_parent.iterdir():
                    if d.is_dir() and d.name.startswith(f"video_studio_{video_stem}"):
                        work_dirs.append(d)

            # 1. Delete project artifacts folder
            try:
                self.pm.delete_project(Path(project["path"]))
            except Exception:
                pass

            all_checked = del_thumbnails.get() and del_audio.get() and del_generated.get() and del_transcripts.get()

            # 2. Delete files in work directories
            for work_dir in work_dirs:
                if all_checked:
                    # All checked — remove entire work_dir
                    shutil.rmtree(work_dir, ignore_errors=True)
                else:
                    # Selective deletion
                    if del_thumbnails.get():
                        thumb_dir = work_dir / "thumbnails"
                        if thumb_dir.exists():
                            shutil.rmtree(thumb_dir, ignore_errors=True)
                        for f in work_dir.glob("*_thumbnail_*"):
                            f.unlink(missing_ok=True)

                    if del_audio.get():
                        for f in work_dir.glob("audio_cleaned*"):
                            f.unlink(missing_ok=True)

                    if del_generated.get():
                        for pattern in ["*_assembled*", "*_with_overlay*", "*_final*", "*_merged*"]:
                            for f in work_dir.glob(pattern):
                                f.unlink(missing_ok=True)

                    if del_transcripts.get():
                        for f in work_dir.glob("*_subtitles*"):
                            f.unlink(missing_ok=True)
                        for f in work_dir.glob("*_timestamps*"):
                            f.unlink(missing_ok=True)
                        for f in work_dir.glob("*_descriptions*"):
                            f.unlink(missing_ok=True)

                    # If work_dir is empty after cleanup — remove it too
                    try:
                        remaining = list(work_dir.iterdir())
                        if not remaining:
                            work_dir.rmdir()
                    except Exception:
                        pass

            dlg.destroy()

            if is_current and self._on_current_deleted:
                self._on_current_deleted()
            else:
                self._refresh_list()

        ctk.CTkButton(
            btn_row, text="Delete", width=120, height=36,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=C["red"], hover_color="#cc5555", text_color="#ffffff",
            command=do_delete,
        ).pack(side="right", padx=4)

        ctk.CTkButton(
            btn_row, text="Cancel", width=100, height=36,
            font=ctk.CTkFont(size=13),
            fg_color=C["surface3"], hover_color=C["border"], text_color=C["text"],
            command=dlg.destroy,
        ).pack(side="right", padx=4)
