"""
Main Window - Главное окно приложения Video Studio (Modern UI)
"""

import customtkinter as ctk
from pathlib import Path
from tkinter import filedialog, messagebox
import threading

try:
    from ..core.artifacts import ArtifactsManager
    from ..processors.video_processor import VideoProcessor
    from ..processors.whisper_transcriber import WhisperTranscriber
    from ..processors.audio_cleanup import AudioCleanup
    from ..processors.title_generator import TitleGenerator
    from ..processors.cover_generator import CoverGenerator
    from ..processors.youtube_uploader import YouTubeUploader
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


# --- Color palette ---
C = {
    "bg":           "#0f0f0f",
    "surface":      "#1a1a1a",
    "surface2":     "#242424",
    "surface3":     "#2e2e2e",
    "border":       "#333333",
    "text":         "#e8e8e8",
    "text2":        "#999999",
    "text3":        "#666666",
    "accent":       "#6c5ce7",
    "accent_hover": "#5a4bd1",
    "accent_dim":   "#3d3566",
    "green":        "#00b894",
    "green_dim":    "#1a3d33",
    "red":          "#ff6b6b",
    "orange":       "#fdcb6e",
    "blue":         "#74b9ff",
}


class MainWindow(ctk.CTk):
    """Главное окно приложения"""

    STEPS = [
        {"id": "import",    "icon": "01", "label": "Import",     "method": "_show_import_panel"},
        {"id": "edit",      "icon": "02", "label": "Edit & Trim","method": "_show_edit_panel"},
        {"id": "transcribe","icon": "03", "label": "Transcribe", "method": "_show_transcribe_panel"},
        {"id": "audio",     "icon": "04", "label": "Clean Audio","method": "_show_audio_cleanup_panel"},
        {"id": "titles",    "icon": "05", "label": "Titles",     "method": "_show_titles_panel"},
        {"id": "thumbnail", "icon": "06", "label": "Thumbnail",  "method": "_show_thumbnail_panel"},
        {"id": "preview",   "icon": "07", "label": "Preview",    "method": "_show_preview_panel"},
        {"id": "upload",    "icon": "08", "label": "Upload",     "method": "_show_upload_panel"},
    ]

    def __init__(self):
        super().__init__()

        self.title("Video Studio")
        self.geometry("1440x900")
        self.minsize(1200, 700)
        self.configure(fg_color=C["bg"])

        self._center_window()
        self._init_processors()

        self.project = {
            "video_path": None,
            "audio_path": None,
            "transcription": None,
            "titles": [],
            "selected_title": None,
            "thumbnail_path": None,
        }

        self.completed_steps: set[str] = set()
        self.active_step: str = "import"
        self._sidebar_buttons: dict[str, ctk.CTkButton] = {}
        self._sidebar_badges: dict[str, ctk.CTkLabel] = {}

        self._setup_ui()

    # ══════════════════════════════════════════
    #  Init
    # ══════════════════════════════════════════

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
            logo_frame, text="VIDEO STUDIO",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=C["text"],
        ).pack(anchor="w")

        ctk.CTkLabel(
            logo_frame, text="Professional video pipeline",
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

        settings_btn = ctk.CTkButton(
            bottom, text="Settings",
            font=ctk.CTkFont(size=12),
            fg_color="transparent", text_color=C["text2"],
            hover_color=C["surface3"], height=32, anchor="w",
            command=self._open_settings,
        )
        settings_btn.pack(fill="x", pady=(0, 4))

        help_btn = ctk.CTkButton(
            bottom, text="Help",
            font=ctk.CTkFont(size=12),
            fg_color="transparent", text_color=C["text2"],
            hover_color=C["surface3"], height=32, anchor="w",
            command=self._open_help,
        )
        help_btn.pack(fill="x")

        # Main area wrapper
        main_wrapper = ctk.CTkFrame(self, fg_color=C["bg"], corner_radius=0)
        main_wrapper.pack(fill="both", expand=True, side="left")

        # Top bar
        self.topbar = ctk.CTkFrame(main_wrapper, height=52, fg_color=C["surface"], corner_radius=0)
        self.topbar.pack(fill="x")
        self.topbar.pack_propagate(False)

        self.topbar_title = ctk.CTkLabel(
            self.topbar, text="Import Video",
            font=ctk.CTkFont(size=14, weight="bold"), text_color=C["text"],
        )
        self.topbar_title.pack(side="left", padx=24)

        self.topbar_status = ctk.CTkLabel(
            self.topbar, text="Ready",
            font=ctk.CTkFont(size=12), text_color=C["text3"],
        )
        self.topbar_status.pack(side="right", padx=24)

        # Content area
        self.content_frame = ctk.CTkFrame(main_wrapper, fg_color=C["bg"], corner_radius=0)
        self.content_frame.pack(fill="both", expand=True)

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
        self.active_step = step_id
        self.topbar_title.configure(text=title)
        for sid, btn in self._sidebar_buttons.items():
            if sid == step_id:
                btn.configure(fg_color=C["accent_dim"], text_color=C["text"])
            else:
                btn.configure(fg_color="transparent", text_color=C["text2"])

    def _mark_step_done(self, step_id: str):
        self.completed_steps.add(step_id)
        self._sidebar_badges[step_id].configure(text="done", text_color=C["green"])

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
        self._update_status("Select a video file to start")

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
                inner, text="Video loaded",
                font=ctk.CTkFont(size=28, weight="bold"), text_color=C["green"],
            ).pack(pady=(0, 8))
            ctk.CTkLabel(
                inner, text=name,
                font=ctk.CTkFont(size=14), text_color=C["text2"],
                wraplength=440,
            ).pack(pady=(0, 20))
            self._make_action_btn(inner, "Choose another file", self._import_video, accent=False).pack()
        else:
            ctk.CTkLabel(
                inner, text="Drop or select video",
                font=ctk.CTkFont(size=22, weight="bold"), text_color=C["text"],
            ).pack(pady=(0, 8))
            ctk.CTkLabel(
                inner, text="MP4, MOV, AVI, MKV",
                font=ctk.CTkFont(size=12), text_color=C["text3"],
            ).pack(pady=(0, 28))
            self._make_action_btn(inner, "Select Video File", self._import_video, width=220).pack()

    # ---------- 02 Edit ----------

    def _show_edit_panel(self):
        if not self._require_video():
            return
        self._clear_content()
        self._set_active_step("edit", "Edit & Trim")
        self._update_status("Trim your video on the timeline")

        try:
            from .timeline_panel import TimelinePanel
        except ImportError:
            from ui.timeline_panel import TimelinePanel

        timeline = TimelinePanel(
            self.content_frame,
            on_video_edited=self._on_video_edited,
        )
        timeline.pack(fill="both", expand=True, padx=24, pady=24)
        timeline.load_video(Path(self.project["video_path"]))

    def _on_video_edited(self, output_path: str):
        self.project["video_path"] = output_path
        self._mark_step_done("edit")
        self._set_status_done(f"Trimmed: {Path(output_path).name}")

    # ---------- 03 Transcribe ----------

    def _show_transcribe_panel(self):
        if not self._require_video():
            return
        self._clear_content()
        self._set_active_step("transcribe", "Transcribe Audio")
        self._update_status("Ready to transcribe")

        scroller = ctk.CTkScrollableFrame(self.content_frame, fg_color="transparent")
        scroller.pack(fill="both", expand=True, padx=24, pady=24)

        # Action card
        card = self._make_card(scroller)
        card.pack(fill="x", pady=(0, 16))

        card_inner = ctk.CTkFrame(card, fg_color="transparent")
        card_inner.pack(fill="x", padx=24, pady=20)

        ctk.CTkLabel(
            card_inner, text="Whisper Transcription",
            font=ctk.CTkFont(size=16, weight="bold"), text_color=C["text"],
        ).pack(anchor="w")
        ctk.CTkLabel(
            card_inner, text="Transcribe audio using OpenAI Whisper model locally",
            font=ctk.CTkFont(size=12), text_color=C["text3"],
        ).pack(anchor="w", pady=(4, 16))

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

    # ---------- 04 Clean Audio ----------

    def _show_audio_cleanup_panel(self):
        if not self._require_video():
            return
        self._clear_content()
        self._set_active_step("audio", "Clean Audio")
        self._update_status("Ready")

        wrapper = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        wrapper.pack(expand=True)

        card = self._make_card(wrapper, width=480, height=220)
        card.pack()
        card.pack_propagate(False)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            inner, text="AI Audio Cleanup",
            font=ctk.CTkFont(size=18, weight="bold"), text_color=C["text"],
        ).pack(pady=(0, 4))
        ctk.CTkLabel(
            inner, text="Remove noise and enhance audio quality",
            font=ctk.CTkFont(size=12), text_color=C["text3"],
        ).pack(pady=(0, 20))

        self._audio_btn = self._make_action_btn(inner, "Clean Audio", self._run_audio_cleanup, width=200)
        self._audio_btn.pack()

    # ---------- 05 Titles ----------

    def _show_titles_panel(self):
        if not self.project["transcription"]:
            messagebox.showwarning("No Transcription", "Please transcribe video first!")
            return
        self._clear_content()
        self._set_active_step("titles", "Generate Titles")
        self._update_status("Ready")

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
        ).pack(anchor="w", pady=(4, 16))

        self._titles_btn = self._make_action_btn(card_inner, "Generate Titles", self._run_title_generation, width=200)
        self._titles_btn.pack(anchor="w")

        # Generated titles
        if self.project["titles"]:
            self._make_section_title(scroller, "Choose a title")
            for i, title_text in enumerate(self.project["titles"], 1):
                row = self._make_card(scroller)
                row.pack(fill="x", pady=3)

                btn = ctk.CTkButton(
                    row,
                    text=f"  {i}.  {title_text}",
                    font=ctk.CTkFont(size=13),
                    anchor="w", height=44, corner_radius=10,
                    fg_color="transparent",
                    hover_color=C["accent_dim"],
                    text_color=C["text"],
                    command=lambda t=title_text: self._select_title(t),
                )
                btn.pack(fill="x")

                if self.project["selected_title"] == title_text:
                    btn.configure(fg_color=C["accent_dim"])

    # ---------- 06 Thumbnail ----------

    def _show_thumbnail_panel(self):
        if not self.project["selected_title"]:
            messagebox.showwarning("No Title", "Please generate and select a title first!")
            return
        self._clear_content()
        self._set_active_step("thumbnail", "Create Thumbnail")
        self._update_status("Ready")

        wrapper = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        wrapper.pack(expand=True)

        card = self._make_card(wrapper, width=480, height=240)
        card.pack()
        card.pack_propagate(False)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            inner, text="Thumbnail Generator",
            font=ctk.CTkFont(size=18, weight="bold"), text_color=C["text"],
        ).pack(pady=(0, 4))

        ctk.CTkLabel(
            inner, text=f'Title: "{self.project["selected_title"][:60]}..."',
            font=ctk.CTkFont(size=12), text_color=C["text3"],
            wraplength=400,
        ).pack(pady=(0, 20))

        self._thumb_btn = self._make_action_btn(inner, "Generate with Gemini", self._run_thumbnail_generation, width=220)
        self._thumb_btn.pack()

    # ---------- 07 Preview ----------

    def _show_preview_panel(self):
        self._clear_content()
        self._set_active_step("preview", "Preview")
        self._update_status("Preview your work")

        if not self.project["video_path"]:
            wrapper = ctk.CTkFrame(self.content_frame, fg_color="transparent")
            wrapper.pack(expand=True)
            ctk.CTkLabel(
                wrapper, text="No video loaded yet",
                font=ctk.CTkFont(size=16), text_color=C["text3"],
            ).pack()
            return

        try:
            from .preview_panel import PreviewPanel
        except ImportError:
            from ui.preview_panel import PreviewPanel

        preview = PreviewPanel(self.content_frame, on_preview_error=lambda e: self._set_status_error(e))
        preview.pack(fill="both", expand=True, padx=24, pady=24)
        preview.load_video(Path(self.project["video_path"]))

    # ---------- 08 Upload ----------

    def _show_upload_panel(self):
        if not self._require_video():
            return
        self._clear_content()
        self._set_active_step("upload", "Upload to YouTube")
        self._update_status("Configure and upload")

        try:
            from .youtube_panel import YouTubePanel
        except ImportError:
            from ui.youtube_panel import YouTubePanel

        scroller = ctk.CTkScrollableFrame(self.content_frame, fg_color="transparent")
        scroller.pack(fill="both", expand=True, padx=24, pady=24)

        panel = YouTubePanel(scroller, artifacts_manager=self.artifacts)
        panel.pack(fill="both", expand=True)

        # Pre-fill title if available
        if self.project["selected_title"]:
            panel.title_entry.insert(0, self.project["selected_title"])
        if self.project["transcription"]:
            panel.desc_textbox.insert("1.0", self.project["transcription"][:500])

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
            self.project["video_path"] = filepath
            video_name = Path(filepath).stem
            self.artifacts = ArtifactsManager(project_name=video_name)
            self.video_processor.artifacts = self.artifacts
            self._mark_step_done("import")
            self._set_status_done(f"Loaded: {Path(filepath).name}")
            self._show_import_panel()

    def _run_transcription(self):
        self._set_status_working("Transcribing...")
        self._transcribe_btn.configure(state="disabled", text="Transcribing...")
        self._transcribe_progress.set(0)

        def transcribe():
            try:
                def progress_cb(progress, status):
                    self.after(0, lambda p=progress: self._transcribe_progress.set(p / 100))
                    self.after(0, lambda s=status: self._set_status_working(s))

                self.whisper.progress_callback = progress_cb
                result = self.whisper.transcribe(self.project["video_path"])
                self.project["transcription"] = result["text"]
                self.after(0, lambda: self._transcribe_progress.set(1.0))
                self.after(0, lambda: self._mark_step_done("transcribe"))
                self.after(0, lambda: self._set_status_done("Transcription complete!"))
                self.after(0, self._show_transcribe_panel)
            except Exception as e:
                error_msg = str(e)
                self.after(0, lambda: self._set_status_error("Transcription failed"))
                self.after(0, lambda: messagebox.showerror("Error", f"Transcription failed:\n{error_msg}"))
                self.after(0, lambda: self._transcribe_btn.configure(state="normal", text="Start Transcription"))

        threading.Thread(target=transcribe, daemon=True).start()

    def _run_audio_cleanup(self):
        self._set_status_working("Cleaning audio...")
        self._audio_btn.configure(state="disabled", text="Processing...")

        def cleanup():
            try:
                output_path = Path(self.project["video_path"]).parent / "audio_cleaned.wav"
                self.audio_cleanup.cleanup(self.project["video_path"], str(output_path), preset="medium")
                self.project["audio_path"] = str(output_path)
                self.after(0, lambda: self._mark_step_done("audio"))
                self.after(0, lambda: self._set_status_done("Audio cleaned!"))
                self.after(0, lambda: self._audio_btn.configure(state="normal", text="Clean Audio"))
                self.after(0, lambda: messagebox.showinfo("Done", "Audio cleanup complete!"))
            except Exception as e:
                error_msg = str(e)
                self.after(0, lambda: self._set_status_error("Cleanup failed"))
                self.after(0, lambda: messagebox.showerror("Error", f"Cleanup failed:\n{error_msg}"))
                self.after(0, lambda: self._audio_btn.configure(state="normal", text="Clean Audio"))

        threading.Thread(target=cleanup, daemon=True).start()

    def _run_title_generation(self):
        self._set_status_working("Generating titles...")
        self._titles_btn.configure(state="disabled", text="Generating...")

        def generate():
            try:
                titles = self.title_generator.generate(
                    description=self.project["transcription"][:500],
                    count=8, style="engaging",
                )
                self.project["titles"] = titles
                self.after(0, lambda: self._mark_step_done("titles"))
                self.after(0, lambda: self._set_status_done("Titles generated!"))
                self.after(0, self._show_titles_panel)
            except Exception as e:
                error_msg = str(e)
                self.after(0, lambda: self._set_status_error("Title generation failed"))
                self.after(0, lambda: messagebox.showerror("Error", f"Title generation failed:\n{error_msg}"))
                self.after(0, lambda: self._titles_btn.configure(state="normal", text="Generate Titles"))

        threading.Thread(target=generate, daemon=True).start()

    def _select_title(self, title: str):
        self.project["selected_title"] = title
        self._set_status_done(f"Selected: {title[:50]}...")
        self._show_titles_panel()

    def _run_thumbnail_generation(self):
        self._set_status_working("Generating thumbnail...")
        self._thumb_btn.configure(state="disabled", text="Generating...")

        def generate():
            try:
                output_path = Path(self.project["video_path"]).parent / "thumbnail.jpg"
                self.cover_generator.generate(
                    title=self.project["selected_title"],
                    output_path=str(output_path), style="modern",
                )
                self.project["thumbnail_path"] = str(output_path)
                self.after(0, lambda: self._mark_step_done("thumbnail"))
                self.after(0, lambda: self._set_status_done("Thumbnail generated!"))
                self.after(0, lambda: self._thumb_btn.configure(state="normal", text="Generate with Gemini"))
                self.after(0, lambda: messagebox.showinfo("Done", f"Thumbnail saved:\n{output_path}"))
            except Exception as e:
                error_msg = str(e)
                self.after(0, lambda: self._set_status_error("Thumbnail generation failed"))
                self.after(0, lambda: messagebox.showerror("Error", f"Thumbnail generation failed:\n{error_msg}"))
                self.after(0, lambda: self._thumb_btn.configure(state="normal", text="Generate with Gemini"))

        threading.Thread(target=generate, daemon=True).start()

    # ══════════════════════════════════════════
    #  Settings / Help
    # ══════════════════════════════════════════

    def _open_settings(self):
        win = ctk.CTkToplevel(self)
        win.title("Settings")
        win.geometry("600x500")
        win.transient(self)
        win.grab_set()

        try:
            from .settings_panel import SettingsPanel
        except ImportError:
            from ui.settings_panel import SettingsPanel

        panel = SettingsPanel(win)
        panel.pack(fill="both", expand=True, padx=16, pady=16)

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
