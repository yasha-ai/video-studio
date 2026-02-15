"""
Main Window v2 — с интегрированной системой артефактов и модульным workflow
"""

import customtkinter as ctk
from pathlib import Path
from typing import Optional

from ..core.artifacts import ArtifactsManager, WorkflowState
from .workflow_panel import WorkflowPanel


class MainWindow(ctk.CTk):
    """Главное окно приложения с поддержкой артефактов и модульного workflow"""
    
    def __init__(self):
        super().__init__()
        
        # Настройка окна
        self.title("Video Studio — YouTube Video Editor")
        self.geometry("1400x900")
        self.minsize(1200, 700)
        
        # Центрируем окно на экране
        self._center_window()
        
        # Менеджеры проекта (создаются при импорте видео)
        self.artifacts: Optional[ArtifactsManager] = None
        self.workflow: Optional[WorkflowState] = None
        
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
            ("💾 Save Project", self._save_project),
            ("⚙️ Settings", self._open_settings),
            ("❓ Help", self._open_help),
        ]
        
        for text, command in menu_buttons:
            btn = ctk.CTkButton(
                self.menu_frame,
                text=text,
                width=120,
                command=command,
                fg_color="transparent",
                hover_color=("gray70", "gray30"),
            )
            btn.pack(side="left", padx=5)
        
        # === БОКОВАЯ ПАНЕЛЬ (Sidebar) === 
        self.sidebar_frame = ctk.CTkFrame(self, width=300, corner_radius=0)
        self.sidebar_frame.pack(fill="y", side="left")
        self.sidebar_frame.pack_propagate(False)
        
        # Workflow Panel (будет создана после импорта видео)
        self.workflow_panel = None
        self._show_sidebar_placeholder()
        
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
            text="Ready — Import a video to start",
            font=ctk.CTkFont(size=12),
        )
        self.status_label.pack(side="left", padx=10)
        
        # Индикатор проекта
        self.project_label = ctk.CTkLabel(
            self.status_bar,
            text="No project loaded",
            font=ctk.CTkFont(size=11),
            text_color="gray50",
        )
        self.project_label.pack(side="right", padx=10)
        
    def _show_sidebar_placeholder(self):
        """Placeholder для sidebar до импорта видео"""
        # Очистка sidebar
        for widget in self.sidebar_frame.winfo_children():
            widget.destroy()
            
        placeholder_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="Import a video\nto see workflow steps",
            font=ctk.CTkFont(size=14),
            text_color="gray50",
        )
        placeholder_label.pack(expand=True)
        
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
        subtitle.pack(pady=(0, 20))
        
        features_text = ctk.CTkLabel(
            welcome_frame,
            text=(
                "✓ Modular Workflow — run only the steps you need\n"
                "✓ Artifacts System — all intermediate files saved\n"
                "✓ AI-Powered — transcription, titles, thumbnails\n"
                "✓ YouTube Ready — one-click upload"
            ),
            font=ctk.CTkFont(size=14),
            text_color="gray70",
            justify="left",
        )
        features_text.pack(pady=(0, 40))
        
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
        from tkinter import filedialog
        
        # Диалог выбора файла
        file_path = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=[
                ("Video files", "*.mp4 *.mov *.avi *.mkv"),
                ("All files", "*.*"),
            ]
        )
        
        if not file_path:
            return
            
        self._update_status("Importing video...")
        
        # Создаем менеджеры проекта
        video_path = Path(file_path)
        project_name = video_path.stem
        
        self.artifacts = ArtifactsManager(project_name)
        self.workflow = WorkflowState(self.artifacts)
        
        # Сохраняем исходное видео как артефакт
        self.artifacts.save_artifact(
            "original_video",
            video_path,
            metadata={"filename": video_path.name, "size": video_path.stat().st_size}
        )
        
        # Помечаем этап импорта как завершенный
        self.workflow.mark_completed("import_video")
        
        # Создаем Workflow Panel
        self._create_workflow_panel()
        
        # Показываем главный экран
        self._show_main_screen()
        
        # Обновляем статусы
        self._update_status(f"Video imported: {project_name}")
        self.project_label.configure(text=f"Project: {self.artifacts.project_id}")
        
    def _create_workflow_panel(self):
        """Создание панели workflow"""
        # Очистка sidebar
        for widget in self.sidebar_frame.winfo_children():
            widget.destroy()
            
        # Создаем Workflow Panel
        self.workflow_panel = WorkflowPanel(
            self.sidebar_frame,
            workflow_state=self.workflow,
            on_step_toggle=self._on_step_toggle,
            on_run_step=self._on_run_step,
        )
        self.workflow_panel.pack(fill="both", expand=True, padx=5, pady=5)
        
    def _show_main_screen(self):
        """Показ главного экрана с артефактами"""
        # Очистка content_frame
        for widget in self.content_frame.winfo_children():
            widget.destroy()
            
        # Контейнер для контента
        main_container = ctk.CTkScrollableFrame(self.content_frame)
        main_container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Заголовок
        title_label = ctk.CTkLabel(
            main_container,
            text=f"Project: {self.artifacts.project_name}",
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        title_label.pack(anchor="w", pady=(0, 10))
        
        # Сводка по артефактам
        artifacts_summary = self.artifacts.export_summary()
        
        summary_label = ctk.CTkLabel(
            main_container,
            text=artifacts_summary,
            font=ctk.CTkFont(size=13, family="monospace"),
            justify="left",
            anchor="w",
        )
        summary_label.pack(anchor="w", fill="x", pady=10)
        
        # Сводка по workflow
        workflow_summary = self.workflow.get_summary()
        
        workflow_label = ctk.CTkLabel(
            main_container,
            text=workflow_summary,
            font=ctk.CTkFont(size=13, family="monospace"),
            justify="left",
            anchor="w",
        )
        workflow_label.pack(anchor="w", fill="x", pady=10)
        
    def _on_step_toggle(self, step: str, is_enabled: bool):
        """Обработка переключения этапа"""
        status = "enabled" if is_enabled else "disabled"
        self._update_status(f"Step {step}: {status}")
        
    def _on_run_step(self, step: str):
        """Запуск одного этапа workflow"""
        self._update_status(f"Running step: {step}...")
        
        # TODO: Реализовать процессоры для каждого этапа
        print(f"[TODO] Run step: {step}")
        
        # Временно помечаем как завершенный
        if self.workflow_panel:
            self.workflow_panel.set_step_completed(step)
            
        self._update_status(f"Step {step} completed")
        
    def _save_project(self):
        """Сохранение проекта"""
        if not self.artifacts:
            self._update_status("No project to save")
            return
            
        # Сохраняем манифест и состояние
        self.artifacts._update_manifest()
        if self.workflow:
            self.workflow._save_state()
            
        self._update_status("Project saved")
        print(f"Project saved: {self.artifacts.project_dir}")
        
    def _open_settings(self):
        """Открыть настройки"""
        # TODO: Создать окно настроек
        self._update_status("Settings - TODO")
        print("⚙️ Settings - TODO")
        
    def _open_help(self):
        """Открыть справку"""
        # TODO: Создать окно справки
        self._update_status("Help - TODO")
        print("❓ Help - TODO")
        
    def _update_status(self, message: str):
        """Обновить текст статус-бара"""
        self.status_label.configure(text=message)
