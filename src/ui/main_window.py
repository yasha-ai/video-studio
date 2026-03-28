"""
Main Window - Главное окно приложения Video Studio (Modern UI)
"""

import os
import logging
import customtkinter as ctk
from pathlib import Path

logger = logging.getLogger(__name__)
from tkinter import filedialog, messagebox
import threading
import json

try:
    from config.settings import Settings
except ImportError:
    Settings = None

try:
    from ..core.artifacts import ArtifactsManager
    from ..processors.video_processor import VideoProcessor
    from ..processors.whisper_transcriber import WhisperTranscriber
    from ..processors.audio_cleanup import AudioCleanup
    from ..processors.title_generator import TitleGenerator
    from ..processors.cover_generator import CoverGenerator
    from ..processors.youtube_uploader import YouTubeUploader
    from ..processors.gemini_transcriber import GeminiTranscriber
    from ..processors.description_generator import DescriptionGenerator
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.artifacts import ArtifactsManager
    from processors.video_processor import VideoProcessor
    from processors.whisper_transcriber import WhisperTranscriber
    from processors.audio_cleanup import AudioCleanup
    from processors.title_generator import TitleGenerator
    from processors.cover_generator import CoverGenerator
    from processors.youtube_uploader import YouTubeUploader
    from processors.gemini_transcriber import GeminiTranscriber
    from processors.description_generator import DescriptionGenerator

try:
    from PIL import Image as PILImage
    from customtkinter import CTkImage
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    from tkinterdnd2 import DND_FILES
    HAS_DND = True
except ImportError:
    HAS_DND = False


try:
    from .theme import C, L
except ImportError:
    from ui.theme import C, L


class MainWindow(ctk.CTk):
    """Главное окно приложения"""

    STEPS = [
        {"id": "import",      "icon": "01", "label": L["step_import"],     "method": "_show_import_panel"},
        {"id": "edit",        "icon": "02", "label": L["step_assembly"],   "method": "_show_edit_panel"},
        {"id": "transcribe",  "icon": "03", "label": L["step_transcribe"], "method": "_show_transcribe_panel"},
        {"id": "audio",       "icon": "04", "label": L["step_audio"],      "method": "_show_audio_cleanup_panel"},
        {"id": "titles",      "icon": "05", "label": L["step_titles"],     "method": "_show_titles_panel"},
        {"id": "thumbnail",   "icon": "06", "label": L["step_thumbnail"],  "method": "_show_thumbnail_panel"},
        {"id": "description", "icon": "07", "label": "Описание",          "method": "_show_description_panel"},
        {"id": "preview",     "icon": "08", "label": L["step_preview"],    "method": "_show_preview_panel"},
        {"id": "upload",      "icon": "09", "label": L["step_upload"],     "method": "_show_upload_panel"},
    ]

    # Step dependencies
    STEP_DEPS = {
        "import":      [],
        "edit":        ["import"],
        "transcribe":  ["import"],
        "audio":       ["import"],
        "titles":      ["import"],
        "thumbnail":   ["import"],
        "description": ["import"],
        "preview":     ["import"],
        "upload":      ["import"],
    }

    PROJECT_FILE = (Settings.OUTPUT_DIR / ".video_studio_project.json") if Settings else Path("output/.video_studio_project.json")

    def __init__(self):
        super().__init__()

        self.title("Video Studio")
        self.geometry("1440x900")
        self.minsize(1200, 700)
        self.configure(fg_color=C["bg"])

        # App icon
        icon_path = Path(__file__).parent.parent.parent / "assets" / "icon.png"
        if icon_path.exists() and HAS_PIL:
            try:
                from PIL import ImageTk
                icon_img = PILImage.open(icon_path)
                icon_img = icon_img.resize((256, 256))
                self._icon_photo = ImageTk.PhotoImage(icon_img)
                self.iconphoto(True, self._icon_photo)
            except Exception:
                pass

        self._setup_clipboard()
        self._center_window()
        self._init_processors()

        self.project = {
            "video_path": None,
            "original_video_path": None,
            "audio_path": None,
            "transcription": None,
            "titles": [],
            "selected_title": None,
            "title_critiques": {},
            "thumbnail_path": None,
            "thumbnail_paths": [],
            "description": None,
            "intro_path": None,
            "outro_path": None,
            "subscribe_overlay_path": None,
            "reference_image": None,
            "descriptions": [],
        }

        self.completed_steps: set[str] = set()
        self.active_step: str = "import"
        self._sidebar_buttons: dict[str, ctk.CTkButton] = {}
        self._sidebar_badges: dict[str, ctk.CTkLabel] = {}

        self._load_project()
        self._setup_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(500, self._validate_environment)

    # ══════════════════════════════════════════
    #  Init
    # ══════════════════════════════════════════

    def _setup_clipboard(self):
        """No-op — native tk.Entry handles Cmd+V/C/X natively."""
        pass

    def _center_window(self):
        self.update_idletasks()
        w, h = 1440, 900
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _init_processors(self):
        try:
            self.artifacts = ArtifactsManager(project_name="untitled_project")
            self.video_processor = VideoProcessor(self.artifacts)
            self.whisper = WhisperTranscriber()
            self.audio_cleanup = AudioCleanup()
            self.title_generator = TitleGenerator()
            self.cover_generator = CoverGenerator()
            self.youtube_uploader = None
        except Exception as e:
            print(f"Warning: processor init error: {e}")

    # ══════════════════════════════════════════
    #  Project persistence
    # ══════════════════════════════════════════

    def _save_project(self):
        """Save project state to disk."""
        logger.debug("Saving project state")
        try:
            self.PROJECT_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "project": self.project,
                "completed_steps": list(self.completed_steps),
                "active_step": self.active_step,
            }
            with open(self.PROJECT_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: could not save project: {e}")

    def _load_project(self):
        """Load project state from disk, verify all files still exist."""
        if not self.PROJECT_FILE.exists():
            return
        try:
            with open(self.PROJECT_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            saved = data.get("project", {})

            # Only restore if the original video file still exists
            if not saved.get("video_path") or not Path(saved["video_path"]).exists():
                logger.warning("Saved project video not found, starting fresh")
                return

            self.project.update(saved)
            self.completed_steps = set(data.get("completed_steps", []))
            self.active_step = data.get("active_step", "import")

            # Validate all file paths — clear missing ones
            invalidated = []

            # Check file-based project fields
            file_keys = {
                "audio_path": "audio",
                "thumbnail_path": "thumbnail",
            }
            for key, step in file_keys.items():
                val = self.project.get(key)
                if val and not Path(val).exists():
                    logger.warning(f"File missing: {key}={val}")
                    self.project[key] = None
                    self.completed_steps.discard(step)
                    invalidated.append(step)

            # Check work_dir
            wd = self.project.get("work_dir")
            if wd and not Path(wd).exists():
                logger.warning(f"Work dir missing: {wd}")
                self.project["work_dir"] = None

            # Check thumbnail_paths list
            if self.project.get("thumbnail_paths"):
                valid = [p for p in self.project["thumbnail_paths"] if Path(p).exists()]
                if len(valid) != len(self.project["thumbnail_paths"]):
                    logger.warning(f"Some thumbnails missing: {len(self.project['thumbnail_paths'])} -> {len(valid)}")
                    self.project["thumbnail_paths"] = valid
                    if not valid:
                        self.project["thumbnail_path"] = None
                        self.completed_steps.discard("thumbnail")
                        invalidated.append("thumbnail")

            # Check intro/outro/overlay
            for key in ("intro_path", "outro_path", "subscribe_overlay_path", "reference_image"):
                val = self.project.get(key)
                if val and not Path(val).exists():
                    logger.warning(f"Asset missing: {key}={val}")
                    self.project[key] = None

            # Check transcription — if text is empty, reset step
            if not self.project.get("transcription"):
                self.completed_steps.discard("transcribe")
                if "transcribe" not in invalidated:
                    invalidated.append("transcribe")

            # Check titles
            if not self.project.get("titles"):
                self.completed_steps.discard("titles")

            if invalidated:
                logger.info(f"Invalidated steps due to missing files: {invalidated}")

        except Exception as e:
            logger.error(f"Could not load project: {e}")

    def _on_close(self):
        """Save state and exit cleanly — avoid SIGSEGV from background threads."""
        self._save_project()

        # Stop any media playback
        try:
            from ui.media_player import stop_playback
            stop_playback()
        except Exception:
            pass

        # Withdraw window first to prevent Tk callbacks on destroyed widgets
        self.withdraw()

        # Give background threads a moment to notice
        import time
        time.sleep(0.1)

        # Use os._exit to avoid Tk cleanup SIGSEGV on macOS
        try:
            self.destroy()
        except Exception:
            pass
        finally:
            os._exit(0)

    def _validate_environment(self):
        """Check environment on startup and show inline toast notifications."""
        if Settings is None:
            return
        issues = Settings.validate()
        if not issues:
            return

        errors = [i["msg"] for i in issues if i["level"] == "error"]
        warnings = [i["msg"] for i in issues if i["level"] == "warning"]

        # Show errors as blocking (can't work without ffmpeg)
        if errors:
            for msg in errors:
                self._show_toast(msg, level="error")
            return

        # Show warnings as dismissable toasts
        for msg in warnings:
            self._show_toast(msg, level="warning")

    def _show_toast(self, message: str, level: str = "info", duration: int = 8000):
        """Show an inline toast notification banner below the topbar."""
        log_fn = {"error": logger.error, "warning": logger.warning, "success": logger.info}.get(level, logger.info)
        log_fn(f"[{level.upper()}] {message}")
        colors = {
            "error":   {"bg": "#3d1515", "border": C["red"],    "text": C["red"]},
            "warning": {"bg": "#3d3515", "border": C["orange"], "text": C["orange"]},
            "info":    {"bg": "#15253d", "border": C["blue"],   "text": C["blue"]},
            "success": {"bg": "#153d20", "border": C["green"],  "text": C["green"]},
        }
        style = colors.get(level, colors["info"])

        toast = ctk.CTkFrame(
            self.content_frame,
            fg_color=style["bg"],
            corner_radius=10,
            border_width=1,
            border_color=style["border"],
            height=40,
        )
        toast.pack(fill="x", padx=24, pady=(8, 0), before=self.content_frame.winfo_children()[0] if self.content_frame.winfo_children() else None)
        toast.pack_propagate(False)

        ctk.CTkLabel(
            toast, text=message,
            font=ctk.CTkFont(size=12),
            text_color=style["text"],
        ).pack(side="left", padx=16)

        # Settings link for config issues
        if level in ("warning", "error"):
            ctk.CTkButton(
                toast, text="Settings", width=70, height=26,
                font=ctk.CTkFont(size=11),
                fg_color="transparent", text_color=style["text"],
                hover_color=style["bg"],
                border_width=1, border_color=style["border"],
                command=lambda: (toast.destroy(), self._open_settings()),
            ).pack(side="right", padx=(0, 8))

        # Dismiss button
        ctk.CTkButton(
            toast, text="x", width=26, height=26,
            font=ctk.CTkFont(size=11),
            fg_color="transparent", text_color=C["text3"],
            hover_color=style["bg"],
            command=toast.destroy,
        ).pack(side="right", padx=(0, 4))

        # Auto-dismiss
        if duration > 0:
            toast.after(duration, lambda: toast.destroy() if toast.winfo_exists() else None)

    def _check_deps(self, step_id: str) -> bool:
        """Check if all dependencies for a step are met. Show warning if not."""
        deps = self.STEP_DEPS.get(step_id, [])
        missing = [d for d in deps if d not in self.completed_steps]
        if missing:
            labels = {s["id"]: s["label"] for s in self.STEPS}
            names = ", ".join(labels.get(m, m) for m in missing)
            messagebox.showwarning("Step unavailable", f"Complete these steps first: {names}")
            return False
        return True

    # ══════════════════════════════════════════
    #  UI Setup
    # ══════════════════════════════════════════

    def _setup_ui(self):
        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color=C["surface"])
        self.sidebar.pack(fill="y", side="left")
        self.sidebar.pack_propagate(False)

        # Logo
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.pack(fill="x", padx=20, pady=(28, 8))

        ctk.CTkLabel(
            logo_frame, text=L["app_title"].upper(),
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=C["text"],
        ).pack(anchor="w")

        ctk.CTkLabel(
            logo_frame, text=L["app_subtitle"],
            font=ctk.CTkFont(size=11),
            text_color=C["text3"],
        ).pack(anchor="w", pady=(2, 0))

        # Divider
        ctk.CTkFrame(self.sidebar, height=1, fg_color=C["border"]).pack(fill="x", padx=16, pady=(16, 12))

        # Steps
        for step in self.STEPS:
            self._create_sidebar_step(step)

        # Bottom area
        bottom = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        bottom.pack(fill="x", side="bottom", padx=16, pady=16)

        ctk.CTkFrame(self.sidebar, height=1, fg_color=C["border"]).pack(
            fill="x", padx=16, side="bottom", pady=(0, 8)
        )

        projects_btn = ctk.CTkButton(
            bottom, text=L["projects"],
            font=ctk.CTkFont(size=12),
            fg_color="transparent", text_color=C["text2"],
            hover_color=C["surface3"], height=32, anchor="w",
            command=self._open_projects,
        )
        projects_btn.pack(fill="x", pady=(0, 4))

        batch_btn = ctk.CTkButton(
            bottom, text=L["batch"],
            font=ctk.CTkFont(size=12),
            fg_color="transparent", text_color=C["text2"],
            hover_color=C["surface3"], height=32, anchor="w",
            command=self._open_batch,
        )
        batch_btn.pack(fill="x", pady=(0, 4))

        settings_btn = ctk.CTkButton(
            bottom, text=L["settings"],
            font=ctk.CTkFont(size=12),
            fg_color="transparent", text_color=C["text2"],
            hover_color=C["surface3"], height=32, anchor="w",
            command=self._open_settings,
        )
        settings_btn.pack(fill="x", pady=(0, 4))

        help_btn = ctk.CTkButton(
            bottom, text=L["help"],
            font=ctk.CTkFont(size=12),
            fg_color="transparent", text_color=C["text2"],
            hover_color=C["surface3"], height=32, anchor="w",
            command=self._open_help,
        )
        help_btn.pack(fill="x")

        # Main area wrapper
        right_side = ctk.CTkFrame(self, fg_color=C["bg"], corner_radius=0)
        right_side.pack(fill="both", expand=True, side="left")

        # Log panel (bottom, collapsible)
        try:
            from .log_panel import LogPanel, GUILogHandler
        except ImportError:
            try:
                from ui.log_panel import LogPanel, GUILogHandler
            except ImportError:
                LogPanel = None

        if LogPanel:
            import logging
            self.log_panel = LogPanel(right_side)
            self.log_panel.pack(fill="x", side="bottom")
            handler = GUILogHandler(self.log_panel)
            handler.setLevel(logging.DEBUG)
            logging.getLogger().addHandler(handler)
            logging.getLogger().setLevel(logging.INFO)

        main_wrapper = ctk.CTkFrame(right_side, fg_color=C["bg"], corner_radius=0)
        main_wrapper.pack(fill="both", expand=True)

        # Top bar
        self.topbar = ctk.CTkFrame(main_wrapper, height=52, fg_color=C["surface"], corner_radius=0)
        self.topbar.pack(fill="x")
        self.topbar.pack_propagate(False)

        # Nav buttons
        nav_frame = ctk.CTkFrame(self.topbar, fg_color="transparent")
        nav_frame.pack(side="left", padx=(16, 0))

        self._prev_btn = ctk.CTkButton(
            nav_frame, text="<", width=36, height=32,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=C["surface3"], hover_color=C["border"],
            text_color=C["text2"], corner_radius=8,
            command=self._go_prev_step,
        )
        self._prev_btn.pack(side="left", padx=(0, 4))

        self.topbar_title = ctk.CTkLabel(
            nav_frame, text="Import Video",
            font=ctk.CTkFont(size=14, weight="bold"), text_color=C["text"],
        )
        self.topbar_title.pack(side="left", padx=12)

        self._next_btn = ctk.CTkButton(
            nav_frame, text=">", width=36, height=32,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=C["accent"], hover_color=C["accent_hover"],
            text_color=C["text"], corner_radius=8,
            command=self._go_next_step,
        )
        self._next_btn.pack(side="left", padx=(4, 0))

        self.topbar_status = ctk.CTkLabel(
            self.topbar, text=L["ready"],
            font=ctk.CTkFont(size=12), text_color=C["text3"],
        )
        self.topbar_status.pack(side="right", padx=24)

        # Content area
        self.content_frame = ctk.CTkFrame(main_wrapper, fg_color=C["bg"], corner_radius=0)
        self.content_frame.pack(fill="both", expand=True)

        # Restore badges from saved state
        for step_id in self.completed_steps:
            if step_id in self._sidebar_badges:
                self._sidebar_badges[step_id].configure(text="  \u2713", text_color=C["green"])

        self._show_import_panel()

    # --- Sidebar step ---

    def _create_sidebar_step(self, step: dict):
        row = ctk.CTkFrame(self.sidebar, fg_color="transparent", height=38)
        row.pack(fill="x", padx=10, pady=1)
        row.pack_propagate(False)

        btn = ctk.CTkButton(
            row,
            text=f"  {step['icon']}   {step['label']}",
            font=ctk.CTkFont(size=13),
            anchor="w",
            height=36,
            corner_radius=8,
            fg_color="transparent",
            text_color=C["text2"],
            hover_color=C["surface3"],
            command=lambda m=step["method"]: getattr(self, m)(),
        )
        btn.pack(fill="both", expand=True, side="left")

        badge = ctk.CTkLabel(
            row, text="", width=20,
            font=ctk.CTkFont(size=10), text_color=C["green"],
        )
        badge.pack(side="right", padx=(0, 8))

        self._sidebar_buttons[step["id"]] = btn
        self._sidebar_badges[step["id"]] = badge

    def _set_active_step(self, step_id: str, title: str):
        logger.info(f"Step: {step_id} ({title})")
        self.active_step = step_id
        self.topbar_title.configure(text=title)
        for sid, btn in self._sidebar_buttons.items():
            if sid == step_id:
                btn.configure(fg_color=C["accent_dim"], text_color=C["text"])
            else:
                btn.configure(fg_color="transparent", text_color=C["text2"])

    def _mark_step_done(self, step_id: str):
        logger.info(f"Step completed: {step_id}")
        self.completed_steps.add(step_id)
        self._sidebar_badges[step_id].configure(text="  \u2713", text_color=C["green"])
        self._save_project()

    def _mark_step_working(self, step_id: str):
        """Show spinning indicator on sidebar."""
        self._sidebar_badges[step_id].configure(text="  \u25CF", text_color=C["orange"])

    def _mark_step_error(self, step_id: str):
        logger.error(f"Step failed: {step_id}")
        self._sidebar_badges[step_id].configure(text="  !", text_color=C["red"])

    def _go_prev_step(self):
        step_ids = [s["id"] for s in self.STEPS]
        idx = step_ids.index(self.active_step) if self.active_step in step_ids else 0
        if idx > 0:
            method = self.STEPS[idx - 1]["method"]
            getattr(self, method)()

    def _go_next_step(self):
        step_ids = [s["id"] for s in self.STEPS]
        idx = step_ids.index(self.active_step) if self.active_step in step_ids else 0
        if idx < len(step_ids) - 1:
            method = self.STEPS[idx + 1]["method"]
            getattr(self, method)()

    # ══════════════════════════════════════════
    #  Helper: build cards & widgets
    # ══════════════════════════════════════════

    def _clear_content(self):
        for w in self.content_frame.winfo_children():
            w.destroy()

    def _make_card(self, parent, **kwargs) -> ctk.CTkFrame:
        card = ctk.CTkFrame(
            parent,
            fg_color=C["surface"],
            corner_radius=12,
            border_width=1,
            border_color=C["border"],
            **kwargs,
        )
        return card

    def _make_action_btn(self, parent, text, command, accent=True, **kw) -> ctk.CTkButton:
        return ctk.CTkButton(
            parent,
            text=text,
            font=ctk.CTkFont(size=13, weight="bold"),
            height=42,
            corner_radius=10,
            fg_color=C["accent"] if accent else C["surface3"],
            hover_color=C["accent_hover"] if accent else C["border"],
            text_color=C["text"],
            command=command,
            **kw,
        )

    def _make_section_title(self, parent, text):
        ctk.CTkLabel(
            parent, text=text,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=C["text"],
        ).pack(anchor="w", padx=24, pady=(20, 8))

    def _make_step_footer(self, parent, step_id: str):
        """Add a footer with 'Mark as done' checkbox and 'Next Step' button."""
        footer = ctk.CTkFrame(parent, fg_color="transparent")
        footer.pack(fill="x", pady=(16, 0))

        is_done = step_id in self.completed_steps

        done_var = ctk.BooleanVar(value=is_done)
        cb = ctk.CTkCheckBox(
            footer, text=L["step_completed"],
            variable=done_var,
            font=ctk.CTkFont(size=12),
            fg_color=C["green"], text_color=C["text2"],
            command=lambda: self._toggle_step_done(step_id, done_var.get()),
        )
        cb.pack(side="left")

        next_btn = ctk.CTkButton(
            footer, text=L["next_step"],
            font=ctk.CTkFont(size=13, weight="bold"),
            height=38, width=140, corner_radius=10,
            fg_color=C["accent"], hover_color=C["accent_hover"],
            text_color=C["text"],
            command=self._go_next_step,
        )
        next_btn.pack(side="right")

        return footer

    def _toggle_step_done(self, step_id: str, checked: bool):
        if checked:
            self._mark_step_done(step_id)
        else:
            self.completed_steps.discard(step_id)
            self._sidebar_badges[step_id].configure(text="")
            self._save_project()

    def _get_work_dir(self) -> Path:
        """Get the working directory for current project outputs."""
        wd = self.project.get("work_dir")
        if wd and Path(wd).exists():
            return Path(wd)
        # Fallback: next to video
        vp = self.project.get("video_path")
        if vp:
            return Path(vp).parent
        return Path("output")

    def _copy_to_clipboard(self, text: str):
        """Copy text to clipboard and show toast."""
        self.clipboard_clear()
        self.clipboard_append(text)
        self._show_toast(L["copied"], level="success", duration=2000)

    def _play_file(self, filepath: str):
        """Open file in embedded media player."""
        try:
            from .media_player import play_media
        except ImportError:
            try:
                from ui.media_player import play_media
            except ImportError:
                self._show_toast("Media player not available", level="error")
                return
        play_media(self, filepath)

    def _update_status(self, message: str):
        self.topbar_status.configure(text=message, text_color=C["text3"])

    def _set_status_working(self, message: str):
        self.topbar_status.configure(text=message, text_color=C["orange"])

    def _set_status_done(self, message: str):
        self.topbar_status.configure(text=message, text_color=C["green"])

    def _set_status_error(self, message: str):
        self.topbar_status.configure(text=message, text_color=C["red"])

    # ══════════════════════════════════════════
    #  Panels
    # ══════════════════════════════════════════

    # ---------- 01 Import ----------

    def _show_import_panel(self):
        self._clear_content()
        self._set_active_step("import", "Import Video")
        self._update_status(L["select_video_start"])

        wrapper = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        wrapper.pack(expand=True)

        # Drop zone card
        card = self._make_card(wrapper, width=520, height=320)
        card.pack(pady=(0, 24))
        card.pack_propagate(False)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.place(relx=0.5, rely=0.5, anchor="center")

        # If video loaded — show its name
        if self.project["video_path"]:
            name = Path(self.project["video_path"]).name
            ctk.CTkLabel(
                inner, text=L["video_loaded"],
                font=ctk.CTkFont(size=28, weight="bold"), text_color=C["green"],
            ).pack(pady=(0, 8))
            ctk.CTkLabel(
                inner, text=name,
                font=ctk.CTkFont(size=14), text_color=C["text2"],
                wraplength=440,
            ).pack(pady=(0, 20))
            self._make_action_btn(inner, L["choose_another"], self._import_video, accent=False).pack()
        else:
            ctk.CTkLabel(
                inner, text=L["drop_or_select"],
                font=ctk.CTkFont(size=22, weight="bold"), text_color=C["text"],
            ).pack(pady=(0, 8))
            ctk.CTkLabel(
                inner, text=L["supported_formats"],
                font=ctk.CTkFont(size=12), text_color=C["text3"],
            ).pack(pady=(0, 28))
            self._make_action_btn(inner, L["select_video"], self._import_video, width=220).pack()

            # Drag & Drop
            if HAS_DND:
                try:
                    card.drop_target_register(DND_FILES)
                    card.dnd_bind("<<Drop>>", self._on_drop_video)
                except Exception:
                    pass

    # ---------- 02 Edit ----------

    def _show_edit_panel(self):
        if not self._check_deps("edit"):
            return
        self._clear_content()
        self._set_active_step("edit", "Assembly")
        self._update_status("Add intro, outro, overlay and render")

        scroller = ctk.CTkScrollableFrame(self.content_frame, fg_color="transparent")
        scroller.pack(fill="both", expand=True, padx=24, pady=24)

        # ── 1. File pickers (Intro / Outro / Overlay) ──
        files_card = self._make_card(scroller)
        files_card.pack(fill="x", pady=(0, 16))

        files_inner = ctk.CTkFrame(files_card, fg_color="transparent")
        files_inner.pack(fill="x", padx=24, pady=16)

        ctk.CTkLabel(
            files_inner, text="Video Assembly",
            font=ctk.CTkFont(size=16, weight="bold"), text_color=C["text"],
        ).pack(anchor="w")
        ctk.CTkLabel(
            files_inner, text="Choose intro, outro and subscribe overlay, then hit Render",
            font=ctk.CTkFont(size=12), text_color=C["text3"],
        ).pack(anchor="w", pady=(2, 12))

        for label_text, key, picker_cmd, clear_cmd in [
            ("Intro",              "intro_path",              self._pick_intro,              lambda: self._set_intro(None)),
            ("Outro",              "outro_path",              self._pick_outro,              lambda: self._set_outro(None)),
            ("Subscribe Overlay",  "subscribe_overlay_path",  self._pick_subscribe_overlay,  lambda: self._clear_subscribe_overlay()),
        ]:
            row = ctk.CTkFrame(files_inner, fg_color="transparent")
            row.pack(fill="x", pady=3)
            ctk.CTkLabel(row, text=f"{label_text}:", font=ctk.CTkFont(size=12), text_color=C["text2"], width=140, anchor="w").pack(side="left")

            val = self.project.get(key)
            name = Path(val).name if val else "Not set"
            color = C["text"] if val else C["text3"]
            ctk.CTkLabel(row, text=name, font=ctk.CTkFont(size=12), text_color=color).pack(side="left", padx=8, fill="x", expand=True)

            ctk.CTkButton(row, text="Choose", width=70, height=28, font=ctk.CTkFont(size=11),
                           fg_color=C["surface3"], command=picker_cmd).pack(side="right", padx=2)
            if val:
                ctk.CTkButton(row, text="Clear", width=50, height=28, font=ctk.CTkFont(size=11),
                               fg_color=C["surface3"], command=clear_cmd).pack(side="right")

        # Overlay timing (only if overlay is set)
        if self.project.get("subscribe_overlay_path"):
            ovl_opts = ctk.CTkFrame(files_inner, fg_color="transparent")
            ovl_opts.pack(fill="x", pady=(8, 0))
            ctk.CTkLabel(ovl_opts, text="Overlay start (sec):", font=ctk.CTkFont(size=11), text_color=C["text3"]).pack(side="left")
            self._ovl_start = ctk.CTkEntry(ovl_opts, width=70, placeholder_text="60")
            self._ovl_start.pack(side="left", padx=6)
            ctk.CTkLabel(ovl_opts, text="Position:", font=ctk.CTkFont(size=11), text_color=C["text3"]).pack(side="left", padx=(12, 0))
            self._ovl_position = ctk.CTkOptionMenu(ovl_opts, values=["bottom-left", "bottom-right", "top-left", "top-right"], width=120, font=ctk.CTkFont(size=11))
            self._ovl_position.set("bottom-left")
            self._ovl_position.pack(side="left", padx=6)

        # ── 2. Preview thumbnails ──
        has_extras = self.project.get("intro_path") or self.project.get("outro_path")
        if has_extras and HAS_PIL:
            preview_card = self._make_card(scroller)
            preview_card.pack(fill="x", pady=(0, 16))

            preview_inner = ctk.CTkFrame(preview_card, fg_color="transparent")
            preview_inner.pack(fill="x", padx=24, pady=16)

            # Sequence labels
            seq_frame = ctk.CTkFrame(preview_inner, fg_color="transparent")
            seq_frame.pack(fill="x", pady=(0, 8))

            all_parts = []
            if self.project.get("intro_path"):
                all_parts.append(("Intro", self.project["intro_path"]))
            all_parts.append(("Main", self.project["video_path"]))
            if self.project.get("outro_path"):
                all_parts.append(("Outro", self.project["outro_path"]))

            for j, (lbl, _) in enumerate(all_parts):
                if j > 0:
                    ctk.CTkLabel(seq_frame, text="  >  ", font=ctk.CTkFont(size=13, weight="bold"), text_color=C["accent"]).pack(side="left")
                color = C["green"] if lbl == "Main" else C["text2"]
                ctk.CTkLabel(seq_frame, text=lbl, font=ctk.CTkFont(size=12), text_color=color, fg_color=C["surface2"], corner_radius=6).pack(side="left", ipadx=10, ipady=4)

            # Frame thumbnails
            frames_row = ctk.CTkFrame(preview_inner, fg_color="transparent")
            frames_row.pack(fill="x", pady=(4, 0))

            import subprocess as _sp, tempfile as _tf
            ffmpeg = Settings.get_ffmpeg() if Settings else "ffmpeg"
            for lbl, vpath in all_parts:
                try:
                    with _tf.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                        tmp_path = tmp.name
                    _sp.run([ffmpeg, "-y", "-ss", "1", "-i", vpath, "-frames:v", "1", "-q:v", "5", tmp_path], capture_output=True, timeout=10)
                    if Path(tmp_path).stat().st_size > 0:
                        pil_img = PILImage.open(tmp_path)
                        # Preserve aspect ratio — fit in 240x180 box
                        orig_w, orig_h = pil_img.size
                        pil_img.thumbnail((240, 180))
                        disp_w, disp_h = pil_img.size
                        ctk_img = CTkImage(pil_img, size=(disp_w, disp_h))
                        col = ctk.CTkFrame(frames_row, fg_color="transparent")
                        col.pack(side="left", padx=6)
                        ctk.CTkLabel(col, image=ctk_img, text="").pack()
                        ctk.CTkLabel(col, text=lbl, font=ctk.CTkFont(size=10), text_color=C["text3"]).pack()
                    Path(tmp_path).unlink(missing_ok=True)
                except Exception:
                    pass

        # ── 3. Render button (always visible) ──
        render_card = self._make_card(scroller)
        render_card.pack(fill="x", pady=(0, 16))

        render_inner = ctk.CTkFrame(render_card, fg_color="transparent")
        render_inner.pack(fill="x", padx=24, pady=16)

        # Play result if already assembled
        assembled = "_assembled" in str(self.project.get("video_path", "")) or "_final" in str(self.project.get("video_path", ""))
        if assembled:
            play_row = ctk.CTkFrame(render_inner, fg_color="transparent")
            play_row.pack(fill="x", pady=(0, 12))

            ctk.CTkButton(
                play_row, text="Play Result",
                font=ctk.CTkFont(size=13, weight="bold"),
                height=36, width=160, corner_radius=8,
                fg_color=C["green"], hover_color="#00a884", text_color=C["text"],
                command=lambda: self._play_file(self.project["video_path"]),
            ).pack(side="left")
            ctk.CTkLabel(play_row, text=Path(self.project["video_path"]).name, font=ctk.CTkFont(size=11), text_color=C["text3"]).pack(side="left", padx=12)

        self._render_progress = ctk.CTkProgressBar(
            render_inner, height=8, corner_radius=4,
            fg_color=C["surface3"], progress_color=C["green"],
        )
        self._render_progress.pack(fill="x", pady=(0, 12))
        self._render_progress.set(0)

        if has_extras:
            self._render_btn = self._make_action_btn(
                render_inner, "Render Assembly",
                self._run_render_assembly, width=300,
            )
            self._render_btn.pack(fill="x")
        else:
            ctk.CTkLabel(
                render_inner, text="Add Intro or Outro above to enable assembly",
                font=ctk.CTkFont(size=12), text_color=C["text3"],
            ).pack()

        self._make_step_footer(scroller, "edit")

    def _on_video_edited(self, output_path: str):
        self.project["video_path"] = output_path
        self._mark_step_done("edit")
        self._set_status_done(f"Trimmed: {Path(output_path).name}")

    def _run_render_assembly(self):
        """Full assembly pipeline: concat → subscribe overlay → restore audio → mix overlay sound."""
        logger.info("Starting render assembly pipeline")
        self._mark_step_working("edit")
        self._set_status_working("Rendering assembly...")
        self._render_btn.configure(state="disabled", text="Rendering...")
        self._render_progress.set(0.05)

        def render():
            try:
                import logging
                logger = logging.getLogger(__name__)

                videos = []
                if self.project.get("intro_path"):
                    videos.append(self.project["intro_path"])
                videos.append(self.project["video_path"])
                if self.project.get("outro_path"):
                    videos.append(self.project["outro_path"])

                if len(videos) <= 1:
                    self.after(0, lambda: self._show_toast("Nothing to assemble — add intro or outro first.", level="warning"))
                    self.after(0, lambda: self._render_btn.configure(state="normal", text="Render Assembly (Intro + Video + Outro)"))
                    return

                # Step 1: Concat
                self.after(0, lambda: self._set_status_working("Step 1/4: Concatenating videos..."))
                self.after(0, lambda: self._render_progress.set(0.1))

                concat_result = self.video_processor.concat_videos(
                    videos,
                    output_name="merged_video",
                    progress_callback=lambda pct, msg: self.after(0, lambda p=pct: self._render_progress.set(0.1 + p * 0.002)),
                )
                logger.info(f"Concat done: {concat_result}")
                current_video = concat_result

                # Step 2: Subscribe overlay (if overlay file selected)
                overlay_path = self.project.get("subscribe_overlay_path")
                ovl_start_sec = 120.0
                if overlay_path and Path(overlay_path).exists():
                    self.after(0, lambda: self._set_status_working("Step 2/4: Adding subscribe overlay..."))
                    self.after(0, lambda: self._render_progress.set(0.35))

                    try:
                        ovl_start_text = self._ovl_start.get() if hasattr(self, "_ovl_start") else "120"
                        ovl_start_sec = float(ovl_start_text or 120)
                    except ValueError:
                        ovl_start_sec = 120.0

                    position = self._ovl_position.get() if hasattr(self, "_ovl_position") else "bottom-left"

                    if hasattr(self.video_processor, "apply_subscribe_overlay"):
                        current_video = self.video_processor.apply_subscribe_overlay(
                            base_video=current_video,
                            overlay_video=overlay_path,
                            output_name="with_overlay",
                            start_time=ovl_start_sec,
                            position=position,
                        )
                        logger.info(f"Overlay applied: {current_video}")

                # Step 3: Restore original audio (avoid quality degradation)
                self.after(0, lambda: self._set_status_working("Step 3/4: Restoring original audio..."))
                self.after(0, lambda: self._render_progress.set(0.6))

                if hasattr(self.video_processor, "restore_original_audio"):
                    sources = []
                    for v in videos:
                        has_audio = self.video_processor._has_audio_stream(v) if hasattr(self.video_processor, "_has_audio_stream") else True
                        sources.append((v, has_audio))

                    current_video = self.video_processor.restore_original_audio(
                        processed_video=current_video,
                        original_sources=sources,
                        output_name="final_video",
                    )
                    logger.info(f"Audio restored: {current_video}")

                # Step 4: Mix overlay audio (if overlay was applied)
                if overlay_path and Path(overlay_path).exists() and hasattr(self.video_processor, "mix_overlay_audio"):
                    self.after(0, lambda: self._set_status_working("Step 4/4: Mixing overlay sound..."))
                    self.after(0, lambda: self._render_progress.set(0.8))

                    current_video = self.video_processor.mix_overlay_audio(
                        video_path=current_video,
                        overlay_audio_source=overlay_path,
                        overlay_start_ms=int(ovl_start_sec * 1000),
                        output_name="final_with_sound",
                    )
                    logger.info(f"Overlay audio mixed: {current_video}")

                self.project["video_path"] = current_video

                # Cleanup intermediate files
                work_dir = self._get_work_dir()
                for pattern in ["*_with_intro_outro*", "*_with_overlay*", "concat_list.txt", "merged_video.mp4"]:
                    for f in work_dir.glob(pattern):
                        if str(f) != current_video:
                            f.unlink(missing_ok=True)
                            logger.info(f"Cleaned up: {f.name}")

                self.after(0, lambda: self._render_progress.set(1.0))
                self.after(0, lambda: self._mark_step_done("edit"))
                self.after(0, lambda: self._set_status_done("Assembly complete!"))
                self.after(0, lambda: self._show_toast("Video assembled! All 4 steps done.", level="success"))
                self.after(0, lambda: self._render_btn.configure(state="normal", text="Render Assembly (Intro + Video + Outro)"))
                self.after(0, self._show_edit_panel)
            except Exception as e:
                error_msg = str(e)[:200]
                self.after(0, lambda: self._mark_step_error("edit"))
                self.after(0, lambda: self._set_status_error("Assembly failed"))
                self.after(0, lambda: self._show_toast(f"Assembly failed: {error_msg}", level="error", duration=0))
                self.after(0, lambda: self._render_btn.configure(state="normal", text="Render Assembly (Intro + Video + Outro)"))

        threading.Thread(target=render, daemon=True).start()

    # ---------- 03 Transcribe ----------

    def _show_transcribe_panel(self):
        if not self._check_deps("transcribe"):
            return
        self._clear_content()
        self._set_active_step("transcribe", "Transcribe Audio")
        self._update_status(L["ready_to_transcribe"])

        scroller = ctk.CTkScrollableFrame(self.content_frame, fg_color="transparent")
        scroller.pack(fill="both", expand=True, padx=24, pady=24)

        # Action card
        card = self._make_card(scroller)
        card.pack(fill="x", pady=(0, 16))

        card_inner = ctk.CTkFrame(card, fg_color="transparent")
        card_inner.pack(fill="x", padx=24, pady=20)

        ctk.CTkLabel(
            card_inner, text="Transcription",
            font=ctk.CTkFont(size=16, weight="bold"), text_color=C["text"],
        ).pack(anchor="w")

        # Engine toggle
        engine_frame = ctk.CTkFrame(card_inner, fg_color="transparent")
        engine_frame.pack(fill="x", pady=(8, 12))

        self._transcribe_engine = ctk.StringVar(value="whisper")
        ctk.CTkRadioButton(
            engine_frame, text="Whisper (local)", variable=self._transcribe_engine,
            value="whisper", font=ctk.CTkFont(size=12),
            fg_color=C["accent"], text_color=C["text"],
        ).pack(side="left", padx=(0, 16))

        gemini_available = bool(Settings and Settings.GEMINI_API_KEY) if Settings else False
        gemini_rb = ctk.CTkRadioButton(
            engine_frame, text="Gemini (cloud)", variable=self._transcribe_engine,
            value="gemini", font=ctk.CTkFont(size=12),
            fg_color=C["accent"], text_color=C["text"] if gemini_available else C["text3"],
        )
        gemini_rb.pack(side="left", padx=(0, 16))
        if not gemini_available:
            gemini_rb.configure(state="disabled")

        # Parakeet option (check if available)
        parakeet_rb = ctk.CTkRadioButton(
            engine_frame, text="Parakeet (local, fast)", variable=self._transcribe_engine,
            value="parakeet", font=ctk.CTkFont(size=12),
            fg_color=C["accent"], text_color=C["text"],
        )
        parakeet_rb.pack(side="left")

        self._transcribe_progress = ctk.CTkProgressBar(
            card_inner, height=6, corner_radius=3,
            fg_color=C["surface3"], progress_color=C["accent"],
        )
        self._transcribe_progress.pack(fill="x", pady=(0, 12))
        self._transcribe_progress.set(0)

        self._transcribe_btn = self._make_action_btn(card_inner, "Start Transcription", self._run_transcription, width=200)
        self._transcribe_btn.pack(anchor="w")

        # Result card
        if self.project["transcription"]:
            res_card = self._make_card(scroller)
            res_card.pack(fill="both", expand=True)

            self._make_section_title(res_card, "Transcription Result")

            txt = ctk.CTkTextbox(
                res_card, font=ctk.CTkFont(size=13),
                fg_color=C["surface2"], corner_radius=8,
                text_color=C["text"], wrap="word",
            )
            txt.pack(fill="both", expand=True, padx=20, pady=(0, 20))
            txt.insert("1.0", self.project["transcription"])
            txt.configure(state="disabled")

        self._make_step_footer(scroller, "transcribe")

    # ---------- 04 Clean Audio ----------

    def _show_audio_cleanup_panel(self):
        if not self._check_deps("audio"):
            return
        self._clear_content()
        self._set_active_step("audio", "Clean Audio")
        self._update_status(L["ready"])

        scroller = ctk.CTkScrollableFrame(self.content_frame, fg_color="transparent")
        scroller.pack(fill="both", expand=True, padx=24, pady=24)

        card = self._make_card(scroller)
        card.pack(fill="x", pady=(0, 16))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=24, pady=20)

        ctk.CTkLabel(
            inner, text="AI Audio Cleanup",
            font=ctk.CTkFont(size=16, weight="bold"), text_color=C["text"],
        ).pack(anchor="w")
        ctk.CTkLabel(
            inner, text="Remove noise and enhance audio quality",
            font=ctk.CTkFont(size=12), text_color=C["text3"],
        ).pack(anchor="w", pady=(4, 16))

        # Mode selection
        mode_frame = ctk.CTkFrame(inner, fg_color="transparent")
        mode_frame.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            mode_frame, text="Mode:",
            font=ctk.CTkFont(size=13), text_color=C["text2"],
        ).pack(side="left", padx=(0, 12))

        self._audio_mode = ctk.StringVar(value="builtin")
        ctk.CTkRadioButton(
            mode_frame, text="Built-in (FFmpeg)", variable=self._audio_mode,
            value="builtin", font=ctk.CTkFont(size=12),
            fg_color=C["accent"], text_color=C["text"],
        ).pack(side="left", padx=(0, 16))
        ctk.CTkRadioButton(
            mode_frame, text="Auphonic (cloud)", variable=self._audio_mode,
            value="auphonic", font=ctk.CTkFont(size=12),
            fg_color=C["accent"], text_color=C["text"],
        ).pack(side="left")

        # Preset selection
        preset_frame = ctk.CTkFrame(inner, fg_color="transparent")
        preset_frame.pack(fill="x", pady=(0, 16))

        ctk.CTkLabel(
            preset_frame, text="Preset:",
            font=ctk.CTkFont(size=13), text_color=C["text2"],
        ).pack(side="left", padx=(0, 12))

        self._audio_preset = ctk.StringVar(value="medium")
        for preset in ["light", "medium", "aggressive"]:
            ctk.CTkRadioButton(
                preset_frame, text=preset.capitalize(), variable=self._audio_preset,
                value=preset, font=ctk.CTkFont(size=12),
                fg_color=C["accent"], text_color=C["text"],
            ).pack(side="left", padx=(0, 16))

        self._audio_progress = ctk.CTkProgressBar(
            inner, height=6, corner_radius=3,
            fg_color=C["surface3"], progress_color=C["accent"],
        )
        self._audio_progress.pack(fill="x", pady=(0, 12))
        self._audio_progress.set(0)

        self._audio_btn = self._make_action_btn(inner, "Clean Audio", self._run_audio_cleanup, width=200)
        self._audio_btn.pack(anchor="w")

        # Result preview (if cleaned audio exists)
        if self.project.get("audio_path") and Path(self.project["audio_path"]).exists():
            result_card = self._make_card(scroller)
            result_card.pack(fill="x", pady=(16, 0))

            result_inner = ctk.CTkFrame(result_card, fg_color="transparent")
            result_inner.pack(fill="x", padx=24, pady=16)

            ctk.CTkLabel(
                result_inner, text=L["cleaned_audio_ready"],
                font=ctk.CTkFont(size=14, weight="bold"), text_color=C["green"],
            ).pack(anchor="w")

            ctk.CTkLabel(
                result_inner, text=Path(self.project["audio_path"]).name,
                font=ctk.CTkFont(size=12), text_color=C["text3"],
            ).pack(anchor="w", pady=(4, 8))

            play_row = ctk.CTkFrame(result_inner, fg_color="transparent")
            play_row.pack(fill="x")

            ctk.CTkButton(
                play_row, text="Play Cleaned",
                font=ctk.CTkFont(size=13, weight="bold"),
                height=36, width=160, corner_radius=8,
                fg_color=C["green"], hover_color="#00a884",
                text_color=C["text"],
                command=lambda: self._play_file(self.project["audio_path"]),
            ).pack(side="left")

            ctk.CTkButton(
                play_row, text="Play Original",
                font=ctk.CTkFont(size=12),
                height=36, width=140, corner_radius=8,
                fg_color=C["surface3"], hover_color=C["border"],
                text_color=C["text2"],
                command=lambda: self._play_file(self.project.get("original_video_path") or self.project["video_path"]),
            ).pack(side="left", padx=8)

            ctk.CTkButton(
                play_row, text="Stop",
                font=ctk.CTkFont(size=12),
                height=36, width=70, corner_radius=8,
                fg_color=C["red"], hover_color="#cc5555",
                text_color=C["text"],
                command=self._stop_audio,
            ).pack(side="left", padx=4)

            # Use cleaned audio checkbox
            use_cleaned = self.project.get("use_cleaned_audio", True)
            self._use_cleaned_var = ctk.BooleanVar(value=use_cleaned)
            ctk.CTkCheckBox(
                result_inner, text="Use cleaned audio in final render",
                variable=self._use_cleaned_var,
                font=ctk.CTkFont(size=12),
                fg_color=C["green"], text_color=C["text"],
                command=self._toggle_use_cleaned_audio,
            ).pack(anchor="w", pady=(12, 0))

        self._make_step_footer(scroller, "audio")

    # ---------- 05 Titles ----------

    def _show_titles_panel(self):
        if not self._check_deps("titles"):
            return
        self._clear_content()
        self._set_active_step("titles", "Generate Titles")

        # Check if transcription is ready
        if not self.project.get("transcription") and "transcribe" not in self.completed_steps:
            self._update_status("Waiting for transcription...")
            wrapper = ctk.CTkFrame(self.content_frame, fg_color="transparent")
            wrapper.pack(expand=True)
            ctk.CTkLabel(
                wrapper, text=L["transcription_in_progress"],
                font=ctk.CTkFont(size=16), text_color=C["orange"],
            ).pack(pady=(0, 8))
            ctk.CTkLabel(
                wrapper, text="Titles will be generated based on transcription.\nPlease wait or go to step 03 to check progress.",
                font=ctk.CTkFont(size=12), text_color=C["text3"], justify="center",
            ).pack()
            # Auto-refresh in 3 seconds
            self.after(3000, lambda: self._show_titles_panel() if self.active_step == "titles" else None)
            return

        self._update_status(L["ready"])

        scroller = ctk.CTkScrollableFrame(self.content_frame, fg_color="transparent")
        scroller.pack(fill="both", expand=True, padx=24, pady=24)

        # Action card
        card = self._make_card(scroller)
        card.pack(fill="x", pady=(0, 16))

        card_inner = ctk.CTkFrame(card, fg_color="transparent")
        card_inner.pack(fill="x", padx=24, pady=20)

        ctk.CTkLabel(
            card_inner, text="AI Title Generator",
            font=ctk.CTkFont(size=16, weight="bold"), text_color=C["text"],
        ).pack(anchor="w")
        ctk.CTkLabel(
            card_inner, text="Generate engaging titles based on transcription",
            font=ctk.CTkFont(size=12), text_color=C["text3"],
        ).pack(anchor="w", pady=(4, 8))

        # Custom prompt input
        ctk.CTkLabel(card_inner, text="Additional context (optional):", font=ctk.CTkFont(size=11), text_color=C["text3"]).pack(anchor="w")
        self._titles_custom_prompt = ctk.CTkTextbox(
            card_inner, height=50, font=ctk.CTkFont(size=12),
            fg_color=C["surface2"], corner_radius=6, text_color=C["text"],
        )
        self._titles_custom_prompt.pack(fill="x", pady=(4, 12))

        self._titles_btn = self._make_action_btn(card_inner, "Generate Titles + Critique", self._run_title_generation, width=240)
        self._titles_btn.pack(anchor="w")

        # Generated titles
        if self.project["titles"]:
            self._make_section_title(scroller, "Choose a title")
            for i, title_text in enumerate(self.project["titles"], 1):
                row = self._make_card(scroller)
                row.pack(fill="x", pady=3)

                row_inner = ctk.CTkFrame(row, fg_color="transparent")
                row_inner.pack(fill="x", padx=8, pady=4)

                btn = ctk.CTkButton(
                    row_inner,
                    text=f"  {i}.  {title_text}",
                    font=ctk.CTkFont(size=13),
                    anchor="w", height=40, corner_radius=8,
                    fg_color="transparent",
                    hover_color=C["accent_dim"],
                    text_color=C["text"],
                    command=lambda t=title_text: self._select_title(t),
                )
                btn.pack(side="left", fill="x", expand=True)

                if self.project["selected_title"] == title_text:
                    btn.configure(fg_color=C["accent_dim"])

                # Copy button
                ctk.CTkButton(
                    row_inner, text="Копировать", width=80, height=26,
                    font=ctk.CTkFont(size=10), fg_color=C["surface3"], hover_color=C["border"],
                    text_color=C["text2"],
                    command=lambda t=title_text: self._copy_to_clipboard(t),
                ).pack(side="right", padx=4)

                # Score badge if critique exists
                critique = self.project.get("title_critiques", {}).get(title_text)
                if critique:
                    score = critique.get("score", 0)
                    color = C["green"] if score >= 70 else C["orange"] if score >= 50 else C["red"]
                    ctk.CTkLabel(
                        row_inner, text=f"{score}/100",
                        font=ctk.CTkFont(size=11, weight="bold"),
                        text_color=color, width=60,
                    ).pack(side="right", padx=4)

            # Critique button
            critique_frame = ctk.CTkFrame(scroller, fg_color="transparent")
            critique_frame.pack(fill="x", pady=(8, 0))

            self._critique_btn = self._make_action_btn(
                critique_frame, "Critique All Titles", self._run_title_critique, accent=False, width=200
            )
            self._critique_btn.pack(side="left")

            # Critique details for selected title
            sel = self.project.get("selected_title")
            if sel and sel in self.project.get("title_critiques", {}):
                crit = self.project["title_critiques"][sel]
                detail_card = self._make_card(scroller)
                detail_card.pack(fill="x", pady=(12, 0))
                detail_inner = ctk.CTkFrame(detail_card, fg_color="transparent")
                detail_inner.pack(fill="x", padx=20, pady=16)

                scores_text = (
                    f"Overall: {crit.get('score', '?')}/100  |  "
                    f"SEO: {crit.get('seo_score', '?')}/100  |  "
                    f"Engagement: {crit.get('engagement_score', '?')}/100"
                )
                ctk.CTkLabel(detail_inner, text=scores_text, font=ctk.CTkFont(size=12, weight="bold"), text_color=C["text"]).pack(anchor="w")

                for label, key, color in [("Strengths", "strengths", C["green"]), ("Weaknesses", "weaknesses", C["red"]), ("Suggestions", "suggestions", C["blue"])]:
                    items = crit.get(key, [])
                    if items:
                        ctk.CTkLabel(detail_inner, text=f"{label}:", font=ctk.CTkFont(size=11, weight="bold"), text_color=color).pack(anchor="w", pady=(8, 2))
                        for item in items:
                            ctk.CTkLabel(detail_inner, text=f"  - {item}", font=ctk.CTkFont(size=11), text_color=C["text2"], wraplength=600).pack(anchor="w")

        self._make_step_footer(scroller, "titles")

    # ---------- 06 Thumbnail ----------

    def _show_thumbnail_panel(self):
        if not self._check_deps("thumbnail"):
            return
        self._clear_content()
        self._set_active_step("thumbnail", "Create Thumbnail")

        # Wait for transcription if not done
        if not self.project.get("transcription") and "transcribe" not in self.completed_steps:
            self._update_status("Waiting for transcription...")
            wrapper = ctk.CTkFrame(self.content_frame, fg_color="transparent")
            wrapper.pack(expand=True)
            ctk.CTkLabel(wrapper, text=L["transcription_in_progress"], font=ctk.CTkFont(size=16), text_color=C["orange"]).pack(pady=(0, 8))
            ctk.CTkLabel(wrapper, text="Thumbnails will use transcription for better prompts.\nPlease wait.", font=ctk.CTkFont(size=12), text_color=C["text3"], justify="center").pack()
            self.after(3000, lambda: self._show_thumbnail_panel() if self.active_step == "thumbnail" else None)
            return

        self._update_status(L["ready"])

        scroller = ctk.CTkScrollableFrame(self.content_frame, fg_color="transparent")
        scroller.pack(fill="both", expand=True, padx=24, pady=24)

        # Action card
        card = self._make_card(scroller)
        card.pack(fill="x", pady=(0, 16))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=24, pady=20)

        ctk.CTkLabel(
            inner, text="Thumbnail Generator",
            font=ctk.CTkFont(size=16, weight="bold"), text_color=C["text"],
        ).pack(anchor="w")

        title_text = self.project.get("selected_title") or ""
        ctk.CTkLabel(
            inner, text=f'Title: "{title_text[:60]}"',
            font=ctk.CTkFont(size=12), text_color=C["text3"], wraplength=500,
        ).pack(anchor="w", pady=(4, 12))

        self._thumb_progress = ctk.CTkProgressBar(
            inner, height=6, corner_radius=3,
            fg_color=C["surface3"], progress_color=C["accent"],
        )
        self._thumb_progress.pack(fill="x", pady=(0, 8))
        self._thumb_progress.set(0)

        # Custom prompt
        ctk.CTkLabel(inner, text="Additional prompt (optional):", font=ctk.CTkFont(size=11), text_color=C["text3"]).pack(anchor="w")
        self._thumb_custom_prompt = ctk.CTkTextbox(
            inner, height=40, font=ctk.CTkFont(size=12),
            fg_color=C["surface2"], corner_radius=6, text_color=C["text"],
        )
        self._thumb_custom_prompt.pack(fill="x", pady=(4, 8))

        # Reference image picker
        ref_row = ctk.CTkFrame(inner, fg_color="transparent")
        ref_row.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(ref_row, text="Reference image:", font=ctk.CTkFont(size=11), text_color=C["text3"]).pack(side="left")
        self._thumb_ref_label = ctk.CTkLabel(
            ref_row, text=Path(self.project.get("reference_image", "") or "").name or "None",
            font=ctk.CTkFont(size=11), text_color=C["text2"],
        )
        self._thumb_ref_label.pack(side="left", padx=8)
        ctk.CTkButton(
            ref_row, text="Choose", width=60, height=26, font=ctk.CTkFont(size=11),
            fg_color=C["surface3"], command=self._pick_reference_image,
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            ref_row, text="Clear", width=50, height=26, font=ctk.CTkFont(size=11),
            fg_color=C["surface3"], command=lambda: self._set_reference_image(None),
        ).pack(side="left")

        self._thumb_btn = self._make_action_btn(inner, "Generate 3 Thumbnails", self._run_thumbnail_generation, width=240)
        self._thumb_btn.pack(anchor="w")

        # Gallery of existing thumbnails
        thumb_paths = self.project.get("thumbnail_paths", [])
        if thumb_paths and HAS_PIL:
            self._make_section_title(scroller, "Choose a thumbnail")
            gallery = ctk.CTkFrame(scroller, fg_color="transparent")
            gallery.pack(fill="x", pady=(0, 16))

            for i, tp in enumerate(thumb_paths):
                if not Path(tp).exists():
                    continue
                col = self._make_card(gallery)
                col.pack(side="left", padx=6, expand=True, fill="x")

                try:
                    pil_img = PILImage.open(tp)
                    pil_img.thumbnail((320, 180))
                    ctk_img = CTkImage(pil_img, size=(320, 180))
                    img_label = ctk.CTkLabel(col, image=ctk_img, text="")
                    img_label.pack(padx=8, pady=(8, 4))
                except Exception:
                    ctk.CTkLabel(col, text=f"Thumbnail {i+1}", text_color=C["text3"]).pack(padx=8, pady=8)

                is_selected = (self.project.get("thumbnail_path") == tp)
                btn_text = "Selected" if is_selected else f"Use #{i+1}"
                btn_color = C["green"] if is_selected else C["accent"]
                ctk.CTkButton(
                    col, text=btn_text, height=30, font=ctk.CTkFont(size=11),
                    fg_color=btn_color, text_color=C["text"],
                    command=lambda p=tp: self._select_thumbnail(p),
                ).pack(padx=8, pady=(0, 8))

        self._make_step_footer(scroller, "thumbnail")

    def _select_thumbnail(self, path: str):
        self.project["thumbnail_path"] = path
        self._mark_step_done("thumbnail")
        self._set_status_done(f"Thumbnail selected: {Path(path).name}")
        self._show_thumbnail_panel()

    def _pick_reference_image(self):
        fp = filedialog.askopenfilename(title="Select Reference Image", filetypes=[("Images", "*.png *.jpg *.jpeg *.webp")])
        if fp:
            self._set_reference_image(fp)

    def _set_reference_image(self, path):
        self.project["reference_image"] = path
        if hasattr(self, "_thumb_ref_label"):
            self._thumb_ref_label.configure(text=Path(path).name if path else "None")
        self._save_project()

    # ---------- 07 Description ----------

    def _show_description_panel(self):
        if not self._check_deps("description"):
            return
        self._clear_content()
        self._set_active_step("description", "Описание видео")

        # Wait for transcription
        if not self.project.get("transcription") and "transcribe" not in self.completed_steps:
            self._update_status("Ожидание транскрипции...")
            wrapper = ctk.CTkFrame(self.content_frame, fg_color="transparent")
            wrapper.pack(expand=True)
            ctk.CTkLabel(wrapper, text="Транскрипция выполняется...", font=ctk.CTkFont(size=16), text_color=C["orange"]).pack(pady=(0, 8))
            ctk.CTkLabel(wrapper, text="Описания генерируются на основе транскрипции.", font=ctk.CTkFont(size=12), text_color=C["text3"]).pack()
            self.after(3000, lambda: self._show_description_panel() if self.active_step == "description" else None)
            return

        self._update_status("Готово")

        scroller = ctk.CTkScrollableFrame(self.content_frame, fg_color="transparent")
        scroller.pack(fill="both", expand=True, padx=24, pady=24)

        # Generate button
        card = self._make_card(scroller)
        card.pack(fill="x", pady=(0, 16))

        card_inner = ctk.CTkFrame(card, fg_color="transparent")
        card_inner.pack(fill="x", padx=24, pady=16)

        ctk.CTkLabel(card_inner, text="Генератор описаний", font=ctk.CTkFont(size=16, weight="bold"), text_color=C["text"]).pack(anchor="w")
        ctk.CTkLabel(card_inner, text="AI генерирует 3 варианта описания на основе транскрипции", font=ctk.CTkFont(size=12), text_color=C["text3"]).pack(anchor="w", pady=(2, 12))

        self._desc_gen_btn = self._make_action_btn(card_inner, "Сгенерировать описания", self._run_description_generation, width=260)
        self._desc_gen_btn.pack(anchor="w")

        # Show existing descriptions
        descriptions = self.project.get("descriptions", [])
        if descriptions:
            self._make_section_title(scroller, f"Варианты описаний ({len(descriptions)})")

            for i, desc_text in enumerate(descriptions):
                d_card = self._make_card(scroller)
                d_card.pack(fill="x", pady=4)

                d_inner = ctk.CTkFrame(d_card, fg_color="transparent")
                d_inner.pack(fill="x", padx=16, pady=12)

                # Header with label + copy button
                d_header = ctk.CTkFrame(d_inner, fg_color="transparent")
                d_header.pack(fill="x")

                label = "Лучшее описание" if i == 0 else f"Вариант {i + 1}"
                color = C["green"] if i == 0 else C["text2"]
                ctk.CTkLabel(d_header, text=label, font=ctk.CTkFont(size=13, weight="bold"), text_color=color).pack(side="left")

                ctk.CTkButton(
                    d_header, text="Копировать", width=100, height=28,
                    font=ctk.CTkFont(size=11), fg_color=C["accent"], hover_color=C["accent_hover"],
                    text_color=C["text"],
                    command=lambda t=desc_text: self._copy_to_clipboard(t),
                ).pack(side="right")

                if i == 0:
                    ctk.CTkButton(
                        d_header, text="Выбрать", width=80, height=28,
                        font=ctk.CTkFont(size=11), fg_color=C["green"], hover_color="#00a884",
                        text_color=C["text"],
                        command=lambda t=desc_text: self._select_description(t),
                    ).pack(side="right", padx=4)

                # Description text (full, scrollable)
                d_text = ctk.CTkTextbox(
                    d_inner, height=120, font=ctk.CTkFont(size=12),
                    fg_color=C["surface2"], corner_radius=6, text_color=C["text"], wrap="word",
                )
                d_text.pack(fill="x", pady=(8, 0))
                d_text.insert("1.0", desc_text)
                d_text.configure(state="disabled")

        self._make_step_footer(scroller, "description")

    def _select_description(self, text: str):
        self.project["description"] = text
        self._mark_step_done("description")
        self._show_toast("Описание выбрано!", level="success")
        self._show_description_panel()

    # ---------- 08 Preview ----------

    def _show_preview_panel(self):
        self._clear_content()
        self._set_active_step("preview", "Preview")
        self._update_status("Preview your work")

        if not self.project["video_path"]:
            wrapper = ctk.CTkFrame(self.content_frame, fg_color="transparent")
            wrapper.pack(expand=True)
            ctk.CTkLabel(
                wrapper, text=L["no_video"],
                font=ctk.CTkFont(size=16), text_color=C["text3"],
            ).pack()
            return

        try:
            from .preview_panel import PreviewPanel
        except ImportError:
            from ui.preview_panel import PreviewPanel

        # Show assembled video if available, otherwise original
        video_to_preview = self.project["video_path"]
        if self.project.get("intro_path") or self.project.get("outro_path"):
            # Check if assembled version exists
            assembled = self._get_work_dir() / f"{Path(self.project['original_video_path'] or self.project['video_path']).stem}_assembled.mp4"
            if assembled.exists():
                video_to_preview = str(assembled)

        preview = PreviewPanel(self.content_frame, on_preview_error=lambda e: self._set_status_error(e))
        preview.pack(fill="both", expand=True, padx=24, pady=24)
        preview.load_video(Path(video_to_preview))

    # ---------- 08 Upload ----------

    def _show_upload_panel(self):
        if not self._check_deps("upload"):
            return
        self._clear_content()
        self._set_active_step("upload", "Export / Upload")
        self._update_status("Save locally or upload to YouTube")

        scroller = ctk.CTkScrollableFrame(self.content_frame, fg_color="transparent")
        scroller.pack(fill="both", expand=True, padx=24, pady=24)

        # ── Save Locally card ──
        save_card = self._make_card(scroller)
        save_card.pack(fill="x", pady=(0, 12))

        save_inner = ctk.CTkFrame(save_card, fg_color="transparent")
        save_inner.pack(fill="x", padx=24, pady=16)

        ctk.CTkLabel(save_inner, text="Save Locally", font=ctk.CTkFont(size=14, weight="bold"), text_color=C["text"]).pack(anchor="w")
        ctk.CTkLabel(save_inner, text="Export all project files to a folder", font=ctk.CTkFont(size=11), text_color=C["text3"]).pack(anchor="w", pady=(2, 8))

        self._make_action_btn(save_inner, "Save to Folder...", self._save_locally, width=200).pack(anchor="w")

        # ── Description generation (compact) ──
        desc_card = self._make_card(scroller)
        desc_card.pack(fill="x", pady=(0, 12))

        desc_inner = ctk.CTkFrame(desc_card, fg_color="transparent")
        desc_inner.pack(fill="x", padx=24, pady=12)

        desc_row = ctk.CTkFrame(desc_inner, fg_color="transparent")
        desc_row.pack(fill="x")

        ctk.CTkLabel(desc_row, text=L.get("ai_description", "AI-описание"), font=ctk.CTkFont(size=13, weight="bold"), text_color=C["text"]).pack(side="left")
        if self.project.get("descriptions"):
            ctk.CTkLabel(desc_row, text=f"  \u2713 {len(self.project['descriptions'])} вариантов", font=ctk.CTkFont(size=11), text_color=C["green"]).pack(side="left", padx=8)

        self._desc_btn = self._make_action_btn(desc_row, L.get("generate_desc", "Сгенерировать"), self._run_description_generation, accent=False, width=140, height=30)
        self._desc_btn.pack(side="right")

        # Show descriptions with copy buttons
        descriptions = self.project.get("descriptions", [])
        if descriptions:
            for i, desc_text in enumerate(descriptions):
                d_frame = ctk.CTkFrame(desc_inner, fg_color=C["surface2"], corner_radius=8)
                d_frame.pack(fill="x", pady=(8, 0))

                d_header = ctk.CTkFrame(d_frame, fg_color="transparent")
                d_header.pack(fill="x", padx=12, pady=(8, 0))

                label = "Лучшее" if i == 0 else f"Вариант {i + 1}"
                color = C["green"] if i == 0 else C["text2"]
                ctk.CTkLabel(d_header, text=label, font=ctk.CTkFont(size=11, weight="bold"), text_color=color).pack(side="left")

                ctk.CTkButton(
                    d_header, text="Копировать", width=90, height=24,
                    font=ctk.CTkFont(size=10), fg_color=C["accent"], hover_color=C["accent_hover"],
                    text_color=C["text"],
                    command=lambda t=desc_text: self._copy_to_clipboard(t),
                ).pack(side="right")

                d_preview = ctk.CTkLabel(
                    d_frame, text=desc_text[:150] + "..." if len(desc_text) > 150 else desc_text,
                    font=ctk.CTkFont(size=11), text_color=C["text3"],
                    wraplength=600, justify="left",
                )
                d_preview.pack(fill="x", padx=12, pady=(4, 8), anchor="w")

        # ── YouTube Upload ──
        try:
            from .youtube_panel import YouTubePanel
        except ImportError:
            from ui.youtube_panel import YouTubePanel

        yt_card = self._make_card(scroller)
        yt_card.pack(fill="x", pady=(0, 12))

        yt_inner = ctk.CTkFrame(yt_card, fg_color="transparent")
        yt_inner.pack(fill="x", padx=24, pady=12)

        ctk.CTkLabel(yt_inner, text="YouTube Upload", font=ctk.CTkFont(size=14, weight="bold"), text_color=C["text"]).pack(anchor="w", pady=(0, 8))

        panel = YouTubePanel(yt_inner, artifacts_manager=self.artifacts)
        panel.pack(fill="x")

        if self.project.get("selected_title"):
            panel.title_entry.insert(0, self.project["selected_title"])
        if self.project.get("description"):
            panel.desc_textbox.insert("1.0", self.project["description"])
        elif self.project.get("transcription"):
            panel.desc_textbox.insert("1.0", self.project["transcription"][:500])

        self._make_step_footer(scroller, "upload")

    # ══════════════════════════════════════════
    #  Actions
    # ══════════════════════════════════════════

    def _require_video(self) -> bool:
        if not self.project["video_path"]:
            messagebox.showwarning("No Video", "Please import a video first!")
            return False
        return True

    def _import_video(self):
        filetypes = [("Video files", "*.mp4 *.mov *.avi *.mkv"), ("All files", "*.*")]
        filepath = filedialog.askopenfilename(title="Select Video File", filetypes=filetypes)
        if filepath:
            self._confirm_and_import(filepath)

    def _on_drop_video(self, event):
        """Handle drag & drop file."""
        filepath = event.data.strip().strip("{}")  # tkdnd wraps in braces
        if filepath and Path(filepath).suffix.lower() in (".mp4", ".mov", ".avi", ".mkv"):
            self._confirm_and_import(filepath)

    def _confirm_and_import(self, filepath: str):
        """If a project is active, warn user and save it before importing new video."""
        has_progress = bool(self.completed_steps - {"import"})

        if has_progress:
            # Save current project first
            try:
                from core.project import ProjectManager
                pm = ProjectManager()
                name = Path(self.project.get("video_path", "untitled")).stem
                state = dict(self.project)
                state["completed_steps"] = list(self.completed_steps)
                existing = pm.list_projects()
                proj_path = None
                for p in existing:
                    if p.get("video_name") == Path(self.project.get("video_path", "")).name:
                        proj_path = Path(p["path"])
                        break
                if proj_path:
                    pm.save_project_state(proj_path, state)
                else:
                    pm.create_project(name, self.project["video_path"])
                logger.info(f"Saved current project: {name}")
            except Exception as e:
                logger.error(f"Could not save current project: {e}")

            # Ask user
            from tkinter import messagebox
            proceed = messagebox.askyesno(
                "Новый проект",
                "Текущий прогресс будет сброшен.\n"
                "Проект сохранён — вернуться можно через Проекты.\n\n"
                "Продолжить с новым видео?",
            )
            if not proceed:
                return

            # Reset state
            self.project = {k: ([] if isinstance(v, list) else ({} if isinstance(v, dict) else None))
                            for k, v in self.project.items()}
            self.completed_steps.clear()
            for sid in self._sidebar_badges:
                self._sidebar_badges[sid].configure(text="")

        self._import_video_from_path(filepath)

    @staticmethod
    def _create_work_dir(video_path: str) -> Path:
        """Create a unique working directory next to the source video.

        Format: {video_dir}/video_studio_{video_stem}/
        If exists: video_studio_{video_stem} (1), (2), etc.
        """
        src = Path(video_path)
        base_name = f"video_studio_{src.stem}"
        parent = src.parent
        work_dir = parent / base_name

        if not work_dir.exists():
            work_dir.mkdir(parents=True)
            return work_dir

        # Find next available (N)
        n = 1
        while True:
            candidate = parent / f"{base_name} ({n})"
            if not candidate.exists():
                candidate.mkdir(parents=True)
                return candidate
            n += 1

    def _import_video_from_path(self, filepath: str):
        """Common import logic for file dialog and drag & drop."""
        logger.info(f"Importing video: {filepath}")
        self.project["video_path"] = filepath
        self.project["original_video_path"] = filepath

        # Create dedicated work directory
        work_dir = self._create_work_dir(filepath)
        self.project["work_dir"] = str(work_dir)

        video_name = Path(filepath).stem
        self.artifacts = ArtifactsManager(project_name=video_name)
        self.video_processor.artifacts = self.artifacts
        self._mark_step_done("import")
        self._set_status_done(f"Loaded: {Path(filepath).name}")
        self._show_import_panel()

        import logging
        logging.getLogger(__name__).info(f"Work directory: {work_dir}")

        # Auto-start transcription + audio cleanup in background
        if "transcribe" not in self.completed_steps:
            self.after(500, self._auto_transcribe)
        if "audio" not in self.completed_steps:
            self.after(800, self._auto_audio_cleanup)

    def _auto_transcribe(self):
        """Start transcription automatically in background after import."""
        if self.project.get("transcription") or "transcribe" not in self.STEP_DEPS:
            return
        self._mark_step_working("transcribe")
        self._set_status_working("Auto-transcribing in background...")

        def transcribe_bg():
            try:
                logger.info("Auto-transcription started (chunked)...")

                try:
                    from processors.chunked_transcriber import transcribe_chunked
                except ImportError:
                    from src.processors.chunked_transcriber import transcribe_chunked

                def whisper_fn(wav_path: str) -> str:
                    result = self.whisper.transcribe(wav_path)
                    return result.get("text", "")

                srt_text = transcribe_chunked(
                    self.project["video_path"], whisper_fn,
                    progress_callback=lambda p, m: logger.info(f"Transcribe: {p:.0f}% {m}"),
                )
                self.project["transcription"] = srt_text

                # Calculate intro duration for SRT shift
                # Generate content summary for titles/thumbnails/descriptions
                transcript = self.project.get("transcription", "")
                if transcript and len(transcript) > 200:
                    # Take first 1000 chars, extract key terms
                    snippet = transcript[:1000]
                    # Simple extraction: find capitalized tech terms
                    import re as _re
                    tech_terms = set(_re.findall(r'\b[A-Z][a-zA-Z.]+\b', snippet))
                    terms_str = ", ".join(list(tech_terms)[:10])
                    self.project["content_summary"] = f"{snippet[:300]}... Ключевые термины: {terms_str}"
                    logger.info(f"Content summary: {len(self.project['content_summary'])} chars, terms: {terms_str}")

                # Shift SRT timestamps by intro duration
                if self.project.get("intro_path"):
                    try:
                        intro_info = self.video_processor.get_video_info(self.project["intro_path"])
                        intro_dur = intro_info.duration
                        self.project["intro_duration"] = intro_dur
                        logger.info(f"Shifting SRT by intro duration: {intro_dur:.1f}s")

                        from processors.chunked_transcriber import _shift_srt_timestamps
                        self.project["transcription"] = _shift_srt_timestamps(
                            self.project["transcription"], intro_dur
                        )
                    except ImportError:
                        try:
                            from src.processors.chunked_transcriber import _shift_srt_timestamps
                            self.project["transcription"] = _shift_srt_timestamps(
                                self.project["transcription"], intro_dur
                            )
                        except Exception:
                            pass
                    except Exception as e:
                        logger.error(f"SRT shift failed: {e}")

                self.after(0, lambda: self._mark_step_done("transcribe"))
                self.after(0, lambda: self._show_toast(L["transcription_complete"], level="success"))
                logger.info("Auto-transcription finished, launching titles + thumbnails + descriptions")

                # Auto-generate titles + thumbnails in background
                self.after(500, self._auto_generate_titles)
                self.after(1000, self._auto_generate_thumbnails)
                self.after(1500, self._auto_generate_descriptions)
            except Exception as e:
                self.after(0, lambda: self._mark_step_error("transcribe"))
                self.after(0, lambda: self._show_toast(f"Auto-transcription failed: {str(e)[:100]}", level="error", duration=0))

        threading.Thread(target=transcribe_bg, daemon=True).start()

    def _auto_audio_cleanup(self):
        """Background audio cleanup after import."""
        if self.project.get("audio_path"):
            return
        self._mark_step_working("audio")

        def cleanup_bg():
            try:
                import logging
                logger = logging.getLogger(__name__)
                logger.info("Auto audio cleanup started...")

                source = self.project.get("original_video_path") or self.project["video_path"]
                output_path = self._get_work_dir() / "audio_cleaned.wav"
                cleanup_processor = AudioCleanup(mode="builtin")
                cleanup_processor.cleanup(source, str(output_path), preset="medium")
                self.project["audio_path"] = str(output_path)
                self.project["use_cleaned_audio"] = True

                self.after(0, lambda: self._mark_step_done("audio"))
                self.after(0, lambda: self._show_toast("Audio cleaned!", level="success"))
                self.after(0, lambda: self._save_project())
                logger.info("Auto audio cleanup finished")
            except Exception as e:
                self.after(0, lambda: self._mark_step_error("audio"))
                import logging
                logging.getLogger(__name__).error(f"Auto audio cleanup failed: {e}")

        threading.Thread(target=cleanup_bg, daemon=True).start()

    def _auto_generate_titles(self):
        """Background title generation with quality threshold 90/100, up to 3 iterations."""
        if self.project.get("titles"):
            return
        self._mark_step_working("titles")

        QUALITY_THRESHOLD = 90
        MAX_ITERATIONS = 3

        def gen():
            try:
                transcript = self.project.get("transcription", "")
                best_titles = []
                best_critiques = {}
                best_score = 0

                for iteration in range(1, MAX_ITERATIONS + 1):
                    logger.info(f"Title generation iteration {iteration}/{MAX_ITERATIONS}")
                    self.after(0, lambda i=iteration: self._set_status_working(
                        f"Генерация заголовков (попытка {i}/{MAX_ITERATIONS})..."
                    ))

                    titles = self.title_generator.generate_titles(transcript=transcript, count=5, style="engaging")

                    # Strip angle brackets from titles (YouTube removes them)
                    titles = [t.replace("<", "(").replace(">", ")") for t in titles]

                    # Critique all
                    critiques = {}
                    for t in titles:
                        try:
                            critiques[t] = self.title_generator.critique_title(t, transcript=transcript)
                        except Exception:
                            pass

                    # Find best score
                    top_score = max((c.get("score", 0) for c in critiques.values()), default=0)
                    logger.info(f"Iteration {iteration}: best score {top_score}/100")

                    if top_score > best_score:
                        best_titles = titles
                        best_critiques = critiques
                        best_score = top_score

                    if top_score >= QUALITY_THRESHOLD:
                        logger.info(f"Quality threshold {QUALITY_THRESHOLD} reached at iteration {iteration}")
                        break

                self.project["titles"] = best_titles
                self.project["title_critiques"] = best_critiques

                self.after(0, lambda: self._mark_step_done("titles"))
                self.after(0, lambda: self._show_toast(
                    f"{len(best_titles)} заголовков (лучший: {best_score}/100)", level="success"
                ))
                self.after(0, lambda: self._save_project())
                logger.info(f"Auto-generated {len(best_titles)} titles, best score: {best_score}")
            except Exception as e:
                self.after(0, lambda: self._mark_step_error("titles"))
                self.after(0, lambda: self._show_toast(f"Ошибка генерации заголовков: {str(e)[:100]}", level="error", duration=0))

        threading.Thread(target=gen, daemon=True).start()

    def _auto_generate_thumbnails(self):
        """Background thumbnail generation after auto-transcribe."""
        if self.project.get("thumbnail_paths"):
            return  # Already generated
        self._mark_step_working("thumbnail")

        def gen():
            try:
                import logging
                logger = logging.getLogger(__name__)
                logger.info("Auto-generating thumbnails...")

                title = self.project.get("selected_title") or Path(self.project["video_path"]).stem
                content_summary = self.project.get("content_summary") or self.project.get("transcription", "")[:500]
                logger.info(f"Thumbnail context: title='{title[:50]}', summary={len(content_summary)} chars")
                output_dir = self._get_work_dir() / "thumbnails"

                paths = self.cover_generator.generate_covers(
                    title=title, description=content_summary, count=3,
                    styles=["vibrant", "dark", "cozy"],
                    output_dir=output_dir,
                    reference_image_path=self.project.get("reference_image") or os.getenv("REFERENCE_IMAGE", ""),
                )
                str_paths = [str(p) for p in paths]
                self.project["thumbnail_paths"] = str_paths
                if str_paths:
                    self.project["thumbnail_path"] = str_paths[0]

                self.after(0, lambda: self._mark_step_done("thumbnail"))
                self.after(0, lambda: self._show_toast(f"{len(paths)} thumbnails generated!", level="success"))
                self.after(0, lambda: self._save_project())
                logger.info(f"Auto-generated {len(paths)} thumbnails")
            except Exception as e:
                self.after(0, lambda: self._mark_step_error("thumbnail"))
                self.after(0, lambda: self._show_toast(f"Thumbnail generation failed: {str(e)[:100]}", level="error", duration=0))

        threading.Thread(target=gen, daemon=True).start()

    def _auto_generate_descriptions(self):
        """Background description generation after auto-transcribe."""
        if self.project.get("description"):
            return

        def gen():
            try:
                logger.info("Auto-generating descriptions...")
                gen = DescriptionGenerator()
                descriptions = gen.generate_descriptions(
                    transcript=self.project.get("transcription", ""),
                    title=self.project.get("selected_title") or Path(self.project["video_path"]).stem,
                    count=3,
                )
                if descriptions:
                    self.project["description"] = descriptions[0]
                    self.project["descriptions"] = descriptions
                self.after(0, lambda: self._show_toast(L["descriptions_generated"], level="success"))
                self.after(0, lambda: self._save_project())
                logger.info(f"Auto-generated {len(descriptions)} descriptions")
            except Exception as e:
                logger.error(f"Auto description generation failed: {e}")

        threading.Thread(target=gen, daemon=True).start()

    def _run_transcription(self):
        engine = self._transcribe_engine.get()
        self._mark_step_working("transcribe")
        self._set_status_working(f"Transcribing ({engine})...")
        self._transcribe_btn.configure(state="disabled", text="Transcribing...")
        self._transcribe_progress.set(0)

        def transcribe():
            try:
                try:
                    from processors.chunked_transcriber import transcribe_chunked
                except ImportError:
                    from src.processors.chunked_transcriber import transcribe_chunked

                video_path = self.project["video_path"]

                def ui_progress(pct, msg):
                    self.after(0, lambda p=pct: self._transcribe_progress.set(p / 100))
                    self.after(0, lambda m=msg: self._set_status_working(m))

                if engine == "parakeet":
                    # Parakeet transcribe function for chunks
                    def parakeet_fn(wav_path: str) -> str:
                        import subprocess as sp
                        work_dir = self._get_work_dir()
                        result = sp.run(
                            ["/Library/Frameworks/Python.framework/Versions/3.12/bin/python3",
                             "/tmp/parakeet_transcribe.py", wav_path, str(work_dir)],
                            capture_output=True, text=True, timeout=600,
                        )
                        if result.returncode == 0:
                            srt_files = list(work_dir.glob("*.srt"))
                            if srt_files:
                                text = srt_files[-1].read_text(encoding="utf-8")
                                srt_files[-1].unlink(missing_ok=True)
                                return text
                            return result.stdout
                        raise RuntimeError(f"Parakeet: {result.stderr[:200]}")

                    srt_text = transcribe_chunked(video_path, parakeet_fn, ui_progress)
                    self.project["transcription"] = srt_text

                elif engine == "gemini":
                    # Gemini — cloud, no chunking needed (handles long audio)
                    transcriber = GeminiTranscriber()
                    result = transcriber.transcribe(Path(video_path))
                    self.project["transcription"] = result.get("text", "")

                else:
                    # Whisper — chunked for speed
                    def whisper_fn(wav_path: str) -> str:
                        result = self.whisper.transcribe(wav_path)
                        return result.get("text", "")

                    srt_text = transcribe_chunked(video_path, whisper_fn, ui_progress)
                    self.project["transcription"] = srt_text

                # If intro is set, calculate offset for SRT timestamp shift
                if self.project.get("intro_path"):
                    try:
                        intro_info = self.video_processor.get_video_info(self.project["intro_path"])
                        intro_duration_sec = intro_info.duration
                        self.project["intro_duration"] = intro_duration_sec
                        import logging
                        logging.getLogger(__name__).info(
                            f"Intro duration: {intro_duration_sec:.1f}s — SRT timestamps will need +{intro_duration_sec:.1f}s shift"
                        )
                    except Exception:
                        pass

                self.after(0, lambda: self._transcribe_progress.set(1.0))
                self.after(0, lambda: self._mark_step_done("transcribe"))
                self.after(0, lambda: self._set_status_done("Transcription complete!"))
                self.after(0, self._show_transcribe_panel)
            except Exception as e:
                error_msg = str(e)
                self.after(0, lambda: self._mark_step_error("transcribe"))
                self.after(0, lambda: self._set_status_error("Transcription failed"))
                self.after(0, lambda: self._show_toast(f"Transcription failed: {error_msg}", level="error", duration=0))
                self.after(0, lambda: self._transcribe_btn.configure(state="normal", text="Start Transcription"))

        threading.Thread(target=transcribe, daemon=True).start()

    def _stop_audio(self):
        try:
            from .media_player import stop_playback
        except ImportError:
            from ui.media_player import stop_playback
        stop_playback()

    def _toggle_use_cleaned_audio(self):
        self.project["use_cleaned_audio"] = self._use_cleaned_var.get()
        self._save_project()

    def _run_audio_cleanup(self):
        mode = self._audio_mode.get()
        preset = self._audio_preset.get()
        self._mark_step_working("audio")
        self._set_status_working(f"Cleaning audio ({mode}, {preset})...")
        self._audio_btn.configure(state="disabled", text="Processing...")

        def cleanup():
            try:
                # Always clean the ORIGINAL video audio (not assembled)
                source = self.project.get("original_video_path") or self.project["video_path"]
                output_path = self._get_work_dir() / "audio_cleaned.wav"
                cleanup_processor = AudioCleanup(mode=mode)
                cleanup_processor.cleanup(
                    source, str(output_path),
                    preset=preset,
                )
                self.project["audio_path"] = str(output_path)
                self.after(0, lambda: self._mark_step_done("audio"))
                self.after(0, lambda: self._set_status_done("Audio cleaned!"))
                self.after(0, lambda: self._audio_btn.configure(state="normal", text="Clean Audio"))
                self.after(0, lambda: self._show_toast(f"Audio cleaned! ({mode}, {preset})", level="success"))
                self.after(0, self._show_audio_cleanup_panel)
            except Exception as e:
                error_msg = str(e)
                self.after(0, lambda: self._mark_step_error("audio"))
                self.after(0, lambda: self._set_status_error("Cleanup failed"))
                self.after(0, lambda: self._show_toast(f"Audio cleanup failed: {error_msg}", level="error", duration=0))
                self.after(0, lambda: self._audio_btn.configure(state="normal", text="Clean Audio"))

        threading.Thread(target=cleanup, daemon=True).start()

    def _run_title_generation(self):
        self._mark_step_working("titles")
        self._set_status_working("Generating titles...")
        self._titles_btn.configure(state="disabled", text="Generating...")

        def generate():
            try:
                transcript = self.project.get("transcription") or ""
                if not transcript:
                    transcript = Path(self.project["video_path"]).stem.replace("_", " ").replace("-", " ")
                # Append custom prompt if provided
                custom = self._titles_custom_prompt.get("1.0", "end").strip() if hasattr(self, "_titles_custom_prompt") else ""
                if custom:
                    transcript = f"{transcript}\n\nAdditional context from user: {custom}"
                titles = self.title_generator.generate_titles(
                    transcript=transcript,
                    count=5, style="engaging",
                )
                self.project["titles"] = titles
                # Auto-critique all titles
                self.after(0, lambda: self._set_status_working("Critiquing titles..."))
                critiques = {}
                for t in titles:
                    try:
                        critiques[t] = self.title_generator.critique_title(t, transcript=self.project.get("transcription"))
                    except Exception:
                        pass
                self.project["title_critiques"] = critiques
                self.after(0, lambda: self._set_status_done("Titles generated with critique!"))
                self.after(0, self._show_titles_panel)
            except Exception as e:
                error_msg = str(e)
                self.after(0, lambda: self._mark_step_error("titles"))
                self.after(0, lambda: self._set_status_error("Title generation failed"))
                self.after(0, lambda: self._show_toast(f"Title generation failed: {error_msg}", level="error", duration=0))
                self.after(0, lambda: self._titles_btn.configure(state="normal", text="Generate Titles"))

        threading.Thread(target=generate, daemon=True).start()

    def _select_title(self, title: str):
        self.project["selected_title"] = title
        self._mark_step_done("titles")
        self._set_status_done(f"Selected: {title[:50]}...")
        self._show_titles_panel()

    def _run_title_critique(self):
        self._set_status_working("Critiquing titles...")
        self._critique_btn.configure(state="disabled", text="Critiquing...")

        def critique():
            try:
                critiques = {}
                for title_text in self.project["titles"]:
                    result = self.title_generator.critique_title(
                        title_text,
                        transcript=self.project.get("transcription"),
                    )
                    critiques[title_text] = result
                self.project["title_critiques"] = critiques
                self.after(0, lambda: self._set_status_done("Critique complete!"))
                self.after(0, self._show_titles_panel)
            except Exception as e:
                error_msg = str(e)
                self.after(0, lambda: self._set_status_error("Critique failed"))
                self.after(0, lambda: self._show_toast(f"Critique failed: {error_msg}", level="error", duration=0))
                self.after(0, lambda: self._critique_btn.configure(state="normal", text="Critique All Titles"))

        threading.Thread(target=critique, daemon=True).start()

    def _run_thumbnail_generation(self):
        self._mark_step_working("thumbnail")
        self._set_status_working("Generating thumbnails...")
        self._thumb_btn.configure(state="disabled", text="Generating...")
        self._thumb_progress.set(0)

        def generate():
            try:
                output_dir = self._get_work_dir() / "thumbnails"

                def progress_cb(current, total, msg):
                    pct = current / total if total > 0 else 0
                    self.after(0, lambda p=pct: self._thumb_progress.set(p))
                    self.after(0, lambda m=msg: self._set_status_working(m))

                # Custom prompt from user
                custom_thumb = self._thumb_custom_prompt.get("1.0", "end").strip() if hasattr(self, "_thumb_custom_prompt") else ""
                title_for_gen = self.project.get("selected_title") or Path(self.project["video_path"]).stem
                desc_for_gen = self.project.get("transcription", "")[:500] if self.project.get("transcription") else None
                if custom_thumb:
                    desc_for_gen = f"{desc_for_gen or ''}\n\nUser request: {custom_thumb}"

                paths = self.cover_generator.generate_covers(
                    title=title_for_gen,
                    description=desc_for_gen,
                    count=3,
                    styles=["vibrant", "dark", "cozy"],
                    output_dir=output_dir,
                    reference_image_path=self.project.get("reference_image") or os.getenv("REFERENCE_IMAGE", ""),
                    progress_callback=progress_cb,
                )
                str_paths = [str(p) for p in paths]
                self.project["thumbnail_paths"] = str_paths
                if str_paths:
                    self.project["thumbnail_path"] = str_paths[0]
                self.after(0, lambda: self._thumb_progress.set(1.0))
                self.after(0, lambda: self._set_status_done(f"Generated {len(paths)} thumbnails — choose one!"))
                self.after(0, lambda: self._thumb_btn.configure(state="normal", text="Generate 3 Thumbnails"))
                self.after(0, self._show_thumbnail_panel)
            except Exception as e:
                error_msg = str(e)
                self.after(0, lambda: self._mark_step_error("thumbnail"))
                self.after(0, lambda: self._set_status_error("Thumbnail generation failed"))
                self.after(0, lambda: self._show_toast(f"Thumbnail generation failed: {error_msg}", level="error", duration=0))
                self.after(0, lambda: self._thumb_btn.configure(state="normal", text="Generate 3 Thumbnails"))

        threading.Thread(target=generate, daemon=True).start()

    # ══════════════════════════════════════════
    #  Save Locally
    # ══════════════════════════════════════════

    def _save_locally(self):
        """Export all project files to a user-chosen folder."""
        import shutil
        dest = filedialog.askdirectory(title="Choose export folder", initialdir=str(self._get_work_dir()))
        if not dest:
            return
        dest = Path(dest)
        dest.mkdir(parents=True, exist_ok=True)

        copied = 0
        for key in ["video_path", "audio_path", "thumbnail_path"]:
            src = self.project.get(key)
            if src and Path(src).exists():
                shutil.copy2(src, dest / Path(src).name)
                copied += 1

        # Copy all thumbnails
        for tp in self.project.get("thumbnail_paths", []):
            if tp and Path(tp).exists():
                shutil.copy2(tp, dest / Path(tp).name)
                copied += 1

        # Save metadata as text
        meta_lines = []
        if self.project.get("selected_title"):
            meta_lines.append(f"Title: {self.project['selected_title']}\n")
        if self.project.get("description"):
            meta_lines.append(f"Description:\n{self.project['description']}\n")
        if self.project.get("transcription"):
            meta_lines.append(f"Transcription:\n{self.project['transcription']}\n")
        if meta_lines:
            (dest / "metadata.txt").write_text("\n".join(meta_lines), encoding="utf-8")
            copied += 1

        self._show_toast(f"Exported {copied} files to {dest.name}/", level="success")

    # ══════════════════════════════════════════
    #  Description generation
    # ══════════════════════════════════════════

    def _run_description_generation(self):
        self._set_status_working("Generating descriptions...")
        self._desc_btn.configure(state="disabled", text="Generating...")

        def generate():
            try:
                gen = DescriptionGenerator()
                descriptions = gen.generate_descriptions(
                    transcript=self.project.get("transcription", ""),
                    title=self.project.get("selected_title", ""),
                    count=3,
                )
                # Use first as default, store all
                if descriptions:
                    self.project["description"] = descriptions[0]
                    self.project["descriptions"] = descriptions
                self.after(0, lambda: self._set_status_done(f"Generated {len(descriptions)} descriptions!"))
                self.after(0, lambda: self._desc_btn.configure(state="normal", text="Generate 3 Descriptions"))
                self.after(0, self._show_upload_panel)
            except Exception as e:
                error_msg = str(e)
                self.after(0, lambda: self._set_status_error("Description generation failed"))
                self.after(0, lambda: self._show_toast(f"Description generation failed: {error_msg}", level="error", duration=0))
                self.after(0, lambda: self._desc_btn.configure(state="normal", text="Generate 3 Descriptions"))

        threading.Thread(target=generate, daemon=True).start()

    # ══════════════════════════════════════════
    #  Intro / Outro
    # ══════════════════════════════════════════

    def _pick_intro(self):
        filetypes = [("Video files", "*.mp4 *.mov *.mkv"), ("All files", "*.*")]
        fp = filedialog.askopenfilename(title="Select Intro Video", filetypes=filetypes)
        if fp:
            logger.info(f"Intro selected: {fp}")
            self.project["intro_path"] = fp
            self._save_project()
            self._show_edit_panel()  # Refresh to show updated state

    def _pick_outro(self):
        filetypes = [("Video files", "*.mp4 *.mov *.mkv"), ("All files", "*.*")]
        fp = filedialog.askopenfilename(title="Select Outro Video", filetypes=filetypes)
        if fp:
            logger.info(f"Outro selected: {fp}")
            self.project["outro_path"] = fp
            self._save_project()
            self._show_edit_panel()

    def _set_intro(self, path):
        self.project["intro_path"] = path
        logger.info(f"Intro {'set: ' + str(path) if path else 'cleared'}")
        self._save_project()
        self._show_edit_panel()

    def _set_outro(self, path):
        self.project["outro_path"] = path
        logger.info(f"Outro {'set: ' + str(path) if path else 'cleared'}")
        self._save_project()
        self._show_edit_panel()

    def _clear_subscribe_overlay(self):
        self.project["subscribe_overlay_path"] = None
        logger.info("Subscribe overlay cleared")
        self._save_project()
        self._show_edit_panel()

    def _pick_subscribe_overlay(self):
        filetypes = [("Video files", "*.mp4 *.mov *.mkv"), ("All files", "*.*")]
        fp = filedialog.askopenfilename(title="Select Subscribe Overlay", filetypes=filetypes)
        if fp:
            logger.info(f"Subscribe overlay selected: {fp}")
            self.project["subscribe_overlay_path"] = fp
            self._save_project()
            self._show_edit_panel()

    # ══════════════════════════════════════════
    #  Settings / Help / Projects
    # ══════════════════════════════════════════

    def _open_projects(self):
        try:
            from .project_manager_panel import ProjectManagerPanel
        except ImportError:
            try:
                from ui.project_manager_panel import ProjectManagerPanel
            except ImportError:
                self._show_toast("Project manager not available", level="error")
                return

        try:
            from core.project import ProjectManager
        except ImportError:
            try:
                from ..core.project import ProjectManager
            except ImportError:
                self._show_toast("Project module not available", level="error")
                return

        pm = ProjectManager()

        # Save current project to project manager before opening
        if self.project.get("video_path"):
            try:
                proj_path = self.artifacts.project_dir
                state = dict(self.project)
                state["completed_steps"] = list(self.completed_steps)
                pm.save_project_state(proj_path, state)
            except Exception:
                pass

        current_video = self.project.get("video_path")

        def on_delete_current():
            """Called when user deletes the currently active project."""
            self._reset_project()
            win.destroy()

        win = ProjectManagerPanel(
            self,
            project_manager=pm,
            on_project_open=lambda state: self._switch_project(state, win),
            on_project_create=lambda vp: self._create_and_switch_project(vp, win),
            current_video_path=current_video,
            on_current_deleted=on_delete_current,
        )
        win.transient(self)
        win.grab_set()

        # Show current project info at the top
        if self.project.get("video_path"):
            current_name = Path(self.project["video_path"]).stem
            steps_done = len(self.completed_steps)
            info_text = f"Current project: {current_name} ({steps_done} steps done)"

            info_bar = ctk.CTkFrame(win, fg_color=C["accent_dim"], corner_radius=0, height=36)
            info_bar.pack(fill="x", side="top", before=win.winfo_children()[0])
            info_bar.pack_propagate(False)

            ctk.CTkLabel(
                info_bar, text=info_text,
                font=ctk.CTkFont(size=12), text_color=C["text"],
            ).pack(side="left", padx=16)

            ctk.CTkButton(
                info_bar, text="Save Current", width=100, height=26,
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color=C["green"], hover_color="#00a884",
                text_color=C["text"],
                command=lambda: self._save_current_project_to_manager(pm, win),
            ).pack(side="right", padx=12)

    def _reset_project(self):
        """Clear everything — return to blank state."""
        self.project = {k: ([] if isinstance(v, list) else ({} if isinstance(v, dict) else None))
                        for k, v in self.project.items()}
        self.completed_steps.clear()
        for sid in self._sidebar_badges:
            self._sidebar_badges[sid].configure(text="")
        self._save_project()
        self._show_import_panel()
        self._show_toast(L["project_deleted"], level="info")

    def _save_current_project_to_manager(self, pm, win=None):
        """Save current project state into the project manager."""
        try:
            name = Path(self.project.get("video_path", "untitled")).stem
            state = dict(self.project)
            state["completed_steps"] = list(self.completed_steps)

            # Check if project already exists in manager
            existing = pm.list_projects()
            proj_path = None
            for p in existing:
                if p.get("video_name") == Path(self.project.get("video_path", "")).name:
                    proj_path = Path(p["path"])
                    break

            if proj_path:
                pm.save_project_state(proj_path, state)
            else:
                pm.create_project(name, self.project["video_path"])

            self._show_toast(f"Project '{name}' saved!", level="success")
            # Refresh the list if window is open
            if win and hasattr(win, "_refresh_list"):
                win._refresh_list()
        except Exception as e:
            self._show_toast(f"Save failed: {e}", level="error")

    def _switch_project(self, state: dict, win=None):
        """Switch to an existing project."""
        self.project.update(state)
        self.completed_steps = set(state.get("completed_steps", []))
        video_name = Path(state.get("video_path", "untitled")).stem
        self.artifacts = ArtifactsManager(project_name=video_name)
        self.video_processor.artifacts = self.artifacts
        for step_id in self.completed_steps:
            if step_id in self._sidebar_badges:
                self._sidebar_badges[step_id].configure(text="done", text_color=C["green"])
        if win:
            win.destroy()
        self._show_import_panel()

    def _create_and_switch_project(self, video_path: str, win=None):
        """Create new project from video path."""
        self.project = {k: None for k in self.project}
        self.project.update({"titles": [], "title_critiques": {}, "thumbnail_paths": []})
        self.project["video_path"] = video_path
        self.project["original_video_path"] = video_path
        self.completed_steps = {"import"}
        video_name = Path(video_path).stem
        self.artifacts = ArtifactsManager(project_name=video_name)
        self.video_processor.artifacts = self.artifacts
        self._save_project()
        for sid in self._sidebar_badges:
            self._sidebar_badges[sid].configure(text="")
        self._sidebar_badges["import"].configure(text="done", text_color=C["green"])
        if win:
            win.destroy()
        self._show_import_panel()

    def _open_batch(self):
        try:
            from .batch_panel import BatchPanel
        except ImportError:
            try:
                from ui.batch_panel import BatchPanel
            except ImportError:
                messagebox.showinfo("Batch", "Batch processing not available yet.")
                return

        win = ctk.CTkToplevel(self)
        win.title("Batch Processing")
        win.geometry("800x600")
        win.transient(self)

        panel = BatchPanel(win, on_batch_complete=lambda results: self._set_status_done(f"Batch done: {len(results)} videos"))
        panel.pack(fill="both", expand=True)

    def _open_settings(self):
        win = ctk.CTkToplevel(self)
        win.title("Settings")
        win.geometry("600x600")
        win.transient(self)
        win.grab_set()

        try:
            from .settings_panel import SettingsPanel
        except ImportError:
            from ui.settings_panel import SettingsPanel

        panel = SettingsPanel(win, on_save=self._on_settings_saved)
        panel.pack(fill="both", expand=True, padx=16, pady=16)

    def _on_settings_saved(self, settings: dict):
        """Refresh processors with new API keys and model after settings change."""
        logger.info("Settings saved and applied")
        import os as _os
        gemini_key = settings.get("GOOGLE_GEMINI_API_KEY", "") or settings.get("GEMINI_API_KEY", "")
        if gemini_key:
            _os.environ["GEMINI_API_KEY"] = gemini_key
            _os.environ["GOOGLE_GEMINI_API_KEY"] = gemini_key
            if hasattr(self, "title_generator"):
                self.title_generator.set_api_key(gemini_key)
            if hasattr(self, "cover_generator"):
                self.cover_generator.set_api_key(gemini_key)
        # Apply model selection
        model = settings.get("GEMINI_MODEL", "")
        if model and hasattr(self, "cover_generator"):
            self.cover_generator.set_model(model)
        self._show_toast(L["settings_applied"], level="success")

    def _open_help(self):
        win = ctk.CTkToplevel(self)
        win.title("Help")
        win.geometry("480x380")
        win.transient(self)

        txt = ctk.CTkTextbox(win, font=ctk.CTkFont(size=13), wrap="word")
        txt.pack(fill="both", expand=True, padx=16, pady=16)
        txt.insert("1.0", (
            "Video Studio — Workflow\n\n"
            "01  Import video file\n"
            "02  Edit & trim on the timeline\n"
            "03  Transcribe audio with Whisper\n"
            "04  Clean audio (noise reduction)\n"
            "05  Generate engaging titles with AI\n"
            "06  Create thumbnail with Gemini\n"
            "07  Preview the result\n"
            "08  Upload to YouTube\n\n"
            "See README.md for details."
        ))
        txt.configure(state="disabled")
