"""
Test для SettingsPanel
"""

import sys
from pathlib import Path

# Добавляем src в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import customtkinter as ctk
from ui.settings_panel import SettingsPanel


def main():
    """Запуск тестового окна с SettingsPanel"""
    
    # Создаем главное окно
    app = ctk.CTk()
    app.title("Settings Panel Test")
    app.geometry("700x800")
    
    # Callback для сохранения
    def on_save(settings: dict):
        print("\n✅ Settings saved:")
        for key, value in settings.items():
            # Маскируем API ключи в выводе
            if "KEY" in key or "SECRET" in key:
                display_value = value[:8] + "..." if len(value) > 8 else "***"
            else:
                display_value = value
            print(f"  {key}: {display_value}")
    
    # Создаем панель настроек
    settings_panel = SettingsPanel(
        app,
        on_save=on_save
    )
    settings_panel.pack(fill="both", expand=True, padx=10, pady=10)
    
    # Запускаем приложение
    app.mainloop()


if __name__ == "__main__":
    main()
