"""
Preview Panel - Панель предпросмотра видео с встроенным превью кадров
"""

import customtkinter as ctk
from tkinter import messagebox
from pathlib import Path
import subprocess
import platform
import tempfile
import shutil
from typing import Optional, Callable

try:
    from PIL import Image
    from customtkinter import CTkImage

    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False

try:
    from .theme import C, L
except ImportError:
    from ui.theme import C, L

# ---------------------------------------------------------------------------
# Helpers to resolve ffmpeg / ffprobe paths
# ---------------------------------------------------------------------------

def _get_ffmpeg() -> str:
    try:
        from config.settings import Settings
        return Settings.get_ffmpeg()
    except Exception:
        return shutil.which("ffmpeg") or "ffmpeg"


def _get_ffprobe() -> str:
    try:
        from config.settings import Settings
        return Settings.get_ffprobe()
    except Exception:
        return shutil.which("ffprobe") or "ffprobe"


class PreviewPanel(ctk.CTkFrame):
    """Панель предпросмотра видео с встроенным просмотром кадров"""

    # Preview canvas size
    PREVIEW_W = 640
    PREVIEW_H = 360
    PLAYBACK_FPS = 5  # frames per second during playback

    def __init__(
        self,
        parent,
        on_preview_error: Optional[Callable[[str], None]] = None,
        **kwargs,
    ):
        super().__init__(parent, fg_color=C["bg"], **kwargs)

        self.on_preview_error = on_preview_error
        self.video_path: Optional[Path] = None

        # Frame-preview state
        self._frames: list = []          # list[PIL.Image]
        self._frame_count: int = 0
        self._current_idx: int = 0
        self._duration: float = 0.0      # total video duration in seconds
        self._playing: bool = False
        self._after_id: Optional[str] = None
        self._temp_dir: Optional[str] = None

        self._setup_ui()

    # ==================================================================
    # UI construction
    # ==================================================================

    def _setup_ui(self):
        """Создание UI элементов"""

        # --- Header ---
        header = ctk.CTkLabel(
            self,
            text="Preview",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=C["text"],
        )
        header.pack(pady=(10, 2), padx=20, anchor="w")

        description = ctk.CTkLabel(
            self,
            text="Просмотрите видео перед публикацией",
            font=ctk.CTkFont(size=12),
            text_color=C["text3"],
        )
        description.pack(pady=(0, 10), padx=20, anchor="w")

        # --- Main container ---
        main_container = ctk.CTkFrame(self, fg_color=C["surface"], corner_radius=12)
        main_container.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        # --- Frame preview zone ---
        self._preview_zone = ctk.CTkFrame(
            main_container,
            fg_color=C["surface2"],
            corner_radius=10,
            height=self.PREVIEW_H,
        )
        self._preview_zone.pack(fill="x", padx=10, pady=(10, 0))
        self._preview_zone.pack_propagate(False)

        # Label that displays the current frame (or placeholder text)
        self._frame_label = ctk.CTkLabel(
            self._preview_zone,
            text="Preview not available",
            font=ctk.CTkFont(size=16),
            text_color=C["text3"],
            image=None,
        )
        self._frame_label.place(relx=0.5, rely=0.5, anchor="center")

        # Video name overlay (bottom-left of preview zone)
        self.video_name_label = ctk.CTkLabel(
            self._preview_zone,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=C["text2"],
        )
        self.video_name_label.place(relx=0.02, rely=0.96, anchor="sw")

        # --- Scrubber + timestamp row ---
        scrubber_frame = ctk.CTkFrame(main_container, fg_color=C["surface"])
        scrubber_frame.pack(fill="x", padx=10, pady=(4, 0))

        self._time_label_left = ctk.CTkLabel(
            scrubber_frame,
            text="00:00",
            font=ctk.CTkFont(size=11, family="Courier"),
            text_color=C["text2"],
            width=50,
        )
        self._time_label_left.pack(side="left", padx=(10, 4))

        self._scrubber = ctk.CTkSlider(
            scrubber_frame,
            from_=0,
            to=1,
            number_of_steps=1,
            command=self._on_scrub,
            fg_color=C["surface3"],
            progress_color=C["accent"],
            button_color=C["accent"],
            button_hover_color="#7c6ef7",
            height=14,
        )
        self._scrubber.set(0)
        self._scrubber.configure(state="disabled")
        self._scrubber.pack(side="left", fill="x", expand=True, padx=4)

        self._time_label_right = ctk.CTkLabel(
            scrubber_frame,
            text="00:00",
            font=ctk.CTkFont(size=11, family="Courier"),
            text_color=C["text2"],
            width=50,
        )
        self._time_label_right.pack(side="left", padx=(4, 10))

        # --- Playback controls ---
        playback_frame = ctk.CTkFrame(main_container, fg_color=C["surface"])
        playback_frame.pack(fill="x", padx=10, pady=(2, 0))

        self._play_pause_btn = ctk.CTkButton(
            playback_frame,
            text="Play",
            width=80,
            height=32,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=C["accent"],
            hover_color="#7c6ef7",
            command=self._toggle_playback,
            state="disabled",
        )
        self._play_pause_btn.pack(side="left", padx=(10, 6))

        self._step_back_btn = ctk.CTkButton(
            playback_frame,
            text="<",
            width=36,
            height=32,
            font=ctk.CTkFont(size=13),
            fg_color=C["surface3"],
            hover_color=C["border"],
            command=lambda: self._step(-1),
            state="disabled",
        )
        self._step_back_btn.pack(side="left", padx=2)

        self._step_fwd_btn = ctk.CTkButton(
            playback_frame,
            text=">",
            width=36,
            height=32,
            font=ctk.CTkFont(size=13),
            fg_color=C["surface3"],
            hover_color=C["border"],
            command=lambda: self._step(1),
            state="disabled",
        )
        self._step_fwd_btn.pack(side="left", padx=2)

        # --- Action buttons ---
        controls_frame = ctk.CTkFrame(main_container, fg_color=C["surface"])
        controls_frame.pack(fill="x", padx=10, pady=(6, 0))

        self.play_button = ctk.CTkButton(
            controls_frame,
            text="Play Full Video",
            command=self._play_video,
            font=ctk.CTkFont(size=13, weight="bold"),
            height=40,
            fg_color=C["green"],
            hover_color="#00d6a4",
            text_color=C["bg"],
            state="disabled",
        )
        self.play_button.pack(side="left", padx=(10, 5), expand=True, fill="x")

        self.quick_preview_button = ctk.CTkButton(
            controls_frame,
            text="Quick preview (30s)",
            command=self._quick_preview,
            font=ctk.CTkFont(size=13),
            height=40,
            fg_color=C["surface3"],
            hover_color=C["border"],
            text_color=C["text"],
            state="disabled",
        )
        self.quick_preview_button.pack(side="left", padx=5, expand=True, fill="x")

        self.folder_button = ctk.CTkButton(
            controls_frame,
            text="Open Folder",
            command=self._open_folder,
            font=ctk.CTkFont(size=13),
            height=40,
            fg_color=C["surface3"],
            hover_color=C["border"],
            text_color=C["text"],
            state="disabled",
        )
        self.folder_button.pack(side="left", padx=(5, 10), expand=True, fill="x")

        # --- Video info ---
        info_frame = ctk.CTkFrame(main_container, fg_color=C["surface2"], corner_radius=8)
        info_frame.pack(fill="x", padx=10, pady=10)

        self.info_text = ctk.CTkTextbox(
            info_frame,
            height=110,
            font=ctk.CTkFont(size=12),
            fg_color=C["surface2"],
            text_color=C["text2"],
            wrap="word",
        )
        self.info_text.pack(fill="both", expand=True, padx=10, pady=10)
        self.info_text.insert("1.0", "Video info will appear here after loading")
        self.info_text.configure(state="disabled")

    # ==================================================================
    # Public API (backward-compatible)
    # ==================================================================

    def load_video(self, video_path: Path):
        """Загрузить видео для предпросмотра"""
        self.video_path = video_path

        # Stop any running playback
        self._stop_playback()

        # Update name label
        self.video_name_label.configure(text=video_path.name)

        # Enable action buttons
        self.play_button.configure(state="normal")
        self.quick_preview_button.configure(state="normal")
        self.folder_button.configure(state="normal")

        # Fetch metadata (also gets duration)
        self._load_video_info()

        # Try to extract frames for built-in preview
        self._load_frames()

    # ==================================================================
    # Frame extraction & display
    # ==================================================================

    def _extract_frames(self, video_path: Path, count: int = 30) -> "list[Image.Image]":
        """
        Use ffmpeg to extract *count* evenly-spaced frames from *video_path*.
        Returns a list of PIL.Image objects. Raises on failure.
        """
        if not _PIL_AVAILABLE:
            raise RuntimeError("Pillow is not installed")

        # Clean up previous temp dir
        self._cleanup_temp()

        self._temp_dir = tempfile.mkdtemp(prefix="vstudio_frames_")

        ffmpeg = _get_ffmpeg()

        # Duration must be known for evenly-spaced extraction
        duration = self._duration if self._duration > 0 else self._probe_duration(video_path)
        if duration <= 0:
            raise RuntimeError("Cannot determine video duration")

        self._duration = duration

        # Calculate fps to get roughly `count` frames
        fps_value = count / duration
        if fps_value < 0.01:
            fps_value = 0.01

        output_pattern = str(Path(self._temp_dir) / "frame_%05d.jpg")

        cmd = [
            ffmpeg,
            "-i", str(video_path),
            "-vf", f"fps={fps_value},scale={self.PREVIEW_W}:{self.PREVIEW_H}:force_original_aspect_ratio=decrease,pad={self.PREVIEW_W}:{self.PREVIEW_H}:(ow-iw)/2:(oh-ih)/2:color=black",
            "-q:v", "3",
            "-y",
            output_pattern,
        ]

        subprocess.run(cmd, capture_output=True, check=True, timeout=60)

        # Collect frames in order
        frame_dir = Path(self._temp_dir)
        frame_files = sorted(frame_dir.glob("frame_*.jpg"))

        frames: list[Image.Image] = []
        for fp in frame_files:
            img = Image.open(fp)
            img.load()  # force read so file can be deleted later
            frames.append(img)

        return frames

    def _load_frames(self):
        """Extract frames and set up the scrubber. Graceful fallback on failure."""
        try:
            self._frames = self._extract_frames(self.video_path, count=30)
            self._frame_count = len(self._frames)

            if self._frame_count == 0:
                raise RuntimeError("No frames extracted")

            self._current_idx = 0

            # Configure scrubber
            steps = max(self._frame_count - 1, 1)
            self._scrubber.configure(
                number_of_steps=steps,
                state="normal",
            )
            self._scrubber.set(0)

            # Enable playback buttons
            self._play_pause_btn.configure(state="normal")
            self._step_back_btn.configure(state="normal")
            self._step_fwd_btn.configure(state="normal")

            # Show the first frame
            self._show_frame(0)

        except Exception:
            # Fallback: show placeholder
            self._frames = []
            self._frame_count = 0
            self._frame_label.configure(
                image=None,
                text="Preview not available — use Play Full Video",
            )
            self._scrubber.configure(state="disabled")
            self._play_pause_btn.configure(state="disabled")
            self._step_back_btn.configure(state="disabled")
            self._step_fwd_btn.configure(state="disabled")

    def _show_frame(self, idx: int):
        """Display frame at given index on the label."""
        if not self._frames or idx < 0 or idx >= self._frame_count:
            return

        self._current_idx = idx
        pil_img = self._frames[idx]

        ctk_img = CTkImage(light_image=pil_img, dark_image=pil_img, size=(self.PREVIEW_W, self.PREVIEW_H))
        self._frame_label.configure(image=ctk_img, text="")
        # Keep a reference so it's not GC'd
        self._frame_label._ctk_img = ctk_img  # type: ignore[attr-defined]

        # Update timestamp labels
        if self._duration > 0 and self._frame_count > 1:
            t = (idx / (self._frame_count - 1)) * self._duration
        else:
            t = 0.0
        self._time_label_left.configure(text=self._fmt_mmss(t))
        self._time_label_right.configure(text=self._fmt_mmss(self._duration))

        # Keep scrubber in sync (avoid feedback loop via _on_scrub guard)
        if self._frame_count > 1:
            self._scrubber.set(idx / (self._frame_count - 1))

    # ==================================================================
    # Scrubber & playback
    # ==================================================================

    def _on_scrub(self, value: float):
        """Called when user drags the scrubber slider."""
        if self._frame_count == 0:
            return
        idx = round(value * (self._frame_count - 1))
        idx = max(0, min(idx, self._frame_count - 1))
        if idx != self._current_idx:
            self._show_frame(idx)

    def _toggle_playback(self):
        if self._playing:
            self._stop_playback()
        else:
            self._start_playback()

    def _start_playback(self):
        if self._frame_count == 0:
            return
        self._playing = True
        self._play_pause_btn.configure(text="Pause")
        self._advance_frame()

    def _stop_playback(self):
        self._playing = False
        self._play_pause_btn.configure(text="Play")
        if self._after_id is not None:
            self.after_cancel(self._after_id)
            self._after_id = None

    def _advance_frame(self):
        """Show next frame and schedule the following one."""
        if not self._playing:
            return
        next_idx = self._current_idx + 1
        if next_idx >= self._frame_count:
            # Loop back to start
            next_idx = 0
        self._show_frame(next_idx)
        delay_ms = int(1000 / self.PLAYBACK_FPS)
        self._after_id = self.after(delay_ms, self._advance_frame)

    def _step(self, delta: int):
        """Step forward/backward by *delta* frames."""
        if self._frame_count == 0:
            return
        self._stop_playback()
        idx = self._current_idx + delta
        idx = max(0, min(idx, self._frame_count - 1))
        self._show_frame(idx)

    # ==================================================================
    # Video info (metadata)
    # ==================================================================

    def _probe_duration(self, video_path: Path) -> float:
        """Get video duration in seconds via ffprobe."""
        try:
            ffprobe = _get_ffprobe()
            result = subprocess.run(
                [
                    ffprobe,
                    "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    str(video_path),
                ],
                capture_output=True,
                text=True,
                check=True,
                timeout=15,
            )
            return float(result.stdout.strip())
        except Exception:
            return 0.0

    def _load_video_info(self):
        """Загрузить информацию о видео через ffprobe"""
        if not self.video_path:
            return

        try:
            ffprobe = _get_ffprobe()
            result = subprocess.run(
                [
                    ffprobe,
                    "-v", "error",
                    "-show_entries",
                    "format=duration,size,bit_rate:stream=width,height,codec_name,r_frame_rate",
                    "-of", "default=noprint_wrappers=1",
                    str(self.video_path),
                ],
                capture_output=True,
                text=True,
                check=True,
                timeout=15,
            )

            info_lines = result.stdout.strip().split("\n")
            info_dict = {}
            for line in info_lines:
                if "=" in line:
                    key, value = line.split("=", 1)
                    info_dict[key] = value

            self._duration = float(info_dict.get("duration", 0))

            info_text = (
                f"File: {self.video_path.name}\n"
                f"Size: {self._format_size(int(info_dict.get('size', 0)))}\n"
                f"Duration: {self._format_duration(self._duration)}\n"
                f"Resolution: {info_dict.get('width', 'N/A')}x{info_dict.get('height', 'N/A')}\n"
                f"Codec: {info_dict.get('codec_name', 'N/A')}\n"
                f"Bitrate: {self._format_bitrate(int(info_dict.get('bit_rate', 0)))}\n"
                f"FPS: {self._format_fps(info_dict.get('r_frame_rate', 'N/A'))}\n"
                f"Path: {self.video_path.absolute()}"
            )

            self.info_text.configure(state="normal")
            self.info_text.delete("1.0", "end")
            self.info_text.insert("1.0", info_text)
            self.info_text.configure(state="disabled")

        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to get video info:\n{e.stderr}"
            self.info_text.configure(state="normal")
            self.info_text.delete("1.0", "end")
            self.info_text.insert("1.0", error_msg)
            self.info_text.configure(state="disabled")

            if self.on_preview_error:
                self.on_preview_error(error_msg)

        except FileNotFoundError:
            error_msg = "ffprobe not found. Install FFmpeg to view video information."
            self.info_text.configure(state="normal")
            self.info_text.delete("1.0", "end")
            self.info_text.insert("1.0", error_msg)
            self.info_text.configure(state="disabled")

    # ==================================================================
    # External player / folder actions (backward-compatible)
    # ==================================================================

    def _play_video(self):
        """Play video in embedded player (ffplay)."""
        if not self.video_path:
            return
        try:
            from .media_player import play_media
        except ImportError:
            try:
                from ui.media_player import play_media
            except ImportError:
                if self.on_preview_error:
                    self.on_preview_error("Media player not available")
                return
        play_media(self, str(self.video_path))

    def _quick_preview(self):
        """Quick preview (first 30 seconds) in embedded player."""
        if not self.video_path:
            return
        try:
            temp_output = self.video_path.parent / f"{self.video_path.stem}_preview_30s.mp4"
            ffmpeg = _get_ffmpeg()
            subprocess.run(
                [ffmpeg, "-i", str(self.video_path), "-t", "30", "-c", "copy", "-y", str(temp_output)],
                capture_output=True, check=True,
            )
            try:
                from .media_player import play_media
            except ImportError:
                from ui.media_player import play_media
            play_media(self, str(temp_output), title="Quick Preview (30s)")
        except Exception as e:
            if self.on_preview_error:
                self.on_preview_error(f"Preview failed: {e}")

    def _open_folder(self):
        """Открыть папку с видео"""
        if not self.video_path:
            return
        try:
            folder = self.video_path.parent
            system = platform.system()
            if system == "Darwin":
                subprocess.run(["open", str(folder)], check=True)
            elif system == "Windows":
                subprocess.run(["explorer", str(folder)], check=True)
            else:
                subprocess.run(["xdg-open", str(folder)], check=True)
        except Exception as e:
            messagebox.showerror("Error", f"Cannot open folder:\n{e}")
            if self.on_preview_error:
                self.on_preview_error(str(e))

    # ==================================================================
    # Cleanup
    # ==================================================================

    def _cleanup_temp(self):
        """Remove temporary frame directory if it exists."""
        if self._temp_dir and Path(self._temp_dir).exists():
            try:
                shutil.rmtree(self._temp_dir)
            except Exception:
                pass
            self._temp_dir = None

    def destroy(self):
        """Override destroy to clean up temp files and cancel scheduled calls."""
        self._stop_playback()
        self._cleanup_temp()
        super().destroy()

    # ==================================================================
    # Static formatting helpers
    # ==================================================================

    @staticmethod
    def _fmt_mmss(seconds: float) -> str:
        """Format seconds as MM:SS."""
        m = int(seconds) // 60
        s = int(seconds) % 60
        return f"{m:02d}:{s:02d}"

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"

    @staticmethod
    def _format_duration(seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"

    @staticmethod
    def _format_bitrate(bitrate: int) -> str:
        if bitrate == 0:
            return "N/A"
        if bitrate >= 1_000_000:
            return f"{bitrate / 1_000_000:.1f} Mbps"
        return f"{bitrate / 1000:.0f} kbps"

    @staticmethod
    def _format_fps(fps_str: str) -> str:
        if "/" in fps_str:
            try:
                num, den = map(int, fps_str.split("/"))
                return f"{num / den:.2f} fps"
            except Exception:
                return fps_str
        return fps_str
