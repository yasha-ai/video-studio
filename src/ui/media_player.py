"""
Embedded Media Player — plays video/audio using ffplay.
ffplay provides native controls: Space=pause, arrows=seek, Q=quit.
"""

import subprocess
import threading
from pathlib import Path
from typing import Optional

try:
    from config.settings import Settings
except ImportError:
    Settings = None


def _get_ffplay() -> str:
    """Get ffplay binary path."""
    if Settings:
        ffmpeg = Settings.get_ffmpeg()
        ffplay = Path(ffmpeg).parent / "ffplay"
        if ffplay.exists():
            return str(ffplay)
    import shutil
    return shutil.which("ffplay") or "ffplay"


_active_process: Optional[subprocess.Popen] = None


def stop_playback():
    """Stop any active playback."""
    global _active_process
    if _active_process and _active_process.poll() is None:
        try:
            _active_process.terminate()
            _active_process.wait(timeout=2)
        except Exception:
            try:
                _active_process.kill()
            except Exception:
                pass
    _active_process = None


def play_media(parent, file_path: str, title: Optional[str] = None):
    """Play media file using ffplay directly (no wrapper window).

    ffplay native controls:
    - Space: pause/resume
    - Left/Right arrows: seek -10s/+10s
    - Up/Down arrows: seek -60s/+60s
    - Q or Esc: quit
    - F: fullscreen toggle
    - Mouse click on progress bar: seek
    """
    if not Path(file_path).exists():
        return

    # Stop any existing playback (non-blocking)
    threading.Thread(target=stop_playback, daemon=True).start()

    ffplay = _get_ffplay()
    fname = Path(file_path).name
    window_title = title or f"Video Studio — {fname}"

    # Detect audio-only files
    suffix = Path(file_path).suffix.lower()
    is_audio = suffix in (".wav", ".mp3", ".aac", ".flac", ".ogg", ".m4a")

    if is_audio:
        # Audio: no video window, play in background only
        cmd = [
            ffplay,
            "-autoexit",
            "-nodisp",           # No visualization window
            file_path,
        ]
    else:
        cmd = [
            ffplay,
            "-autoexit",
            "-window_title", window_title,
            "-x", "960",
            "-y", "540",
            file_path,
        ]

    def run():
        global _active_process
        try:
            _active_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            _active_process.wait()
        except Exception:
            pass
        _active_process = None

    threading.Thread(target=run, daemon=True).start()
