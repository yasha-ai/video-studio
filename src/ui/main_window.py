"""
Main Window - Главное окно приложения Video Studio
"""

import customtkinter as ctk
from pathlib import Path


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
        workflow_steps = [
            "📁 Import Video",
            "✂️ Edit & Trim",
            "🎤 Transcribe",
            "🧹 Clean Audio",
            "📝 Generate Titles",
            "🎨 Create Thumbnail",
            "▶️ Preview",
            "📤 Upload to YouTube",
        ]
        
        for step in workflow_steps:
            btn = ctk.CTkButton(
                self.sidebar_frame,
                text=step,
                anchor="w",
                height=40,
                fg_color="transparent",
                text_color=("gray10", "gray90"),
                hover_color=("gray70", "gray30"),
                command=lambda s=step: self._switch_workflow_step(s),
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
        
    def _show_welcome_screen(self):
        """Показ приветственного экрана"""
        # Очистка content_frame
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
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
            command=self._import_video,
        )
        start_button.pack()
        
    def _import_video(self):
        """Импорт видеофайла"""
        # TODO: Реализовать файловый диалог и загрузку видео
        self._update_status("Importing video...")
        print("📁 Import video functionality - TODO")
        
    def _switch_workflow_step(self, step: str):
        """Переключение между этапами работы"""
        self._update_status(f"Switched to: {step}")
        print(f"Switched to workflow step: {step}")
        
    def _open_settings(self):
        """Открыть настройки"""
        print("⚙️ Settings - TODO")
        
    def _open_help(self):
        """Открыть справку"""
        print("❓ Help - TODO")
        
    def _update_status(self, message: str):
        """Обновить текст статус-бара"""
        self.status_label.configure(text=message)
