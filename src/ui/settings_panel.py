"""
Settings Panel — панель настроек приложения
"""

import customtkinter as ctk
import tkinter as tk
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

        # Секция: Paths
        self._create_section(scroll_frame, "Paths")

        self._create_entry_field(
            scroll_frame,
            key="OUTPUT_DIR",
            label="Output Directory",
        )

        self._create_entry_field(
            scroll_frame,
            key="FFMPEG_PATH",
            label="FFmpeg Path (optional)",
        )

        self._create_entry_field(
            scroll_frame,
            key="FFPROBE_PATH",
            label="FFprobe Path (optional)",
        )

        # Секция: Gemini Model
        self._create_section(scroll_frame, "Gemini Image Model")

        # Dynamic model dropdown
        model_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        model_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(
            model_frame, text="Image Model",
            font=ctk.CTkFont(size=12), width=200, anchor="w"
        ).pack(side="left", padx=(0, 10))

        self._model_dropdown = ctk.CTkOptionMenu(
            model_frame, values=["(auto-detect)"], width=300,
            font=ctk.CTkFont(size=12),
        )
        self._model_dropdown.pack(side="left", fill="x", expand=True)
        self._refresh_models_btn = ctk.CTkButton(
            model_frame, text="Refresh", width=70, height=28,
            font=ctk.CTkFont(size=11), fg_color="gray40",
            command=self._refresh_image_models,
        )
        self._refresh_models_btn.pack(side="right", padx=(6, 0))
        self.after(500, self._refresh_image_models)

        self._create_entry_field(
            scroll_frame,
            key="GOOGLE_GEMINI_BASE_URL",
            label="Custom Base URL",
        )

        # Секция: Presets
        self._create_section(scroll_frame, "Workflow Presets")

        preset_row = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        preset_row.pack(fill="x", pady=5)

        self._preset_dropdown = ctk.CTkOptionMenu(
            preset_row, values=["(none)"], width=200,
            font=ctk.CTkFont(size=12),
        )
        self._preset_dropdown.pack(side="left", padx=(0, 8))
        self._refresh_presets()

        ctk.CTkButton(
            preset_row, text="Load", width=60, height=28,
            font=ctk.CTkFont(size=11), command=self._load_preset,
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            preset_row, text="Save Current", width=90, height=28,
            font=ctk.CTkFont(size=11), command=self._save_preset,
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            preset_row, text="Delete", width=60, height=28,
            font=ctk.CTkFont(size=11), fg_color="gray40", command=self._delete_preset,
        ).pack(side="left", padx=2)

        # Разделитель перед кнопками
        separator2 = ctk.CTkFrame(self, height=2)
        separator2.pack(fill="x", padx=10, pady=(10, 5))
        
        # Кнопки управления
        buttons_frame = ctk.CTkFrame(self, fg_color="transparent")
        buttons_frame.pack(fill="x", padx=10, pady=10)
        
        save_btn = ctk.CTkButton(
            buttons_frame,
            text="Save & Apply",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40,
            command=self._save_settings,
        )
        save_btn.pack(fill="x")
        
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
        """Создание поля ввода. Использует tk.Entry для надёжного Cmd+V."""
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

        # Native tk.Entry with explicit clipboard bindings
        entry = tk.Entry(
            field_frame,
            font=("Helvetica", 13),
            bg="#242424", fg="#e8e8e8",
            insertbackground="#e8e8e8",
            selectbackground="#6c5ce7", selectforeground="#e8e8e8",
            relief="flat", bd=0,
            highlightthickness=1, highlightcolor="#6c5ce7", highlightbackground="#333333",
        )
        if show:
            entry.configure(show=show)
        entry.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 4))

        # Force clipboard bindings (CustomTkinter can swallow them)
        def _paste(e):
            try:
                txt = entry.clipboard_get()
                try:
                    entry.delete("sel.first", "sel.last")
                except tk.TclError:
                    pass
                entry.insert("insert", txt)
            except tk.TclError:
                pass
            return "break"

        def _copy(e):
            try:
                txt = entry.selection_get()
                entry.clipboard_clear()
                entry.clipboard_append(txt)
            except tk.TclError:
                pass
            return "break"

        def _cut(e):
            _copy(e)
            try:
                entry.delete("sel.first", "sel.last")
            except tk.TclError:
                pass
            return "break"

        def _select_all(e):
            entry.select_range(0, "end")
            entry.icursor("end")
            return "break"

        for mod in ("Command", "Control"):
            for key, fn in [("v", _paste), ("c", _copy), ("x", _cut), ("a", _select_all)]:
                entry.bind(f"<{mod}-{key}>", fn)
                entry.bind(f"<{mod}-{key.upper()}>", fn)

        # Right-click context menu
        def _show_context_menu(e):
            ctx = tk.Menu(entry, tearoff=0, bg="#2e2e2e", fg="#e8e8e8",
                          activebackground="#6c5ce7", activeforeground="#e8e8e8",
                          font=("Helvetica", 12))
            ctx.add_command(label="Cut", command=lambda: _cut(None))
            ctx.add_command(label="Copy", command=lambda: _copy(None))
            ctx.add_command(label="Paste", command=lambda: _paste(None))
            ctx.add_separator()
            ctx.add_command(label="Select All", command=lambda: _select_all(None))
            ctx.tk_popup(e.x_root, e.y_root)

        entry.bind("<Button-2>", _show_context_menu)   # Middle click (Linux)
        entry.bind("<Button-3>", _show_context_menu)   # Right click (Win/Linux)
        entry.bind("<Control-Button-1>", _show_context_menu)  # Ctrl+click (macOS alt)

        # Show/Hide toggle for masked fields
        if show:
            is_hidden = [True]
            def toggle_visibility():
                is_hidden[0] = not is_hidden[0]
                entry.configure(show="*" if is_hidden[0] else "")
                eye_btn.configure(text="Show" if is_hidden[0] else "Hide")

            eye_btn = ctk.CTkButton(
                field_frame, text="Show", width=50, height=28,
                font=ctk.CTkFont(size=11),
                fg_color="gray40", hover_color="gray30",
                command=toggle_visibility,
            )
            eye_btn.pack(side="right", padx=(2, 0))

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
            
            # Из entry полей (include empty values to allow clearing keys)
            for key, entry in self.entries.items():
                settings[key] = entry.get().strip()
            
            # Из dropdown'ов
            for key, dropdown in self.dropdowns.items():
                settings[key] = dropdown.get()

            # Image model
            model_val = self._model_dropdown.get()
            if model_val and model_val != "(auto-detect)":
                settings["GEMINI_MODEL"] = model_val
            else:
                settings["GEMINI_MODEL"] = ""
            
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

    # ── Image Models ──

    def _refresh_image_models(self):
        """Fetch available image models from API."""
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from processors.cover_generator import CoverGenerator
            models = CoverGenerator.list_available_models()
            values = ["(auto-detect)"] + models
            self._model_dropdown.configure(values=values)
            # Restore saved value
            saved = os.getenv("GEMINI_MODEL", "")
            if saved and saved in models:
                self._model_dropdown.set(saved)
            else:
                self._model_dropdown.set("(auto-detect)")
        except Exception:
            self._model_dropdown.configure(values=["(auto-detect)"])

    # ── Presets ──

    def _refresh_presets(self):
        try:
            from core.presets import PresetManager
            pm = PresetManager()
            names = [p.name for p in pm.list_presets()]
            values = names if names else ["(none)"]
            self._preset_dropdown.configure(values=values)
            if names:
                self._preset_dropdown.set(names[0])
            else:
                self._preset_dropdown.set("(none)")
        except Exception:
            self._preset_dropdown.configure(values=["(none)"])

    def _load_preset(self):
        try:
            from core.presets import PresetManager
            name = self._preset_dropdown.get()
            if name == "(none)":
                return
            pm = PresetManager()
            preset = pm.load_preset(name)
            # Apply preset settings to entry fields
            for key, value in preset.settings.items():
                upkey = key.upper()
                if upkey in self.entries and value:
                    self.entries[upkey].delete(0, "end")
                    self.entries[upkey].insert(0, str(value))
            self.status_label.configure(text=f"Preset '{name}' loaded", text_color="green")
        except Exception as e:
            self.status_label.configure(text=f"Error: {e}", text_color="red")

    def _save_preset(self):
        try:
            from core.presets import PresetManager, Preset
            from tkinter import simpledialog
            name = simpledialog.askstring("Save Preset", "Preset name:", parent=self)
            if not name:
                return
            settings = self.get_settings()
            preset = Preset(name=name, description="", settings=settings)
            pm = PresetManager()
            pm.save_preset(preset)
            self._refresh_presets()
            self.status_label.configure(text=f"Preset '{name}' saved", text_color="green")
        except Exception as e:
            self.status_label.configure(text=f"Error: {e}", text_color="red")

    def _delete_preset(self):
        try:
            from core.presets import PresetManager
            name = self._preset_dropdown.get()
            if name == "(none)":
                return
            pm = PresetManager()
            pm.delete_preset(name)
            self._refresh_presets()
            self.status_label.configure(text=f"Preset '{name}' deleted", text_color="green")
        except Exception as e:
            self.status_label.configure(text=f"Error: {e}", text_color="red")
