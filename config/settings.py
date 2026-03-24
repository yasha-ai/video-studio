"""
Configuration Settings for Video Studio

All paths and keys are configurable via .env file or Settings UI.
No hardcoded absolute paths — app is fully portable.
"""

import os
import shutil
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def _resolve_path(env_key: str, default: str) -> Path:
    """Resolve path from env var. Supports relative (to PROJECT_ROOT) and absolute."""
    raw = os.getenv(env_key, default)
    p = Path(raw)
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    return p


class Settings:
    """Global application settings — all configurable via .env"""

    PROJECT_ROOT: Path = PROJECT_ROOT

    # ── Output directories ──
    OUTPUT_DIR: Path = _resolve_path("OUTPUT_DIR", "output")
    TEMP_DIR: Path = _resolve_path("TEMP_DIR", "output/temp")
    VIDEOS_DIR: Path = _resolve_path("VIDEOS_DIR", "output/videos")
    AUDIO_DIR: Path = _resolve_path("AUDIO_DIR", "output/audio")
    TRANSCRIPTS_DIR: Path = _resolve_path("TRANSCRIPTS_DIR", "output/transcripts")
    THUMBNAILS_DIR: Path = _resolve_path("THUMBNAILS_DIR", "output/thumbnails")
    ARTIFACTS_DIR: Path = _resolve_path("ARTIFACTS_DIR", "output/artifacts")

    # ── External tool paths (empty = search in PATH) ──
    FFMPEG_PATH: str = os.getenv("FFMPEG_PATH", "")
    FFPROBE_PATH: str = os.getenv("FFPROBE_PATH", "")

    # ── API Keys ──
    GEMINI_API_KEY: str = os.getenv("GOOGLE_GEMINI_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    AUPHONIC_API_KEY: str = os.getenv("AUPHONIC_API_KEY", "")

    # ── YouTube API ──
    YOUTUBE_CLIENT_ID: str = os.getenv("YOUTUBE_CLIENT_ID", "")
    YOUTUBE_CLIENT_SECRET: str = os.getenv("YOUTUBE_CLIENT_SECRET", "")

    # ── Whisper Settings ──
    WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "base")
    WHISPER_DEVICE: str = os.getenv("WHISPER_DEVICE", "cpu")

    # ── Gemini model / proxy ──
    GEMINI_MODEL: str = os.getenv("NANO_BANANA_MODEL", "") or os.getenv("GEMINI_MODEL", "")
    GEMINI_BASE_URL: str = os.getenv("GOOGLE_GEMINI_BASE_URL", "")

    @classmethod
    def ensure_dirs(cls):
        """Create output directories if they don't exist."""
        for dir_path in [
            cls.OUTPUT_DIR,
            cls.TEMP_DIR,
            cls.VIDEOS_DIR,
            cls.AUDIO_DIR,
            cls.TRANSCRIPTS_DIR,
            cls.THUMBNAILS_DIR,
            cls.ARTIFACTS_DIR,
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_ffmpeg(cls) -> str:
        """Return ffmpeg binary path — custom or from PATH."""
        if cls.FFMPEG_PATH and Path(cls.FFMPEG_PATH).exists():
            return cls.FFMPEG_PATH
        found = shutil.which("ffmpeg")
        return found or "ffmpeg"

    @classmethod
    def get_ffprobe(cls) -> str:
        """Return ffprobe binary path — custom or from PATH."""
        if cls.FFPROBE_PATH and Path(cls.FFPROBE_PATH).exists():
            return cls.FFPROBE_PATH
        found = shutil.which("ffprobe")
        return found or "ffprobe"

    @classmethod
    def validate(cls) -> list[dict]:
        """Validate environment. Returns list of issues: [{"level": "error"|"warning", "msg": ...}]"""
        issues = []

        # FFmpeg
        if not shutil.which("ffmpeg") and not (cls.FFMPEG_PATH and Path(cls.FFMPEG_PATH).exists()):
            issues.append({
                "level": "error",
                "msg": "FFmpeg not found. Install it or set FFMPEG_PATH in Settings."
            })

        # API keys
        if not cls.GEMINI_API_KEY:
            issues.append({
                "level": "warning",
                "msg": "Gemini API key not set. Titles, thumbnails, and Gemini transcription won't work."
            })

        if not cls.YOUTUBE_CLIENT_ID or not cls.YOUTUBE_CLIENT_SECRET:
            issues.append({
                "level": "warning",
                "msg": "YouTube API credentials not set. Upload feature won't work."
            })

        # Output dir writable
        try:
            cls.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            test_file = cls.OUTPUT_DIR / ".write_test"
            test_file.touch()
            test_file.unlink()
        except Exception:
            issues.append({
                "level": "error",
                "msg": f"Output directory is not writable: {cls.OUTPUT_DIR}"
            })

        return issues


# Create dirs on import
Settings.ensure_dirs()
