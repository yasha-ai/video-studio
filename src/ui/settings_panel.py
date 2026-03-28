"""
Settings Panel — панель настроек приложения (tabbed layout)
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
from pathlib import Path
from typing import Optional, Callable
import os
import json

try:
    from .theme import C, L
except ImportError:
    from ui.theme import C, L


class SettingsPanel(ctk.CTkFrame):
    """Панель настроек приложения (API ключи, модели, пути) — tabbed UI"""

    # Доступные модели Whisper
    WHISPER_MODELS = ["tiny", "base", "small", "medium", "large"]

    # Доступные устройства
    WHISPER_DEVICES = ["cpu", "cuda"]

    # Доступные движки транскрипции
    TRANSCRIPTION_ENGINES = ["whisper", "parakeet", "gemini"]

    def __init__(
        self,
        parent,
        on_save: Optional[Callable] = None,
        **kwargs
    ):
        super().__init__(parent, fg_color=C["bg"], **kwargs)

        self.on_save = on_save

        # Путь к .env файлу
        self.env_path = Path(__file__).parent.parent.parent / ".env"

        # Словари для хранения виджетов
        self.entries = {}
        self.dropdowns = {}

        # Dynamic list widgets
        self._social_link_rows = []  # list of dicts: {frame, name_entry, url_entry}
        self._reference_image_rows = []  # list of dicts: {frame, path, label}

        self._setup_ui()
        self._load_settings()

    # ── UI Setup ─────────────────────────────────────────────────────

    def _setup_ui(self):
        """Создание UI панели с вкладками"""

        # Заголовок панели
        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkLabel(
            title_frame,
            text="Настройки",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=C["text"],
        ).pack(side="left")

        # Разделитель
        ctk.CTkFrame(self, height=2, fg_color=C["border"]).pack(fill="x", padx=10, pady=5)

        # ── Tabview ──
        self.tabview = ctk.CTkTabview(
            self,
            fg_color=C["surface"],
            segmented_button_fg_color=C["surface2"],
            segmented_button_selected_color=C["accent"],
            segmented_button_selected_hover_color="#7d6ef0",
            segmented_button_unselected_color=C["surface2"],
            segmented_button_unselected_hover_color=C["surface3"],
            text_color=C["text"],
            border_color=C["border"],
            border_width=1,
        )
        self.tabview.pack(fill="both", expand=True, padx=10, pady=5)

        # Create tabs
        tab_api = self.tabview.add("API Ключи")
        tab_models = self.tabview.add("Модели")
        tab_paths = self.tabview.add("Пути")
        tab_assets = self.tabview.add("Ассеты")
        tab_presets = self.tabview.add("Пресеты")

        # Populate each tab
        self._build_api_keys_tab(tab_api)
        self._build_models_tab(tab_models)
        self._build_paths_tab(tab_paths)
        self._build_assets_tab(tab_assets)
        self._build_presets_tab(tab_presets)

        # ── Bottom bar (outside tabs) ──
        ctk.CTkFrame(self, height=2, fg_color=C["border"]).pack(fill="x", padx=10, pady=(10, 5))

        buttons_frame = ctk.CTkFrame(self, fg_color="transparent")
        buttons_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkButton(
            buttons_frame,
            text="Сохранить и применить",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40,
            fg_color=C["accent"],
            hover_color="#7d6ef0",
            command=self._save_settings,
        ).pack(fill="x")

        # Статус сохранения
        self.status_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=C["text3"],
        )
        self.status_label.pack(pady=5)

    # ── Tab builders ─────────────────────────────────────────────────

    def _build_api_keys_tab(self, tab):
        """Tab 1 — API Ключи"""
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=5, pady=5)

        self._create_section(scroll, "Google Gemini")
        self._create_entry_field(scroll, key="GOOGLE_GEMINI_API_KEY", label="Ключ Google Gemini API", show="*")

        self._create_section(scroll, "OpenAI")
        self._create_entry_field(scroll, key="OPENAI_API_KEY", label="Ключ OpenAI API", show="*")

        self._create_section(scroll, "Auphonic")
        self._create_entry_field(scroll, key="AUPHONIC_API_KEY", label="Ключ Auphonic API", show="*")

        self._create_section(scroll, "YouTube")
        self._create_entry_field(scroll, key="YOUTUBE_CLIENT_ID", label="YouTube Client ID")
        self._create_entry_field(scroll, key="YOUTUBE_CLIENT_SECRET", label="YouTube Client Secret", show="*")

    def _build_models_tab(self, tab):
        """Tab 2 — Модели"""
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=5, pady=5)

        self._create_section(scroll, "Транскрипция")
        self._create_dropdown_field(scroll, key="TRANSCRIPTION_ENGINE", label="Движок транскрипции",
                                    values=self.TRANSCRIPTION_ENGINES, default="whisper")

        self._create_section(scroll, "Whisper")
        self._create_dropdown_field(scroll, key="WHISPER_MODEL", label="Модель Whisper",
                                    values=self.WHISPER_MODELS, default="base")
        self._create_dropdown_field(scroll, key="WHISPER_DEVICE", label="Устройство Whisper",
                                    values=self.WHISPER_DEVICES, default="cpu")

        self._create_section(scroll, "Модель изображений Gemini")

        # Dynamic model dropdown
        model_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        model_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(
            model_frame, text="Модель изображений",
            font=ctk.CTkFont(size=12), text_color=C["text"],
            width=200, anchor="w",
        ).pack(side="left", padx=(0, 10))

        self._model_dropdown = ctk.CTkOptionMenu(
            model_frame, values=["(auto-detect)"], width=300,
            font=ctk.CTkFont(size=12),
            fg_color=C["surface2"], button_color=C["surface3"],
            button_hover_color=C["accent"],
        )
        self._model_dropdown.pack(side="left", fill="x", expand=True)

        self._refresh_models_btn = ctk.CTkButton(
            model_frame, text="Обновить", width=80, height=28,
            font=ctk.CTkFont(size=11), fg_color=C["surface3"],
            hover_color=C["accent"],
            command=self._refresh_image_models,
        )
        self._refresh_models_btn.pack(side="right", padx=(6, 0))
        self.after(500, self._refresh_image_models)

        self._create_section(scroll, "API Endpoint")
        self._create_entry_field(scroll, key="GOOGLE_GEMINI_BASE_URL", label="Пользовательский URL")

    def _build_paths_tab(self, tab):
        """Tab 3 — Пути"""
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=5, pady=5)

        self._create_section(scroll, "Вывод")
        self._create_entry_field(scroll, key="OUTPUT_DIR", label="Папка вывода")

        self._create_section(scroll, "Внешние инструменты")
        self._create_entry_field(scroll, key="FFMPEG_PATH", label="Путь к FFmpeg")
        self._create_entry_field(scroll, key="FFPROBE_PATH", label="Путь к FFprobe")

    def _build_assets_tab(self, tab):
        """Tab 4 — Ассеты (референсные изображения, фоны, соцсети)"""
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=5, pady=5)

        # ── Reference Images (dynamic list) ──
        self._create_section(scroll, "Референсные изображения")

        self._ref_images_container = ctk.CTkFrame(scroll, fg_color="transparent")
        self._ref_images_container.pack(fill="x", pady=(0, 5))

        ctk.CTkButton(
            scroll, text="+  Добавить изображение", width=180, height=28,
            font=ctk.CTkFont(size=11),
            fg_color=C["surface3"], hover_color=C["accent"],
            command=self._add_reference_image_row,
        ).pack(anchor="w", pady=(0, 10))

        # ── Custom Background (single picker, kept) ──
        self._create_section(scroll, "Фон")
        self._create_file_picker_field(
            scroll,
            key="CUSTOM_BACKGROUND",
            label="Пользовательский фон",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.webp"), ("All", "*.*")],
        )

        # ── Social Links (dynamic list) ──
        self._create_section(scroll, "Социальные сети")

        self._social_links_container = ctk.CTkFrame(scroll, fg_color="transparent")
        self._social_links_container.pack(fill="x", pady=(0, 5))

        ctk.CTkButton(
            scroll, text="+  Добавить ссылку", width=160, height=28,
            font=ctk.CTkFont(size=11),
            fg_color=C["surface3"], hover_color=C["accent"],
            command=self._add_social_link_row,
        ).pack(anchor="w", pady=(0, 5))

        ctk.CTkLabel(
            scroll,
            text="Ссылки на соцсети для описаний видео.",
            font=ctk.CTkFont(size=11),
            text_color=C["text3"],
            anchor="w",
        ).pack(fill="x", padx=5, pady=(0, 5))

    def _build_presets_tab(self, tab):
        """Tab 5 — Пресеты"""
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=5, pady=5)

        self._create_section(scroll, "Пресеты рабочего процесса")

        preset_row = ctk.CTkFrame(scroll, fg_color="transparent")
        preset_row.pack(fill="x", pady=5)

        self._preset_dropdown = ctk.CTkOptionMenu(
            preset_row, values=["(нет)"], width=200,
            font=ctk.CTkFont(size=12),
            fg_color=C["surface2"], button_color=C["surface3"],
            button_hover_color=C["accent"],
        )
        self._preset_dropdown.pack(side="left", padx=(0, 8))
        self._refresh_presets()

        ctk.CTkButton(
            preset_row, text="Загрузить", width=70, height=28,
            font=ctk.CTkFont(size=11),
            fg_color=C["accent"], hover_color="#7d6ef0",
            command=self._load_preset,
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            preset_row, text="Сохранить текущий", width=120, height=28,
            font=ctk.CTkFont(size=11),
            fg_color=C["accent"], hover_color="#7d6ef0",
            command=self._save_preset,
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            preset_row, text="Удалить", width=70, height=28,
            font=ctk.CTkFont(size=11),
            fg_color=C["surface3"], hover_color="#c0392b",
            command=self._delete_preset,
        ).pack(side="left", padx=2)

        # Description
        ctk.CTkLabel(
            scroll,
            text="Пресеты хранят настройки пайплайна (модель whisper, включённые шаги, интро/аутро и т.д.) "
                 "в виде JSON-файлов.",
            font=ctk.CTkFont(size=11),
            text_color=C["text3"],
            anchor="w",
            wraplength=500,
        ).pack(fill="x", padx=5, pady=(10, 5))

    # ── Dynamic social links ─────────────────────────────────────────

    def _add_social_link_row(self, name: str = "", url: str = ""):
        """Add a row to the social links list."""
        row_frame = ctk.CTkFrame(self._social_links_container, fg_color="transparent")
        row_frame.pack(fill="x", pady=2)

        name_entry = tk.Entry(
            row_frame,
            font=("Helvetica", 13),
            bg=C["surface2"], fg=C["text"],
            insertbackground=C["text"],
            selectbackground=C["accent"], selectforeground=C["text"],
            relief="flat", bd=0,
            highlightthickness=1, highlightcolor=C["accent"], highlightbackground=C["border"],
            width=15,
        )
        name_entry.pack(side="left", ipady=6, padx=(0, 4))
        name_entry.insert(0, name)
        self._bind_clipboard(name_entry)
        self._bind_context_menu(name_entry)

        url_entry = tk.Entry(
            row_frame,
            font=("Helvetica", 13),
            bg=C["surface2"], fg=C["text"],
            insertbackground=C["text"],
            selectbackground=C["accent"], selectforeground=C["text"],
            relief="flat", bd=0,
            highlightthickness=1, highlightcolor=C["accent"], highlightbackground=C["border"],
        )
        url_entry.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 4))
        url_entry.insert(0, url)
        self._bind_clipboard(url_entry)
        self._bind_context_menu(url_entry)

        row_data = {"frame": row_frame, "name_entry": name_entry, "url_entry": url_entry}

        def _delete_row():
            row_frame.destroy()
            if row_data in self._social_link_rows:
                self._social_link_rows.remove(row_data)

        ctk.CTkButton(
            row_frame, text="✕", width=28, height=28,
            font=ctk.CTkFont(size=12),
            fg_color=C["surface3"], hover_color="#c0392b",
            command=_delete_row,
        ).pack(side="right", padx=(2, 0))

        self._social_link_rows.append(row_data)

    def _get_social_links_json(self) -> str:
        """Collect social link rows into a JSON string."""
        links = []
        for row in self._social_link_rows:
            n = row["name_entry"].get().strip()
            u = row["url_entry"].get().strip()
            if n or u:
                links.append({"name": n, "url": u})
        return json.dumps(links, ensure_ascii=False)

    def _load_social_links_from_json(self, raw: str):
        """Parse JSON string and populate rows."""
        # Clear existing
        for row in list(self._social_link_rows):
            row["frame"].destroy()
        self._social_link_rows.clear()

        try:
            data = json.loads(raw)
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        self._add_social_link_row(
                            name=item.get("name", ""),
                            url=item.get("url", ""),
                        )
        except (json.JSONDecodeError, TypeError):
            # Fallback: treat as comma-separated plain URLs (legacy format)
            if raw.strip():
                for part in raw.split(","):
                    part = part.strip()
                    if part:
                        self._add_social_link_row(name="", url=part)

    # ── Dynamic reference images ─────────────────────────────────────

    def _add_reference_image_row(self, path: str = ""):
        """Add a row to the reference images list."""
        row_frame = ctk.CTkFrame(self._ref_images_container, fg_color="transparent")
        row_frame.pack(fill="x", pady=2)

        display_name = Path(path).name if path else "(не выбрано)"
        path_var = {"value": path}

        name_label = ctk.CTkLabel(
            row_frame,
            text=display_name,
            font=ctk.CTkFont(size=12),
            text_color=C["text"],
            anchor="w",
        )
        name_label.pack(side="left", fill="x", expand=True, padx=(0, 4))

        row_data = {"frame": row_frame, "path_var": path_var, "label": name_label}

        def _browse():
            fp = filedialog.askopenfilename(
                parent=self,
                title="Выбрать изображение",
                filetypes=[("Images", "*.png *.jpg *.jpeg *.webp"), ("All", "*.*")],
            )
            if fp:
                path_var["value"] = fp
                name_label.configure(text=Path(fp).name)

        ctk.CTkButton(
            row_frame, text="Обзор", width=60, height=28,
            font=ctk.CTkFont(size=11),
            fg_color=C["surface3"], hover_color=C["accent"],
            command=_browse,
        ).pack(side="right", padx=(2, 0))

        def _delete_row():
            row_frame.destroy()
            if row_data in self._reference_image_rows:
                self._reference_image_rows.remove(row_data)

        ctk.CTkButton(
            row_frame, text="✕", width=28, height=28,
            font=ctk.CTkFont(size=12),
            fg_color=C["surface3"], hover_color="#c0392b",
            command=_delete_row,
        ).pack(side="right", padx=(2, 0))

        self._reference_image_rows.append(row_data)

    def _get_reference_images_json(self) -> str:
        """Collect reference image paths into a JSON string."""
        paths = []
        for row in self._reference_image_rows:
            p = row["path_var"]["value"]
            if p:
                paths.append(p)
        return json.dumps(paths, ensure_ascii=False)

    def _load_reference_images_from_json(self, raw: str):
        """Parse JSON string and populate rows."""
        for row in list(self._reference_image_rows):
            row["frame"].destroy()
        self._reference_image_rows.clear()

        try:
            data = json.loads(raw)
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, str) and item:
                        self._add_reference_image_row(path=item)
        except (json.JSONDecodeError, TypeError):
            # Fallback: treat as a single path (legacy)
            if raw.strip():
                self._add_reference_image_row(path=raw.strip())

    # ── Widget factories ─────────────────────────────────────────────

    def _create_section(self, parent, title: str):
        """Создание заголовка секции"""
        section_frame = ctk.CTkFrame(parent, fg_color="transparent")
        section_frame.pack(fill="x", pady=(15, 5))

        ctk.CTkLabel(
            section_frame,
            text=title,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=C["text"],
        ).pack(anchor="w")

        ctk.CTkFrame(section_frame, height=1, fg_color=C["border"]).pack(fill="x", pady=5)

    def _create_entry_field(self, parent, key: str, label: str, show: Optional[str] = None):
        """Создание поля ввода. Использует tk.Entry для надёжного Cmd+V."""
        field_frame = ctk.CTkFrame(parent, fg_color="transparent")
        field_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(
            field_frame,
            text=label,
            font=ctk.CTkFont(size=12),
            text_color=C["text"],
            width=200,
            anchor="w",
        ).pack(side="left", padx=(0, 10))

        # Native tk.Entry with explicit clipboard bindings
        entry = tk.Entry(
            field_frame,
            font=("Helvetica", 13),
            bg=C["surface2"], fg=C["text"],
            insertbackground=C["text"],
            selectbackground=C["accent"], selectforeground=C["text"],
            relief="flat", bd=0,
            highlightthickness=1, highlightcolor=C["accent"], highlightbackground=C["border"],
        )
        if show:
            entry.configure(show=show)
        entry.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 4))

        self._bind_clipboard(entry)
        self._bind_context_menu(entry)

        # Show/Hide toggle for masked fields
        if show:
            is_hidden = [True]

            def toggle_visibility():
                is_hidden[0] = not is_hidden[0]
                entry.configure(show="*" if is_hidden[0] else "")
                eye_btn.configure(text="Показать" if is_hidden[0] else "Скрыть")

            eye_btn = ctk.CTkButton(
                field_frame, text="Показать", width=60, height=28,
                font=ctk.CTkFont(size=11),
                fg_color=C["surface3"], hover_color=C["accent"],
                command=toggle_visibility,
            )
            eye_btn.pack(side="right", padx=(2, 0))

        self.entries[key] = entry

    def _create_dropdown_field(self, parent, key: str, label: str, values: list, default: str):
        """Создание выпадающего списка"""
        field_frame = ctk.CTkFrame(parent, fg_color="transparent")
        field_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(
            field_frame,
            text=label,
            font=ctk.CTkFont(size=12),
            text_color=C["text"],
            width=200,
            anchor="w",
        ).pack(side="left", padx=(0, 10))

        dropdown = ctk.CTkOptionMenu(
            field_frame,
            values=values,
            font=ctk.CTkFont(size=12),
            fg_color=C["surface2"], button_color=C["surface3"],
            button_hover_color=C["accent"],
        )
        dropdown.set(default)
        dropdown.pack(side="left", fill="x", expand=True)

        self.dropdowns[key] = dropdown

    def _create_file_picker_field(self, parent, key: str, label: str, filetypes: list):
        """Создание поля с кнопкой выбора файла"""
        field_frame = ctk.CTkFrame(parent, fg_color="transparent")
        field_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(
            field_frame,
            text=label,
            font=ctk.CTkFont(size=12),
            text_color=C["text"],
            width=200,
            anchor="w",
        ).pack(side="left", padx=(0, 10))

        # Text entry (same style as other entries)
        entry = tk.Entry(
            field_frame,
            font=("Helvetica", 13),
            bg=C["surface2"], fg=C["text"],
            insertbackground=C["text"],
            selectbackground=C["accent"], selectforeground=C["text"],
            relief="flat", bd=0,
            highlightthickness=1, highlightcolor=C["accent"], highlightbackground=C["border"],
        )
        entry.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 4))

        self._bind_clipboard(entry)
        self._bind_context_menu(entry)

        def _browse():
            path = filedialog.askopenfilename(
                parent=self,
                title=f"Выбрать {label}",
                filetypes=filetypes,
            )
            if path:
                entry.delete(0, "end")
                entry.insert(0, path)

        ctk.CTkButton(
            field_frame, text="Обзор", width=70, height=28,
            font=ctk.CTkFont(size=11),
            fg_color=C["surface3"], hover_color=C["accent"],
            command=_browse,
        ).pack(side="right", padx=(2, 0))

        self.entries[key] = entry

    # ── Clipboard & context menu helpers ─────────────────────────────

    @staticmethod
    def _bind_clipboard(entry: tk.Entry):
        """Force clipboard bindings (CustomTkinter can swallow them)."""
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

    @staticmethod
    def _bind_context_menu(entry: tk.Entry):
        """Attach a right-click context menu to an entry."""
        def _paste(e=None):
            try:
                txt = entry.clipboard_get()
                try:
                    entry.delete("sel.first", "sel.last")
                except tk.TclError:
                    pass
                entry.insert("insert", txt)
            except tk.TclError:
                pass

        def _copy(e=None):
            try:
                txt = entry.selection_get()
                entry.clipboard_clear()
                entry.clipboard_append(txt)
            except tk.TclError:
                pass

        def _cut(e=None):
            _copy()
            try:
                entry.delete("sel.first", "sel.last")
            except tk.TclError:
                pass

        def _select_all(e=None):
            entry.select_range(0, "end")
            entry.icursor("end")

        def _show_context_menu(e):
            ctx = tk.Menu(entry, tearoff=0,
                          bg=C["surface3"], fg=C["text"],
                          activebackground=C["accent"], activeforeground=C["text"],
                          font=("Helvetica", 12))
            ctx.add_command(label="Вырезать", command=_cut)
            ctx.add_command(label="Копировать", command=_copy)
            ctx.add_command(label="Вставить", command=_paste)
            ctx.add_separator()
            ctx.add_command(label="Выделить всё", command=_select_all)
            ctx.tk_popup(e.x_root, e.y_root)

        entry.bind("<Button-2>", _show_context_menu)
        entry.bind("<Button-3>", _show_context_menu)
        entry.bind("<Control-Button-1>", _show_context_menu)

    # ── Load / Save ──────────────────────────────────────────────────

    def _load_settings(self):
        """Загрузка настроек из .env файла"""
        if not self.env_path.exists():
            self.status_label.configure(
                text="Предупреждение: файл .env не найден",
                text_color="orange"
            )
            return

        try:
            env_vars = {}
            with open(self.env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()

            # Заполняем entry поля (skip dynamic keys handled separately)
            for key, entry in self.entries.items():
                if key in env_vars:
                    entry.delete(0, 'end')
                    entry.insert(0, env_vars[key])

            # Заполняем dropdown'ы
            for key, dropdown in self.dropdowns.items():
                if key in env_vars:
                    value = env_vars[key]
                    if key == "WHISPER_MODEL" and value in self.WHISPER_MODELS:
                        dropdown.set(value)
                    elif key == "WHISPER_DEVICE" and value in self.WHISPER_DEVICES:
                        dropdown.set(value)
                    elif key == "TRANSCRIPTION_ENGINE" and value in self.TRANSCRIPTION_ENGINES:
                        dropdown.set(value)

            # Load dynamic social links
            social_raw = env_vars.get("SOCIAL_LINKS", "")
            if social_raw:
                self._load_social_links_from_json(social_raw)

            # Load dynamic reference images
            ref_raw = env_vars.get("REFERENCE_IMAGES", "")
            if ref_raw:
                self._load_reference_images_from_json(ref_raw)
            else:
                # Legacy: single REFERENCE_IMAGE key
                legacy = env_vars.get("REFERENCE_IMAGE", "")
                if legacy:
                    self._add_reference_image_row(path=legacy)

            self.status_label.configure(
                text="Настройки загружены",
                text_color="green"
            )

        except Exception as e:
            self.status_label.configure(
                text=f"Ошибка загрузки настроек: {str(e)}",
                text_color="red"
            )

    def _save_settings(self):
        """Сохранение настроек в .env файл"""
        try:
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

            # Dynamic social links → JSON
            settings["SOCIAL_LINKS"] = self._get_social_links_json()

            # Dynamic reference images → JSON
            settings["REFERENCE_IMAGES"] = self._get_reference_images_json()

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
                text="Настройки сохранены",
                text_color="green"
            )

            # Вызываем callback если есть
            if self.on_save:
                self.on_save(settings)

        except Exception as e:
            self.status_label.configure(
                text=f"Ошибка сохранения настроек: {str(e)}",
                text_color="red"
            )

    def get_settings(self) -> dict:
        """Получить текущие настройки из UI"""
        settings = {}

        for key, entry in self.entries.items():
            settings[key] = entry.get().strip()

        for key, dropdown in self.dropdowns.items():
            settings[key] = dropdown.get()

        # Include dynamic data
        settings["SOCIAL_LINKS"] = self._get_social_links_json()
        settings["REFERENCE_IMAGES"] = self._get_reference_images_json()

        return settings

    # ── Image Models ─────────────────────────────────────────────────

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

    # ── Presets ───────────────────────────────────────────────────────

    def _refresh_presets(self):
        try:
            from core.presets import PresetManager
            pm = PresetManager()
            names = [p.name for p in pm.list_presets()]
            values = names if names else ["(нет)"]
            self._preset_dropdown.configure(values=values)
            if names:
                self._preset_dropdown.set(names[0])
            else:
                self._preset_dropdown.set("(нет)")
        except Exception:
            self._preset_dropdown.configure(values=["(нет)"])

    def _load_preset(self):
        try:
            from core.presets import PresetManager
            name = self._preset_dropdown.get()
            if name == "(нет)":
                return
            pm = PresetManager()
            preset = pm.load_preset(name)
            # Apply preset settings to entry fields
            for key, value in preset.settings.items():
                upkey = key.upper()
                if upkey in self.entries and value:
                    self.entries[upkey].delete(0, "end")
                    self.entries[upkey].insert(0, str(value))
            self.status_label.configure(text=f"Пресет '{name}' загружен", text_color="green")
        except Exception as e:
            self.status_label.configure(text=f"Ошибка: {e}", text_color="red")

    def _save_preset(self):
        try:
            from core.presets import PresetManager, Preset
            from tkinter import simpledialog
            name = simpledialog.askstring("Сохранить пресет", "Имя пресета:", parent=self)
            if not name:
                return
            settings = self.get_settings()
            preset = Preset(name=name, description="", settings=settings)
            pm = PresetManager()
            pm.save_preset(preset)
            self._refresh_presets()
            self.status_label.configure(text=f"Пресет '{name}' сохранён", text_color="green")
        except Exception as e:
            self.status_label.configure(text=f"Ошибка: {e}", text_color="red")

    def _delete_preset(self):
        try:
            from core.presets import PresetManager
            name = self._preset_dropdown.get()
            if name == "(нет)":
                return
            pm = PresetManager()
            pm.delete_preset(name)
            self._refresh_presets()
            self.status_label.configure(text=f"Пресет '{name}' удалён", text_color="green")
        except Exception as e:
            self.status_label.configure(text=f"Ошибка: {e}", text_color="red")
