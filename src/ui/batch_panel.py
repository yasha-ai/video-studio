"""
Batch Processing UI Panel

CTkToplevel window for adding multiple videos and processing them
through the pipeline in a background thread.
"""

import threading
from pathlib import Path
from tkinter import filedialog
from typing import Optional, Callable

import customtkinter as ctk

from src.core.batch_processor import BatchProcessor, DEFAULT_STEPS, STEP_LABELS

# ── Color palette ───────────────────────────────────────────────
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
    "orange": "#fdcb6e",
}

STATUS_ICONS = {
    "pending": "\u23f3",   # hourglass
    "running": "\u25b6",   # play
    "done": "\u2714",      # check
    "error": "\u2716",     # cross
    "cancelled": "\u25a0", # stop
}

STATUS_COLORS = {
    "pending": C["text3"],
    "running": C["orange"],
    "done": C["green"],
    "error": C["red"],
    "cancelled": C["text3"],
}

VIDEO_EXTENSIONS = [
    ("Video files", "*.mp4 *.mkv *.avi *.mov *.webm *.flv *.wmv"),
    ("All files", "*.*"),
]


class BatchPanel(ctk.CTkToplevel):
    """
    Batch processing window.

    Args:
        master: Parent widget.
        on_batch_complete: Optional callback receiving the results list
            when the batch finishes.
    """

    def __init__(
        self,
        master,
        on_batch_complete: Optional[Callable[[list], None]] = None,
        **kwargs,
    ):
        super().__init__(master, **kwargs)

        self.title("Batch Processing")
        self.geometry("720x680")
        self.configure(fg_color=C["bg"])
        self.resizable(True, True)
        self.minsize(600, 500)

        self._on_batch_complete = on_batch_complete
        self._processor: Optional[BatchProcessor] = None
        self._thread: Optional[threading.Thread] = None
        self._video_paths: list[str] = []
        self._is_running = False

        self._build_ui()

    # ── UI construction ─────────────────────────────────────────

    def _build_ui(self):
        # ---------- Top: add videos ----------
        top_frame = ctk.CTkFrame(self, fg_color=C["surface"], corner_radius=10)
        top_frame.pack(fill="x", padx=16, pady=(16, 8))

        header = ctk.CTkLabel(
            top_frame, text="Batch Processing", font=("", 18, "bold"),
            text_color=C["text"],
        )
        header.pack(anchor="w", padx=16, pady=(12, 4))

        btn_row = ctk.CTkFrame(top_frame, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(0, 12))

        self._add_btn = ctk.CTkButton(
            btn_row, text="+ Add Videos", width=140,
            fg_color=C["accent"], hover_color=C["accent_hover"],
            text_color=C["text"], command=self._on_add_videos,
        )
        self._add_btn.pack(side="left")

        self._clear_btn = ctk.CTkButton(
            btn_row, text="Clear List", width=100,
            fg_color=C["surface3"], hover_color=C["surface2"],
            text_color=C["text2"], command=self._on_clear_list,
        )
        self._clear_btn.pack(side="left", padx=(8, 0))

        drop_label = ctk.CTkLabel(
            btn_row,
            text="Select video files to add to the batch queue",
            text_color=C["text3"], font=("", 12),
        )
        drop_label.pack(side="left", padx=(16, 0))

        # ---------- Video list ----------
        list_frame = ctk.CTkFrame(self, fg_color=C["surface"], corner_radius=10)
        list_frame.pack(fill="both", expand=True, padx=16, pady=4)

        list_header = ctk.CTkLabel(
            list_frame, text="Videos (0)", font=("", 13, "bold"),
            text_color=C["text2"],
        )
        list_header.pack(anchor="w", padx=16, pady=(10, 4))
        self._list_header = list_header

        self._scroll_frame = ctk.CTkScrollableFrame(
            list_frame, fg_color=C["surface2"], corner_radius=6,
        )
        self._scroll_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self._video_rows: list[ctk.CTkFrame] = []
        self._status_labels: list[ctk.CTkLabel] = []
        self._icon_labels: list[ctk.CTkLabel] = []

        # ---------- Step checkboxes ----------
        steps_frame = ctk.CTkFrame(self, fg_color=C["surface"], corner_radius=10)
        steps_frame.pack(fill="x", padx=16, pady=4)

        steps_label = ctk.CTkLabel(
            steps_frame, text="Steps", font=("", 13, "bold"),
            text_color=C["text2"],
        )
        steps_label.pack(anchor="w", padx=16, pady=(10, 4))

        checks_row = ctk.CTkFrame(steps_frame, fg_color="transparent")
        checks_row.pack(fill="x", padx=16, pady=(0, 12))

        self._step_vars: dict[str, ctk.BooleanVar] = {}
        for step in DEFAULT_STEPS:
            var = ctk.BooleanVar(value=True)
            self._step_vars[step] = var
            cb = ctk.CTkCheckBox(
                checks_row,
                text=STEP_LABELS[step],
                variable=var,
                fg_color=C["accent"],
                hover_color=C["accent_hover"],
                border_color=C["border"],
                text_color=C["text"],
                font=("", 12),
            )
            cb.pack(side="left", padx=(0, 16))

        # ---------- Progress section ----------
        prog_frame = ctk.CTkFrame(self, fg_color=C["surface"], corner_radius=10)
        prog_frame.pack(fill="x", padx=16, pady=4)

        self._progress_label = ctk.CTkLabel(
            prog_frame, text="Ready", font=("", 12),
            text_color=C["text2"],
        )
        self._progress_label.pack(anchor="w", padx=16, pady=(10, 4))

        self._progress_bar = ctk.CTkProgressBar(
            prog_frame, progress_color=C["accent"], fg_color=C["surface3"],
            height=8,
        )
        self._progress_bar.pack(fill="x", padx=16, pady=(0, 12))
        self._progress_bar.set(0)

        # ---------- Action buttons ----------
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=16, pady=(8, 16))

        self._start_btn = ctk.CTkButton(
            btn_frame, text="Start Batch", width=160, height=38,
            fg_color=C["green"], hover_color="#00a884",
            text_color="#000000", font=("", 14, "bold"),
            command=self._on_start,
        )
        self._start_btn.pack(side="left")

        self._cancel_btn = ctk.CTkButton(
            btn_frame, text="Cancel", width=120, height=38,
            fg_color=C["red"], hover_color="#e05555",
            text_color=C["text"], font=("", 14),
            command=self._on_cancel, state="disabled",
        )
        self._cancel_btn.pack(side="left", padx=(8, 0))

        self._results_label = ctk.CTkLabel(
            btn_frame, text="", font=("", 12),
            text_color=C["text2"],
        )
        self._results_label.pack(side="right", padx=(8, 0))

    # ── Actions ─────────────────────────────────────────────────

    def _on_add_videos(self):
        if self._is_running:
            return
        paths = filedialog.askopenfilenames(
            title="Select video files",
            filetypes=VIDEO_EXTENSIONS,
        )
        if not paths:
            return
        for p in paths:
            if p not in self._video_paths:
                self._video_paths.append(p)
                self._add_video_row(p)
        self._list_header.configure(text=f"Videos ({len(self._video_paths)})")

    def _on_clear_list(self):
        if self._is_running:
            return
        self._video_paths.clear()
        for row in self._video_rows:
            row.destroy()
        self._video_rows.clear()
        self._status_labels.clear()
        self._icon_labels.clear()
        self._list_header.configure(text="Videos (0)")
        self._results_label.configure(text="")
        self._progress_bar.set(0)
        self._progress_label.configure(text="Ready")

    def _on_start(self):
        if self._is_running or not self._video_paths:
            return

        selected_steps = [s for s, var in self._step_vars.items() if var.get()]
        if not selected_steps:
            return

        self._is_running = True
        self._start_btn.configure(state="disabled")
        self._cancel_btn.configure(state="normal")
        self._add_btn.configure(state="disabled")
        self._clear_btn.configure(state="disabled")
        self._results_label.configure(text="")

        # Reset statuses
        for i in range(len(self._video_paths)):
            self._update_row_status(i, "pending", "Pending")

        self._processor = BatchProcessor()
        for vp in self._video_paths:
            self._processor.add_video(vp, steps=selected_steps)

        self._thread = threading.Thread(
            target=self._run_batch, daemon=True,
        )
        self._thread.start()

    def _on_cancel(self):
        if self._processor:
            self._processor.cancel()
        self._progress_label.configure(text="Cancelling...")

    # ── Background work ─────────────────────────────────────────

    def _run_batch(self):
        try:
            self._processor.run(progress_callback=self._progress_callback)
        finally:
            self.after(0, self._on_finished)

    def _progress_callback(self, video_idx, total, video_name, step_name, status):
        """Called from background thread — schedule UI update on main thread."""
        self.after(0, self._handle_progress, video_idx, total, video_name, step_name, status)

    def _handle_progress(self, video_idx, total, video_name, step_name, status):
        # Update overall progress
        fraction = video_idx / total if total > 0 else 0
        if status == "done":
            # Advance fractionally within current video
            pass
        self._progress_bar.set(fraction)
        self._progress_label.configure(
            text=f"[{video_idx + 1}/{total}] {video_name} — {step_name}: {status}"
        )

        # Update per-video row
        if 0 <= video_idx < len(self._video_paths):
            if status == "running":
                self._update_row_status(video_idx, "running", step_name)
            elif status == "done":
                self._update_row_status(video_idx, "running", f"{step_name} done")
            elif status.startswith("error"):
                self._update_row_status(video_idx, "error", status)

    def _on_finished(self):
        self._is_running = False
        self._start_btn.configure(state="normal")
        self._cancel_btn.configure(state="disabled")
        self._add_btn.configure(state="normal")
        self._clear_btn.configure(state="normal")
        self._progress_bar.set(1.0)

        results = self._processor.get_results() if self._processor else []

        # Update row statuses from final results
        for i, res in enumerate(results):
            if i < len(self._video_paths):
                final_status = res["status"]
                detail = ", ".join(res["completed_steps"]) if res["completed_steps"] else "none"
                if res["error"]:
                    detail = res["error"][:60]
                self._update_row_status(i, final_status, detail)

        # Summary
        done_count = sum(1 for r in results if r["status"] == "done")
        err_count = sum(1 for r in results if r["status"] == "error")
        cancel_count = sum(1 for r in results if r["status"] == "cancelled")
        summary_parts = [f"{done_count} done"]
        if err_count:
            summary_parts.append(f"{err_count} errors")
        if cancel_count:
            summary_parts.append(f"{cancel_count} cancelled")
        summary = "Batch complete: " + ", ".join(summary_parts)
        self._progress_label.configure(text=summary)
        self._results_label.configure(text=summary)

        if self._on_batch_complete:
            self._on_batch_complete(results)

    # ── Video list helpers ──────────────────────────────────────

    def _add_video_row(self, video_path: str):
        idx = len(self._video_rows)
        name = Path(video_path).name

        row = ctk.CTkFrame(self._scroll_frame, fg_color=C["surface3"], corner_radius=6, height=36)
        row.pack(fill="x", pady=(0, 4))
        row.pack_propagate(False)

        icon_lbl = ctk.CTkLabel(
            row, text=STATUS_ICONS["pending"], width=24,
            text_color=STATUS_COLORS["pending"], font=("", 14),
        )
        icon_lbl.pack(side="left", padx=(10, 4), pady=6)

        name_lbl = ctk.CTkLabel(
            row, text=name, text_color=C["text"], font=("", 12),
            anchor="w",
        )
        name_lbl.pack(side="left", fill="x", expand=True, pady=6)

        status_lbl = ctk.CTkLabel(
            row, text="Pending", text_color=C["text3"], font=("", 11),
            anchor="e",
        )
        status_lbl.pack(side="right", padx=(4, 12), pady=6)

        # Remove button
        if not self._is_running:
            rm_btn = ctk.CTkButton(
                row, text="x", width=24, height=24,
                fg_color="transparent", hover_color=C["surface2"],
                text_color=C["text3"], font=("", 11),
                command=lambda i=idx: self._remove_video(i),
            )
            rm_btn.pack(side="right", padx=(0, 4), pady=6)

        self._video_rows.append(row)
        self._icon_labels.append(icon_lbl)
        self._status_labels.append(status_lbl)

    def _remove_video(self, idx: int):
        if self._is_running or idx >= len(self._video_paths):
            return
        self._video_paths.pop(idx)
        row = self._video_rows.pop(idx)
        self._icon_labels.pop(idx)
        self._status_labels.pop(idx)
        row.destroy()
        self._list_header.configure(text=f"Videos ({len(self._video_paths)})")

    def _update_row_status(self, idx: int, status: str, detail: str = ""):
        if idx >= len(self._icon_labels):
            return
        icon = STATUS_ICONS.get(status, "?")
        color = STATUS_COLORS.get(status, C["text3"])
        self._icon_labels[idx].configure(text=icon, text_color=color)
        self._status_labels[idx].configure(text=detail or status, text_color=color)
