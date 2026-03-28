"""
Timeline Panel - Non-destructive video editing with undo/redo support.

All operations are recorded in EditHistory and only applied on final Render.
The original video file is never modified.
"""

import customtkinter as ctk
from tkinter import Canvas, messagebox
from pathlib import Path
import subprocess
import threading
from typing import Optional, Callable, Any
import sys

sys.path.append(str(Path(__file__).parent.parent))
from core.artifacts import ArtifactsManager
from core.edit_history import EditHistory

try:
    from .theme import C, L
except ImportError:
    from ui.theme import C, L


class TimelinePanel(ctk.CTkFrame):
    """Non-destructive video editing panel with timeline, undo/redo, and render."""

    def __init__(
        self,
        parent,
        edit_history: Optional[EditHistory] = None,
        on_video_edited: Optional[Callable[[str], None]] = None,
        **kwargs,
    ):
        super().__init__(parent, fg_color=C["bg"], **kwargs)

        self.on_video_edited = on_video_edited
        self.edit_history = edit_history

        # Artifacts for temp files during render
        self.artifacts = ArtifactsManager(project_name="timeline_edit")

        # Video state
        self.video_path: Optional[Path] = None
        self.duration: float = 0.0
        self.start_time: float = 0.0
        self.end_time: float = 0.0

        # Timeline settings
        self.timeline_height = 80
        self.timeline_padding = 40

        self._setup_ui()

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------

    def _setup_ui(self):
        """Build the full UI layout."""

        # --- Header ---
        header = ctk.CTkLabel(
            self,
            text="Edit & Trim",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=C["text"],
        )
        header.pack(pady=(10, 2), padx=20, anchor="w")

        description = ctk.CTkLabel(
            self,
            text="Non-destructive editing. Add operations, then Render.",
            font=ctk.CTkFont(size=12),
            text_color=C["text3"],
        )
        description.pack(pady=(0, 10), padx=20, anchor="w")

        # --- Main container ---
        main_container = ctk.CTkFrame(self, fg_color=C["surface"], corner_radius=12)
        main_container.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        # --- Source info ---
        info_frame = ctk.CTkFrame(main_container, fg_color=C["surface2"], corner_radius=8)
        info_frame.pack(fill="x", padx=10, pady=(10, 5))

        self.info_label = ctk.CTkLabel(
            info_frame,
            text="Source: no video loaded",
            font=ctk.CTkFont(size=13),
            text_color=C["text2"],
        )
        self.info_label.pack(pady=8, padx=10, anchor="w")

        # --- Timeline canvas ---
        timeline_frame = ctk.CTkFrame(main_container, fg_color=C["surface2"], corner_radius=8)
        timeline_frame.pack(fill="both", padx=10, pady=5)

        self.timeline_canvas = Canvas(
            timeline_frame,
            height=self.timeline_height,
            bg=C["surface2"],
            highlightthickness=0,
        )
        self.timeline_canvas.pack(fill="both", expand=True, padx=10, pady=10)

        self.timeline_canvas.bind("<Button-1>", self._on_timeline_click)
        self.timeline_canvas.bind("<B1-Motion>", self._on_timeline_drag)
        self.timeline_canvas.bind("<ButtonRelease-1>", self._on_timeline_release)

        # --- Time controls ---
        controls_frame = ctk.CTkFrame(main_container, fg_color=C["surface2"], corner_radius=8)
        controls_frame.pack(fill="x", padx=10, pady=5)

        # Start time
        start_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        start_frame.pack(side="left", padx=(10, 20), pady=8)

        ctk.CTkLabel(
            start_frame,
            text="Start:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=C["green"],
        ).pack(side="left", padx=(0, 6))

        self.start_entry = ctk.CTkEntry(
            start_frame,
            width=90,
            placeholder_text="00:00:00",
            fg_color=C["surface3"],
            border_color=C["border"],
            text_color=C["text"],
        )
        self.start_entry.pack(side="left")
        self.start_entry.bind("<Return>", lambda e: self._on_time_changed())

        # End time
        end_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        end_frame.pack(side="left", padx=(0, 20), pady=8)

        ctk.CTkLabel(
            end_frame,
            text="End:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=C["red"],
        ).pack(side="left", padx=(0, 6))

        self.end_entry = ctk.CTkEntry(
            end_frame,
            width=90,
            placeholder_text="00:00:00",
            fg_color=C["surface3"],
            border_color=C["border"],
            text_color=C["text"],
        )
        self.end_entry.pack(side="left")
        self.end_entry.bind("<Return>", lambda e: self._on_time_changed())

        # Selected duration
        dur_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        dur_frame.pack(side="left", pady=8)

        ctk.CTkLabel(
            dur_frame,
            text="Selection:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=C["text2"],
        ).pack(side="left", padx=(0, 6))

        self.duration_label = ctk.CTkLabel(
            dur_frame,
            text="00:00:00",
            font=ctk.CTkFont(size=12),
            text_color=C["text"],
        )
        self.duration_label.pack(side="left")

        # --- Action buttons row ---
        actions_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        actions_frame.pack(fill="x", padx=10, pady=5)

        # Add Trim button
        self.trim_button = ctk.CTkButton(
            actions_frame,
            text="Add Trim",
            command=self._add_trim,
            font=ctk.CTkFont(size=13, weight="bold"),
            height=36,
            fg_color=C["accent"],
            hover_color=C["accent_hover"],
            state="disabled",
        )
        self.trim_button.pack(side="left", padx=(10, 6), expand=True, fill="x")

        # Undo button
        self.undo_button = ctk.CTkButton(
            actions_frame,
            text="Undo",
            command=self._undo,
            font=ctk.CTkFont(size=13),
            height=36,
            width=80,
            fg_color=C["surface3"],
            hover_color=C["surface2"],
            text_color=C["text2"],
            state="disabled",
        )
        self.undo_button.pack(side="left", padx=3)

        # Redo button
        self.redo_button = ctk.CTkButton(
            actions_frame,
            text="Redo",
            command=self._redo,
            font=ctk.CTkFont(size=13),
            height=36,
            width=80,
            fg_color=C["surface3"],
            hover_color=C["surface2"],
            text_color=C["text2"],
            state="disabled",
        )
        self.redo_button.pack(side="left", padx=3)

        # Reset button
        self.reset_button = ctk.CTkButton(
            actions_frame,
            text="Reset",
            command=self._reset_selection,
            font=ctk.CTkFont(size=13),
            height=36,
            width=80,
            fg_color=C["surface3"],
            hover_color=C["surface2"],
            text_color=C["text3"],
            state="disabled",
        )
        self.reset_button.pack(side="left", padx=(3, 10))

        # --- Operations list ---
        ops_label = ctk.CTkLabel(
            main_container,
            text="Operations",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=C["text2"],
        )
        ops_label.pack(pady=(8, 2), padx=16, anchor="w")

        ops_list_frame = ctk.CTkFrame(main_container, fg_color=C["surface2"], corner_radius=8)
        ops_list_frame.pack(fill="both", padx=10, pady=(0, 5), expand=True)

        self.ops_scrollable = ctk.CTkScrollableFrame(
            ops_list_frame,
            fg_color=C["surface2"],
            height=100,
        )
        self.ops_scrollable.pack(fill="both", expand=True, padx=4, pady=4)

        self.ops_empty_label = ctk.CTkLabel(
            self.ops_scrollable,
            text="No operations yet. Use the timeline to add a trim.",
            font=ctk.CTkFont(size=12),
            text_color=C["text3"],
        )
        self.ops_empty_label.pack(pady=10)

        # --- Render row ---
        render_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        render_frame.pack(fill="x", padx=10, pady=(5, 10))

        self.render_button = ctk.CTkButton(
            render_frame,
            text="Render",
            command=self._render_video,
            font=ctk.CTkFont(size=14, weight="bold"),
            height=42,
            fg_color=C["green"],
            hover_color="#00a383",
            text_color=C["bg"],
            state="disabled",
        )
        self.render_button.pack(side="left", padx=(10, 6), expand=True, fill="x")

        # Status
        self.status_label = ctk.CTkLabel(
            main_container,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=C["text3"],
        )
        self.status_label.pack(pady=(0, 8))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_video(self, video_path: Path):
        """Load a video for editing. Creates EditHistory if not provided externally."""
        self.video_path = Path(video_path)

        # Refresh artifacts name
        self.artifacts = ArtifactsManager(project_name=f"{self.video_path.stem}_edit")

        # Create or reset edit history if needed
        if self.edit_history is None or self.edit_history.original_video != str(self.video_path):
            self.edit_history = EditHistory(self.video_path)

        # Probe duration
        try:
            result = subprocess.run(
                [
                    "ffprobe", "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    str(video_path),
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            self.duration = float(result.stdout.strip())
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load video:\n{e}")
            return

        self.start_time = 0.0
        self.end_time = self.duration

        self._update_info()
        self._draw_timeline()
        self._update_time_controls()
        self._refresh_operations_list()
        self._refresh_button_states()

    def set_edit_history(self, edit_history: EditHistory):
        """Attach a shared EditHistory instance (e.g. from main_window)."""
        self.edit_history = edit_history
        self._refresh_operations_list()
        self._refresh_button_states()

    # ------------------------------------------------------------------
    # Info / Timeline drawing
    # ------------------------------------------------------------------

    def _update_info(self):
        if not self.video_path:
            self.info_label.configure(text="Source: no video loaded")
            return
        duration_str = self._format_time(self.duration)
        self.info_label.configure(
            text=f"Source: {self.video_path.name}  |  Duration: {duration_str}",
            text_color=C["text"],
        )

    def _draw_timeline(self):
        self.timeline_canvas.delete("all")

        if self.duration == 0:
            return

        width = self.timeline_canvas.winfo_width()
        height = self.timeline_height

        if width <= 1:
            self.after(100, self._draw_timeline)
            return

        pad = self.timeline_padding
        tw = width - 2 * pad  # timeline width in pixels

        # Background bar
        self.timeline_canvas.create_rectangle(
            pad, 10, width - pad, height - 10,
            fill=C["surface"],
            outline=C["border"],
            width=2,
        )

        # Selected region
        start_x = pad + (self.start_time / self.duration) * tw
        end_x = pad + (self.end_time / self.duration) * tw

        self.timeline_canvas.create_rectangle(
            start_x, 10, end_x, height - 10,
            fill="#3b3499",
            stipple="gray50",
            outline=C["accent"],
            width=2,
        )

        # Start marker (green)
        self.timeline_canvas.create_line(
            start_x, 10, start_x, height - 10,
            fill=C["green"], width=3, tags="start_marker",
        )
        self.timeline_canvas.create_oval(
            start_x - 5, height // 2 - 5,
            start_x + 5, height // 2 + 5,
            fill=C["green"], outline="white", width=2, tags="start_marker",
        )

        # End marker (red)
        self.timeline_canvas.create_line(
            end_x, 10, end_x, height - 10,
            fill=C["red"], width=3, tags="end_marker",
        )
        self.timeline_canvas.create_oval(
            end_x - 5, height // 2 - 5,
            end_x + 5, height // 2 + 5,
            fill=C["red"], outline="white", width=2, tags="end_marker",
        )

        # Time labels every 10%
        for i in range(0, 11):
            x = pad + (i / 10) * tw
            t = (i / 10) * self.duration
            self.timeline_canvas.create_line(
                x, height - 10, x, height - 5, fill=C["text3"], width=1,
            )
            self.timeline_canvas.create_text(
                x, height - 3,
                text=self._format_time(t),
                fill=C["text3"],
                font=("Arial", 8),
                anchor="n",
            )

    # ------------------------------------------------------------------
    # Timeline mouse interaction
    # ------------------------------------------------------------------

    def _on_timeline_click(self, event):
        if self.duration == 0:
            return

        width = self.timeline_canvas.winfo_width()
        tw = width - 2 * self.timeline_padding

        click_time = ((event.x - self.timeline_padding) / tw) * self.duration
        click_time = max(0, min(self.duration, click_time))

        start_x = self.timeline_padding + (self.start_time / self.duration) * tw
        end_x = self.timeline_padding + (self.end_time / self.duration) * tw

        if abs(event.x - start_x) < 20:
            self.dragging = "start"
        elif abs(event.x - end_x) < 20:
            self.dragging = "end"
        else:
            self.start_time = click_time
            self.end_time = click_time
            self.dragging = "end"

        self._draw_timeline()
        self._update_time_controls()

    def _on_timeline_drag(self, event):
        if self.duration == 0 or not hasattr(self, "dragging"):
            return

        width = self.timeline_canvas.winfo_width()
        tw = width - 2 * self.timeline_padding

        drag_time = ((event.x - self.timeline_padding) / tw) * self.duration
        drag_time = max(0, min(self.duration, drag_time))

        if self.dragging == "start":
            self.start_time = min(drag_time, self.end_time)
        elif self.dragging == "end":
            self.end_time = max(drag_time, self.start_time)

        self._draw_timeline()
        self._update_time_controls()

    def _on_timeline_release(self, event):
        if hasattr(self, "dragging"):
            del self.dragging

    # ------------------------------------------------------------------
    # Time controls
    # ------------------------------------------------------------------

    def _update_time_controls(self):
        self.start_entry.delete(0, "end")
        self.start_entry.insert(0, self._format_time(self.start_time))

        self.end_entry.delete(0, "end")
        self.end_entry.insert(0, self._format_time(self.end_time))

        selected = self.end_time - self.start_time
        self.duration_label.configure(text=self._format_time(selected))

    def _on_time_changed(self):
        try:
            self.start_time = self._parse_time(self.start_entry.get())
            self.end_time = self._parse_time(self.end_entry.get())

            self.start_time = max(0, min(self.duration, self.start_time))
            self.end_time = max(self.start_time, min(self.duration, self.end_time))

            self._draw_timeline()
            self._update_time_controls()
        except ValueError:
            messagebox.showerror("Error", "Invalid time format. Use HH:MM:SS")

    # ------------------------------------------------------------------
    # Operations
    # ------------------------------------------------------------------

    def _add_trim(self):
        """Add a trim operation to the edit history (non-destructive)."""
        if not self.video_path or not self.edit_history:
            return

        if self.start_time >= self.end_time:
            messagebox.showerror("Error", "Start must be less than end")
            return

        # Don't add a trim that covers the whole video
        if self.start_time == 0.0 and abs(self.end_time - self.duration) < 0.5:
            messagebox.showinfo("Info", "Selection covers the entire video. Nothing to trim.")
            return

        self.edit_history.add({
            "type": "trim",
            "start": self.start_time,
            "end": self.end_time,
        })

        self.status_label.configure(
            text=f"Added: Trim {self._format_time(self.start_time)} -> {self._format_time(self.end_time)}",
            text_color=C["green"],
        )

        self._refresh_operations_list()
        self._refresh_button_states()

    def _undo(self):
        if not self.edit_history:
            return
        op = self.edit_history.undo()
        if op:
            self.status_label.configure(
                text=f"Undone: {self._describe_operation(op)}",
                text_color=C["orange"],
            )
        self._refresh_operations_list()
        self._refresh_button_states()

    def _redo(self):
        if not self.edit_history:
            return
        op = self.edit_history.redo()
        if op:
            self.status_label.configure(
                text=f"Redone: {self._describe_operation(op)}",
                text_color=C["orange"],
            )
        self._refresh_operations_list()
        self._refresh_button_states()

    def _reset_selection(self):
        """Reset timeline markers to full video (does not affect operations)."""
        self.start_time = 0.0
        self.end_time = self.duration
        self._draw_timeline()
        self._update_time_controls()

    # ------------------------------------------------------------------
    # Operations list display
    # ------------------------------------------------------------------

    def _refresh_operations_list(self):
        """Rebuild the scrollable operations list from edit_history."""
        # Clear existing widgets
        for widget in self.ops_scrollable.winfo_children():
            widget.destroy()

        if not self.edit_history:
            return

        operations = self.edit_history.get_operations()

        if not operations:
            self.ops_empty_label = ctk.CTkLabel(
                self.ops_scrollable,
                text="No operations yet. Use the timeline to add a trim.",
                font=ctk.CTkFont(size=12),
                text_color=C["text3"],
            )
            self.ops_empty_label.pack(pady=10)
            return

        for i, op in enumerate(operations):
            row = ctk.CTkFrame(self.ops_scrollable, fg_color=C["surface3"], corner_radius=6, height=30)
            row.pack(fill="x", padx=4, pady=2)

            idx_label = ctk.CTkLabel(
                row,
                text=f"{i + 1}.",
                font=ctk.CTkFont(size=11),
                text_color=C["text3"],
                width=24,
            )
            idx_label.pack(side="left", padx=(8, 4), pady=4)

            desc = self._describe_operation(op)
            desc_label = ctk.CTkLabel(
                row,
                text=desc,
                font=ctk.CTkFont(size=12),
                text_color=C["text"],
                anchor="w",
            )
            desc_label.pack(side="left", fill="x", expand=True, padx=(0, 8), pady=4)

    def _refresh_button_states(self):
        """Enable/disable buttons based on current state."""
        has_video = self.video_path is not None
        has_history = self.edit_history is not None

        # Trim / Reset depend on having a video loaded
        self.trim_button.configure(state="normal" if has_video else "disabled")
        self.reset_button.configure(state="normal" if has_video else "disabled")

        # Undo / Redo depend on history state
        can_undo = has_history and self.edit_history.can_undo
        can_redo = has_history and self.edit_history.can_redo
        self.undo_button.configure(
            state="normal" if can_undo else "disabled",
            text_color=C["text"] if can_undo else C["text3"],
        )
        self.redo_button.configure(
            state="normal" if can_redo else "disabled",
            text_color=C["text"] if can_redo else C["text3"],
        )

        # Render requires at least one operation
        has_ops = has_history and len(self.edit_history.get_operations()) > 0
        self.render_button.configure(state="normal" if (has_video and has_ops) else "disabled")

    # ------------------------------------------------------------------
    # Render (applies all operations via ffmpeg)
    # ------------------------------------------------------------------

    def _render_video(self):
        """Run ffmpeg with all operations from EditHistory."""
        if not self.video_path or not self.edit_history:
            return

        operations = self.edit_history.get_operations()
        if not operations:
            messagebox.showinfo("Info", "No operations to render.")
            return

        # Build output filename
        output_filename = f"{self.video_path.stem}_edited.mp4"
        output_path = self.video_path.parent / output_filename

        # Disable buttons during render
        self.render_button.configure(state="disabled", text="Rendering...")
        self.trim_button.configure(state="disabled")
        self.undo_button.configure(state="disabled")
        self.redo_button.configure(state="disabled")
        self.status_label.configure(text="Rendering...", text_color=C["orange"])

        def render_thread():
            try:
                ffmpeg_args = EditHistory.build_ffmpeg_args(
                    operations=operations,
                    input_path=str(self.video_path),
                    output_path=str(output_path),
                )
                result = subprocess.run(
                    ffmpeg_args,
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    raise RuntimeError(result.stderr[-500:] if result.stderr else "ffmpeg failed")
                self.after(0, lambda: self._render_complete(output_path))
            except Exception as e:
                self.after(0, lambda: self._render_error(str(e)))

        thread = threading.Thread(target=render_thread, daemon=True)
        thread.start()

    def _render_complete(self, output_path: Path):
        self.render_button.configure(text="Render")
        self._refresh_button_states()
        self.status_label.configure(
            text=f"Rendered: {output_path.name}",
            text_color=C["green"],
        )
        messagebox.showinfo("Done", f"Video rendered successfully!\n\nSaved: {output_path.name}")

        if self.on_video_edited:
            self.on_video_edited(str(output_path))

    def _render_error(self, error_msg: str):
        self.render_button.configure(text="Render")
        self._refresh_button_states()
        self.status_label.configure(
            text=f"Render failed: {error_msg[:80]}",
            text_color=C["red"],
        )
        messagebox.showerror("Error", f"Render failed:\n{error_msg}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _format_time(seconds: float) -> str:
        """Format seconds as HH:MM:SS."""
        seconds = max(0, seconds)
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    @staticmethod
    def _parse_time(time_str: str) -> float:
        """Parse HH:MM:SS (or MM:SS or SS) into seconds."""
        parts = time_str.strip().split(":")
        if len(parts) == 3:
            h, m, s = map(int, parts)
            return h * 3600 + m * 60 + s
        elif len(parts) == 2:
            m, s = map(int, parts)
            return m * 60 + s
        elif len(parts) == 1:
            return int(parts[0])
        raise ValueError("Invalid time format")

    @staticmethod
    def _describe_operation(op: dict[str, Any]) -> str:
        """Return a human-readable description of an operation."""
        op_type = op.get("type", "unknown")

        if op_type == "trim":
            start = TimelinePanel._format_time(float(op.get("start", 0)))
            end = TimelinePanel._format_time(float(op.get("end", 0)))
            return f"Trim {start} -> {end}"

        if op_type == "concat_intro":
            name = Path(op.get("path", "?")).name
            return f"Add Intro: {name}"

        if op_type == "concat_outro":
            name = Path(op.get("path", "?")).name
            return f"Add Outro: {name}"

        if op_type == "overlay_subscribe":
            name = Path(op.get("path", "?")).name
            pos = op.get("position", "bottom-right")
            return f"Overlay: {name} ({pos})"

        return f"{op_type}: {op}"
