#!/usr/bin/env python3
"""
Test Imports - Проверка импортов без запуска GUI

Для тестирования на headless-серверах (без X11/GUI)
"""

import sys
from pathlib import Path

# Добавляем корень проекта в PYTHONPATH
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

def test_imports():
    """Тестирование всех импортов"""
    
    print("🧪 Testing imports...")
    
    # Config
    try:
        from config.settings import Settings
        print("✅ config.settings imported successfully")
        print(f"   PROJECT_ROOT: {Settings.PROJECT_ROOT}")
    except Exception as e:
        print(f"❌ config.settings failed: {e}")
        return False
    
    # Utils (пока пустые модули)
    try:
        import src.utils
        print("✅ src.utils imported successfully")
    except Exception as e:
        print(f"❌ src.utils failed: {e}")
        return False
    
    # Core (пока пустые модули)
    try:
        import src.core
        print("✅ src.core imported successfully")
    except Exception as e:
        print(f"❌ src.core failed: {e}")
        return False
    
    # Processors (пока пустые модули)
    try:
        import src.processors
        print("✅ src.processors imported successfully")
    except Exception as e:
        print(f"❌ src.processors failed: {e}")
        return False
    
    # UI (требует Tkinter, пропускаем на headless)
    try:
        import customtkinter
        from src.ui.main_window import MainWindow
        print("✅ src.ui.main_window imported successfully")
    except ModuleNotFoundError as e:
        if "_tkinter" in str(e):
            print("⚠️  src.ui.main_window skipped (Tkinter not available - headless environment)")
        else:
            print(f"❌ src.ui.main_window failed: {e}")
            return False
    except Exception as e:
        print(f"❌ src.ui.main_window failed: {e}")
        return False
    
    print("\n✅ All available imports passed!")
    return True


if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
