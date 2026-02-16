"""
Settings Panel — панель настроек приложения
"""

import customtkinter as ctk
from pathlib import Path
from typing import Optional, Callable
import os


class SettingsPanel(ctk.CTkFrame):
    """Панель настроек приложения (API ключи, модели, пути)"""
    
    # Доступные модели Whisper
    WHISPER_MODELS = ["tiny", "base", "small", "medium", "large"]
    
    # Доступные устройства
    WHISPER_DEVICES = ["cpu", "cuda"]
    
    def __init__(
        self, 
        parent,
        on_save: Optional[Callable] = None,
        **kwargs
    ):
        """
        Инициализация панели настроек
        
        Args:
            parent: Родительский виджет
            on_save: Callback при сохранении настроек
        """
        super().__init__(parent, **kwargs)
        
        self.on_save = on_save
        
        # Путь к .env файлу
        self.env_path = Path(__file__).parent.parent.parent / ".env"
        
        # Словари для хранения виджетов
        self.entries = {}
        self.dropdowns = {}
        
        self._setup_ui()
        self._load_settings()
        
    def _setup_ui(self):
        """Создание UI панели"""
        
        # Заголовок панели
        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        title_label = ctk.CTkLabel(
            title_frame,
            text="⚙️ Settings",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        title_label.pack(side="left")
        
        # Разделитель
        separator = ctk.CTkFrame(self, height=2)
        separator.pack(fill="x", padx=10, pady=5)
        
        # Создаем прокручиваемый фрейм для настроек
        scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Секция: API Keys
        self._create_section(scroll_frame, "🔑 API Keys")
        
        self._create_entry_field(
            scroll_frame,
            key="GOOGLE_GEMINI_API_KEY",
            label="Google Gemini API Key",
            show="*"
        )
        
        self._create_entry_field(
            scroll_frame,
            key="OPENAI_API_KEY",
            label="OpenAI API Key",
            show="*"
        )
        
        self._create_entry_field(
            scroll_frame,
            key="AUPHONIC_API_KEY",
            label="Auphonic API Key",
            show="*"
        )
        
        # Секция: YouTube API
        self._create_section(scroll_frame, "📺 YouTube Settings")
        
        self._create_entry_field(
            scroll_frame,
            key="YOUTUBE_CLIENT_ID",
            label="YouTube Client ID",
        )
        
        self._create_entry_field(
            scroll_frame,
            key="YOUTUBE_CLIENT_SECRET",
            label="YouTube Client Secret",
            show="*"
        )
        
        # Секция: Whisper Settings
        self._create_section(scroll_frame, "🎤 Whisper Settings")
        
        self._create_dropdown_field(
            scroll_frame,
            key="WHISPER_MODEL",
            label="Whisper Model",
            values=self.WHISPER_MODELS,
            default="base"
        )
        
        self._create_dropdown_field(
            scroll_frame,
            key="WHISPER_DEVICE",
            label="Whisper Device",
            values=self.WHISPER_DEVICES,
            default="cpu"
        )
        
        # Разделитель перед кнопками
        separator2 = ctk.CTkFrame(self, height=2)
        separator2.pack(fill="x", padx=10, pady=(10, 5))
        
        # Кнопки управления
        buttons_frame = ctk.CTkFrame(self, fg_color="transparent")
        buttons_frame.pack(fill="x", padx=10, pady=10)
        
        save_btn = ctk.CTkButton(
            buttons_frame,
            text="💾 Save Settings",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40,
            command=self._save_settings,
        )
        save_btn.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        reload_btn = ctk.CTkButton(
            buttons_frame,
            text="🔄 Reload",
            font=ctk.CTkFont(size=14),
            height=40,
            fg_color="gray40",
            hover_color="gray30",
            command=self._load_settings,
        )
        reload_btn.pack(side="right", padx=(5, 0))
        
        # Статус сохранения
        self.status_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="gray60",
        )
        self.status_label.pack(pady=5)
        
    def _create_section(self, parent, title: str):
        """Создание заголовка секции"""
        section_frame = ctk.CTkFrame(parent, fg_color="transparent")
        section_frame.pack(fill="x", pady=(15, 5))
        
        section_label = ctk.CTkLabel(
            section_frame,
            text=title,
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        section_label.pack(anchor="w")
        
        # Горизонтальная линия
        line = ctk.CTkFrame(section_frame, height=1, fg_color="gray30")
        line.pack(fill="x", pady=5)
        
    def _create_entry_field(
        self, 
        parent, 
        key: str, 
        label: str,
        show: Optional[str] = None
    ):
        """Создание поля ввода"""
        field_frame = ctk.CTkFrame(parent, fg_color="transparent")
        field_frame.pack(fill="x", pady=5)
        
        label_widget = ctk.CTkLabel(
            field_frame,
            text=label,
            font=ctk.CTkFont(size=12),
            width=200,
            anchor="w"
        )
        label_widget.pack(side="left", padx=(0, 10))
        
        entry = ctk.CTkEntry(
            field_frame,
            placeholder_text=f"Enter {label.lower()}...",
            show=show,
            font=ctk.CTkFont(size=12),
        )
        entry.pack(side="left", fill="x", expand=True)
        
        self.entries[key] = entry
        
    def _create_dropdown_field(
        self,
        parent,
        key: str,
        label: str,
        values: list,
        default: str
    ):
        """Создание выпадающего списка"""
        field_frame = ctk.CTkFrame(parent, fg_color="transparent")
        field_frame.pack(fill="x", pady=5)
        
        label_widget = ctk.CTkLabel(
            field_frame,
            text=label,
            font=ctk.CTkFont(size=12),
            width=200,
            anchor="w"
        )
        label_widget.pack(side="left", padx=(0, 10))
        
        dropdown = ctk.CTkOptionMenu(
            field_frame,
            values=values,
            font=ctk.CTkFont(size=12),
        )
        dropdown.set(default)
        dropdown.pack(side="left", fill="x", expand=True)
        
        self.dropdowns[key] = dropdown
        
    def _load_settings(self):
        """Загрузка настроек из .env файла"""
        if not self.env_path.exists():
            self.status_label.configure(
                text="⚠️ .env file not found",
                text_color="orange"
            )
            return
            
        try:
            # Читаем .env файл
            env_vars = {}
            with open(self.env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
            
            # Заполняем entry поля
            for key, entry in self.entries.items():
                if key in env_vars:
                    entry.delete(0, 'end')
                    entry.insert(0, env_vars[key])
            
            # Заполняем dropdown'ы
            for key, dropdown in self.dropdowns.items():
                if key in env_vars:
                    value = env_vars[key]
                    if value in (self.WHISPER_MODELS if key == "WHISPER_MODEL" else self.WHISPER_DEVICES):
                        dropdown.set(value)
            
            self.status_label.configure(
                text="✓ Settings loaded",
                text_color="green"
            )
            
        except Exception as e:
            self.status_label.configure(
                text=f"✗ Error loading settings: {str(e)}",
                text_color="red"
            )
            
    def _save_settings(self):
        """Сохранение настроек в .env файл"""
        try:
            # Собираем все настройки
            settings = {}
            
            # Из entry полей
            for key, entry in self.entries.items():
                value = entry.get().strip()
                if value:  # Сохраняем только непустые значения
                    settings[key] = value
            
            # Из dropdown'ов
            for key, dropdown in self.dropdowns.items():
                settings[key] = dropdown.get()
            
            # Читаем существующий .env (если есть) для сохранения комментариев
            existing_lines = []
            if self.env_path.exists():
                with open(self.env_path, 'r') as f:
                    existing_lines = f.readlines()
            
            # Обновляем или добавляем новые значения
            updated_lines = []
            updated_keys = set()
            
            for line in existing_lines:
                stripped = line.strip()
                if stripped and not stripped.startswith('#') and '=' in stripped:
                    key = stripped.split('=', 1)[0].strip()
                    if key in settings:
                        updated_lines.append(f"{key}={settings[key]}\n")
                        updated_keys.add(key)
                    else:
                        updated_lines.append(line)
                else:
                    updated_lines.append(line)
            
            # Добавляем новые ключи
            for key, value in settings.items():
                if key not in updated_keys:
                    updated_lines.append(f"{key}={value}\n")
            
            # Записываем обратно
            with open(self.env_path, 'w') as f:
                f.writelines(updated_lines)
            
            # Обновляем переменные окружения
            for key, value in settings.items():
                os.environ[key] = value
            
            self.status_label.configure(
                text="✓ Settings saved successfully",
                text_color="green"
            )
            
            # Вызываем callback если есть
            if self.on_save:
                self.on_save(settings)
                
        except Exception as e:
            self.status_label.configure(
                text=f"✗ Error saving settings: {str(e)}",
                text_color="red"
            )
            
    def get_settings(self) -> dict:
        """Получить текущие настройки из UI"""
        settings = {}
        
        for key, entry in self.entries.items():
            settings[key] = entry.get().strip()
        
        for key, dropdown in self.dropdowns.items():
            settings[key] = dropdown.get()
        
        return settings
