"""
Main Window - Главное окно приложения Video Studio (с интеграцией модулей)
"""

import customtkinter as ctk
from pathlib import Path
from tkinter import filedialog, messagebox
import threading

# Импорт модулей обработки
# Пытаемся использовать относительные импорты (если запущен как пакет)
# Иначе используем абсолютные импорты (если запущен напрямую)
try:
    from ..core.artifacts import ArtifactsManager
    from ..processors.video_processor import VideoProcessor
    from ..processors.whisper_transcriber import WhisperTranscriber
    from ..processors.audio_cleanup import AudioCleanup
    from ..processors.title_generator import TitleGenerator
    from ..processors.cover_generator import CoverGenerator
    from ..processors.youtube_uploader import YouTubeUploader
except ImportError:
    # Fallback для абсолютных импортов
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from core.artifacts import ArtifactsManager
    from processors.video_processor import VideoProcessor
    from processors.whisper_transcriber import WhisperTranscriber
    from processors.audio_cleanup import AudioCleanup
    from processors.title_generator import TitleGenerator
    from processors.cover_generator import CoverGenerator
    from processors.youtube_uploader import YouTubeUploader


class MainWindow(ctk.CTk):
    """Главное окно приложения"""
    
    def __init__(self):
        super().__init__()
        
        # Настройка окна
        self.title("Video Studio — YouTube Video Editor")
        self.geometry("1400x900")
        self.minsize(1200, 700)
        
        # Центрируем окно на экране
        self._center_window()
        
        # Инициализация обработчиков
        self._init_processors()
        
        # Хранилище данных проекта
        self.project = {
            "video_path": None,
            "audio_path": None,
            "transcription": None,
            "titles": [],
            "selected_title": None,
            "thumbnail_path": None,
        }
        
        # Инициализация UI
        self._setup_ui()
        
    def _center_window(self):
        """Центрирование окна на экране"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
    
    def _init_processors(self):
        """Инициализация всех процессоров"""
        try:
            # Создаём менеджер артефактов (для хранения промежуточных файлов)
            self.artifacts = ArtifactsManager()
            
            # Инициализируем процессоры
            self.video_processor = VideoProcessor(self.artifacts)
            self.whisper = WhisperTranscriber()
            self.audio_cleanup = AudioCleanup()
            self.title_generator = TitleGenerator()
            self.cover_generator = CoverGenerator()
            # YouTubeUploader требует OAuth, инициализируем позже
            self.youtube_uploader = None
        except Exception as e:
            print(f"⚠️ Ошибка инициализации процессоров: {e}")
        
    def _setup_ui(self):
        """Создание интерфейса"""
        
        # === ВЕРХНЯЯ ПАНЕЛЬ (Header) ===
        self.header_frame = ctk.CTkFrame(self, height=60, corner_radius=0)
        self.header_frame.pack(fill="x", side="top")
        self.header_frame.pack_propagate(False)
        
        # Логотип и название
        self.logo_label = ctk.CTkLabel(
            self.header_frame,
            text="🎬 VIDEO STUDIO",
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        self.logo_label.pack(side="left", padx=20)
        
        # Кнопки верхнего меню
        self.menu_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.menu_frame.pack(side="right", padx=20)
        
        menu_buttons = [
            ("⚙️ Settings", self._open_settings),
            ("❓ Help", self._open_help),
        ]
        
        for text, command in menu_buttons:
            btn = ctk.CTkButton(
                self.menu_frame,
                text=text,
                width=100,
                command=command,
                fg_color="transparent",
                hover_color=("gray70", "gray30"),
            )
            btn.pack(side="left", padx=5)
        
        # === БОКОВАЯ ПАНЕЛЬ (Sidebar) ===
        self.sidebar_frame = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar_frame.pack(fill="y", side="left")
        self.sidebar_frame.pack_propagate(False)
        
        # Заголовок боковой панели
        self.sidebar_title = ctk.CTkLabel(
            self.sidebar_frame,
            text="Workflow Steps",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        self.sidebar_title.pack(pady=20)
        
        # Список этапов работы
        self.workflow_steps = [
            ("📁 Import Video", self._show_import_panel),
            ("✂️ Edit & Trim", self._show_edit_panel),
            ("🎤 Transcribe", self._show_transcribe_panel),
            ("🧹 Clean Audio", self._show_audio_cleanup_panel),
            ("📝 Generate Titles", self._show_titles_panel),
            ("🎨 Create Thumbnail", self._show_thumbnail_panel),
            ("▶️ Preview", self._show_preview_panel),
            ("📤 Upload to YouTube", self._show_upload_panel),
        ]
        
        for step_name, command in self.workflow_steps:
            btn = ctk.CTkButton(
                self.sidebar_frame,
                text=step_name,
                anchor="w",
                height=40,
                fg_color="transparent",
                text_color=("gray10", "gray90"),
                hover_color=("gray70", "gray30"),
                command=command,
            )
            btn.pack(fill="x", padx=10, pady=5)
        
        # === ОСНОВНАЯ ОБЛАСТЬ (Main Content) ===
        self.content_frame = ctk.CTkFrame(self, corner_radius=0)
        self.content_frame.pack(fill="both", expand=True, side="left")
        
        # Приветственный экран
        self._show_welcome_screen()
        
        # === НИЖНЯЯ ПАНЕЛЬ (Status Bar) ===
        self.status_bar = ctk.CTkFrame(self, height=30, corner_radius=0)
        self.status_bar.pack(fill="x", side="bottom")
        self.status_bar.pack_propagate(False)
        
        self.status_label = ctk.CTkLabel(
            self.status_bar,
            text="Ready",
            font=ctk.CTkFont(size=12),
        )
        self.status_label.pack(side="left", padx=10)
    
    # ========== ЭКРАНЫ WORKFLOW ==========
    
    def _clear_content(self):
        """Очистка основной области"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
    
    def _show_welcome_screen(self):
        """Показ приветственного экрана"""
        self._clear_content()
        
        welcome_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        welcome_frame.pack(expand=True)
        
        # Приветственный текст
        welcome_text = ctk.CTkLabel(
            welcome_frame,
            text="Welcome to Video Studio!",
            font=ctk.CTkFont(size=32, weight="bold"),
        )
        welcome_text.pack(pady=(0, 10))
        
        subtitle = ctk.CTkLabel(
            welcome_frame,
            text="Professional YouTube video editing & publishing",
            font=ctk.CTkFont(size=16),
            text_color="gray60",
        )
        subtitle.pack(pady=(0, 40))
        
        # Кнопка начала работы
        start_button = ctk.CTkButton(
            welcome_frame,
            text="📁 Import Video to Start",
            font=ctk.CTkFont(size=18, weight="bold"),
            height=50,
            width=300,
            command=self._show_import_panel,
        )
        start_button.pack()
    
    def _show_import_panel(self):
        """Панель импорта видео"""
        self._clear_content()
        self._update_status("Import Video")
        
        panel = ctk.CTkFrame(self.content_frame)
        panel.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Заголовок
        title = ctk.CTkLabel(
            panel,
            text="📁 Import Video",
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        title.pack(pady=(20, 10))
        
        # Информация о текущем видео
        if self.project["video_path"]:
            info = ctk.CTkLabel(
                panel,
                text=f"Current: {Path(self.project['video_path']).name}",
                font=ctk.CTkFont(size=14),
                text_color="green",
            )
            info.pack(pady=10)
        
        # Кнопка выбора файла
        select_btn = ctk.CTkButton(
            panel,
            text="Select Video File",
            font=ctk.CTkFont(size=16),
            height=50,
            width=300,
            command=self._import_video,
        )
        select_btn.pack(pady=20)
        
        # Поддерживаемые форматы
        formats = ctk.CTkLabel(
            panel,
            text="Supported: MP4, MOV, AVI, MKV",
            font=ctk.CTkFont(size=12),
            text_color="gray60",
        )
        formats.pack()
    
    def _show_edit_panel(self):
        """Панель редактирования"""
        if not self.project["video_path"]:
            messagebox.showwarning("No Video", "Please import a video first!")
            return
        
        self._clear_content()
        self._update_status("Edit & Trim")
        
        panel = ctk.CTkFrame(self.content_frame)
        panel.pack(fill="both", expand=True, padx=20, pady=20)
        
        title = ctk.CTkLabel(
            panel,
            text="✂️ Edit & Trim Video",
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        title.pack(pady=20)
        
        # TODO: Добавить timeline и preview
        placeholder = ctk.CTkLabel(
            panel,
            text="Video editing interface\n(Timeline, trim tools, preview)",
            font=ctk.CTkFont(size=14),
            text_color="gray60",
        )
        placeholder.pack(expand=True)
    
    def _show_transcribe_panel(self):
        """Панель транскрибации"""
        if not self.project["video_path"]:
            messagebox.showwarning("No Video", "Please import a video first!")
            return
        
        self._clear_content()
        self._update_status("Transcribe Audio")
        
        panel = ctk.CTkFrame(self.content_frame)
        panel.pack(fill="both", expand=True, padx=20, pady=20)
        
        title = ctk.CTkLabel(
            panel,
            text="🎤 Transcribe Audio",
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        title.pack(pady=20)
        
        # Кнопка запуска транскрибации
        transcribe_btn = ctk.CTkButton(
            panel,
            text="Start Transcription (Whisper)",
            font=ctk.CTkFont(size=16),
            height=50,
            width=300,
            command=self._run_transcription,
        )
        transcribe_btn.pack(pady=20)
        
        # Результат транскрибации
        if self.project["transcription"]:
            result_frame = ctk.CTkFrame(panel)
            result_frame.pack(fill="both", expand=True, padx=20, pady=20)
            
            result_text = ctk.CTkTextbox(result_frame, font=ctk.CTkFont(size=12))
            result_text.pack(fill="both", expand=True)
            result_text.insert("1.0", self.project["transcription"])
            result_text.configure(state="disabled")
    
    def _show_audio_cleanup_panel(self):
        """Панель очистки аудио"""
        if not self.project["video_path"]:
            messagebox.showwarning("No Video", "Please import a video first!")
            return
        
        self._clear_content()
        self._update_status("Clean Audio")
        
        panel = ctk.CTkFrame(self.content_frame)
        panel.pack(fill="both", expand=True, padx=20, pady=20)
        
        title = ctk.CTkLabel(
            panel,
            text="🧹 Clean Audio",
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        title.pack(pady=20)
        
        # Кнопка очистки
        cleanup_btn = ctk.CTkButton(
            panel,
            text="Clean Audio (AI)",
            font=ctk.CTkFont(size=16),
            height=50,
            width=300,
            command=self._run_audio_cleanup,
        )
        cleanup_btn.pack(pady=20)
    
    def _show_titles_panel(self):
        """Панель генерации заголовков"""
        if not self.project["transcription"]:
            messagebox.showwarning("No Transcription", "Please transcribe video first!")
            return
        
        self._clear_content()
        self._update_status("Generate Titles")
        
        panel = ctk.CTkFrame(self.content_frame)
        panel.pack(fill="both", expand=True, padx=20, pady=20)
        
        title = ctk.CTkLabel(
            panel,
            text="📝 Generate Titles",
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        title.pack(pady=20)
        
        # Кнопка генерации
        generate_btn = ctk.CTkButton(
            panel,
            text="Generate Titles (AI)",
            font=ctk.CTkFont(size=16),
            height=50,
            width=300,
            command=self._run_title_generation,
        )
        generate_btn.pack(pady=20)
        
        # Список сгенерированных заголовков
        if self.project["titles"]:
            titles_frame = ctk.CTkFrame(panel)
            titles_frame.pack(fill="both", expand=True, padx=20, pady=20)
            
            for i, title_text in enumerate(self.project["titles"], 1):
                title_btn = ctk.CTkButton(
                    titles_frame,
                    text=f"{i}. {title_text}",
                    anchor="w",
                    command=lambda t=title_text: self._select_title(t),
                )
                title_btn.pack(fill="x", pady=5, padx=10)
    
    def _show_thumbnail_panel(self):
        """Панель создания обложки"""
        if not self.project["selected_title"]:
            messagebox.showwarning("No Title", "Please generate and select a title first!")
            return
        
        self._clear_content()
        self._update_status("Create Thumbnail")
        
        panel = ctk.CTkFrame(self.content_frame)
        panel.pack(fill="both", expand=True, padx=20, pady=20)
        
        title = ctk.CTkLabel(
            panel,
            text="🎨 Create Thumbnail",
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        title.pack(pady=20)
        
        # Кнопка генерации
        generate_btn = ctk.CTkButton(
            panel,
            text="Generate Thumbnail (Gemini)",
            font=ctk.CTkFont(size=16),
            height=50,
            width=300,
            command=self._run_thumbnail_generation,
        )
        generate_btn.pack(pady=20)
    
    def _show_preview_panel(self):
        """Панель предпросмотра"""
        self._clear_content()
        self._update_status("Preview")
        
        panel = ctk.CTkFrame(self.content_frame)
        panel.pack(fill="both", expand=True, padx=20, pady=20)
        
        title = ctk.CTkLabel(
            panel,
            text="▶️ Preview",
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        title.pack(pady=20)
        
        # TODO: Добавить video player
        placeholder = ctk.CTkLabel(
            panel,
            text="Video preview player\n(Coming soon)",
            font=ctk.CTkFont(size=14),
            text_color="gray60",
        )
        placeholder.pack(expand=True)
    
    def _show_upload_panel(self):
        """Панель загрузки на YouTube"""
        if not self.project["video_path"]:
            messagebox.showwarning("No Video", "Please complete all steps first!")
            return
        
        self._clear_content()
        self._update_status("Upload to YouTube")
        
        panel = ctk.CTkFrame(self.content_frame)
        panel.pack(fill="both", expand=True, padx=20, pady=20)
        
        title = ctk.CTkLabel(
            panel,
            text="📤 Upload to YouTube",
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        title.pack(pady=20)
        
        # Кнопка загрузки
        upload_btn = ctk.CTkButton(
            panel,
            text="Upload Video",
            font=ctk.CTkFont(size=16),
            height=50,
            width=300,
            command=self._run_youtube_upload,
        )
        upload_btn.pack(pady=20)
    
    # ========== ДЕЙСТВИЯ ==========
    
    def _import_video(self):
        """Импорт видеофайла"""
        filetypes = [
            ("Video files", "*.mp4 *.mov *.avi *.mkv"),
            ("All files", "*.*")
        ]
        
        filepath = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=filetypes
        )
        
        if filepath:
            self.project["video_path"] = filepath
            self._update_status(f"Loaded: {Path(filepath).name}")
            messagebox.showinfo("Success", f"Video loaded:\n{Path(filepath).name}")
            self._show_import_panel()  # Refresh panel
    
    def _run_transcription(self):
        """Запуск транскрибации"""
        self._update_status("Transcribing... (this may take a while)")
        
        def transcribe():
            try:
                result = self.whisper.transcribe(self.project["video_path"])
                self.project["transcription"] = result["text"]
                self.after(0, lambda: self._update_status("Transcription complete!"))
                self.after(0, self._show_transcribe_panel)  # Refresh
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", f"Transcription failed:\n{e}"))
        
        threading.Thread(target=transcribe, daemon=True).start()
    
    def _run_audio_cleanup(self):
        """Запуск очистки аудио"""
        self._update_status("Cleaning audio...")
        
        def cleanup():
            try:
                output_path = Path(self.project["video_path"]).parent / "audio_cleaned.wav"
                self.audio_cleanup.cleanup(
                    self.project["video_path"],
                    str(output_path),
                    preset="medium"
                )
                self.project["audio_path"] = str(output_path)
                self.after(0, lambda: self._update_status("Audio cleaned!"))
                self.after(0, lambda: messagebox.showinfo("Success", "Audio cleanup complete!"))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", f"Cleanup failed:\n{e}"))
        
        threading.Thread(target=cleanup, daemon=True).start()
    
    def _run_title_generation(self):
        """Запуск генерации заголовков"""
        self._update_status("Generating titles...")
        
        def generate():
            try:
                titles = self.title_generator.generate(
                    description=self.project["transcription"][:500],  # First 500 chars
                    count=8,
                    style="engaging"
                )
                self.project["titles"] = titles
                self.after(0, lambda: self._update_status("Titles generated!"))
                self.after(0, self._show_titles_panel)  # Refresh
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", f"Title generation failed:\n{e}"))
        
        threading.Thread(target=generate, daemon=True).start()
    
    def _select_title(self, title: str):
        """Выбор заголовка"""
        self.project["selected_title"] = title
        self._update_status(f"Selected: {title}")
        messagebox.showinfo("Title Selected", f"Selected:\n{title}")
    
    def _run_thumbnail_generation(self):
        """Запуск генерации обложки"""
        self._update_status("Generating thumbnail...")
        
        def generate():
            try:
                output_path = Path(self.project["video_path"]).parent / "thumbnail.jpg"
                self.cover_generator.generate(
                    title=self.project["selected_title"],
                    output_path=str(output_path),
                    style="modern"
                )
                self.project["thumbnail_path"] = str(output_path)
                self.after(0, lambda: self._update_status("Thumbnail generated!"))
                self.after(0, lambda: messagebox.showinfo("Success", f"Thumbnail saved:\n{output_path}"))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", f"Thumbnail generation failed:\n{e}"))
        
        threading.Thread(target=generate, daemon=True).start()
    
    def _run_youtube_upload(self):
        """Запуск загрузки на YouTube"""
        messagebox.showinfo("Coming Soon", "YouTube upload requires OAuth setup.\nSee docs/youtube-integration.md")
    
    def _open_settings(self):
        """Открыть настройки"""
        messagebox.showinfo("Settings", "Settings panel coming soon!\nFor now, edit .env file manually.")
        
    def _open_help(self):
        """Открыть справку"""
        messagebox.showinfo("Help", "Video Studio Help\n\nWorkflow:\n1. Import video\n2. Transcribe\n3. Clean audio\n4. Generate titles\n5. Create thumbnail\n6. Upload to YouTube\n\nSee README.md for details.")
        
    def _update_status(self, message: str):
        """Обновить текст статус-бара"""
        self.status_label.configure(text=message)
        print(f"📊 {message}")
