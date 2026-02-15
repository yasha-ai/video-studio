"""
Configuration Settings for Video Studio
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные окружения
PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")


class Settings:
    """Глобальные настройки приложения"""
    
    # Пути
    PROJECT_ROOT: Path = PROJECT_ROOT
    OUTPUT_DIR: Path = PROJECT_ROOT / "output"
    TEMP_DIR: Path = OUTPUT_DIR / "temp"
    VIDEOS_DIR: Path = OUTPUT_DIR / "videos"
    AUDIO_DIR: Path = OUTPUT_DIR / "audio"
    TRANSCRIPTS_DIR: Path = OUTPUT_DIR / "transcripts"
    THUMBNAILS_DIR: Path = OUTPUT_DIR / "thumbnails"
    
    # API Keys
    GEMINI_API_KEY: str = os.getenv("GOOGLE_GEMINI_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    AUPHONIC_API_KEY: str = os.getenv("AUPHONIC_API_KEY", "")
    
    # YouTube API
    YOUTUBE_CLIENT_ID: str = os.getenv("YOUTUBE_CLIENT_ID", "")
    YOUTUBE_CLIENT_SECRET: str = os.getenv("YOUTUBE_CLIENT_SECRET", "")
    
    # Whisper Settings
    WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "base")
    WHISPER_DEVICE: str = os.getenv("WHISPER_DEVICE", "cpu")
    
    @classmethod
    def ensure_dirs(cls):
        """Создать необходимые директории"""
        for dir_path in [
            cls.OUTPUT_DIR,
            cls.TEMP_DIR,
            cls.VIDEOS_DIR,
            cls.AUDIO_DIR,
            cls.TRANSCRIPTS_DIR,
            cls.THUMBNAILS_DIR,
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)


# Создаем директории при импорте модуля
Settings.ensure_dirs()
