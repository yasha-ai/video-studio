#!/usr/bin/env python3
"""
Video Studio - Main Application Entry Point

Локальное десктопное приложение для полного цикла подготовки видео к публикации.
"""

import customtkinter as ctk
from pathlib import Path
import sys
import os

# Добавляем корневую папку проекта в PYTHONPATH
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.ui.main_window import MainWindow


class VideoStudioApp:
    """Главный класс приложения Video Studio"""
    
    def __init__(self):
        # Настройка CustomTkinter темы
        ctk.set_appearance_mode("dark")  # Темная тема по умолчанию
        ctk.set_default_color_theme("dark-blue")  # Неоновые акценты
        
        # Создаем главное окно
        self.root = MainWindow()
        
    def run(self):
        """Запуск приложения"""
        print("🎬 Video Studio запущен...")
        self.root.mainloop()


def main():
    """Точка входа в приложение"""
    try:
        app = VideoStudioApp()
        app.run()
    except KeyboardInterrupt:
        print("\n\n⏹️  Video Studio остановлен.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Ошибка запуска: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
