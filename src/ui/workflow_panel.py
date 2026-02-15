"""
Workflow Panel — панель управления этапами обработки видео
"""

import customtkinter as ctk
from typing import Dict, Callable, Optional
from ..core.artifacts import WorkflowState


class WorkflowPanel(ctk.CTkFrame):
    """Панель с чекбоксами для управления этапами workflow"""
    
    # Описания этапов для UI
    STEP_LABELS = {
        "import_video": "📁 Import Video",
        "edit_trim": "✂️ Edit & Trim",
        "transcribe": "🎤 Transcribe Audio",
        "clean_audio": "🧹 Clean Audio",
        "generate_titles": "📝 Generate Titles",
        "create_thumbnail": "🎨 Create Thumbnail",
        "preview": "▶️ Preview Video",
        "upload_youtube": "📤 Upload to YouTube",
    }
    
    def __init__(
        self, 
        parent, 
        workflow_state: Optional[WorkflowState] = None,
        on_step_toggle: Optional[Callable] = None,
        on_run_step: Optional[Callable] = None,
        **kwargs
    ):
        """
        Инициализация панели workflow
        
        Args:
            parent: Родительский виджет
            workflow_state: Состояние workflow (опционально)
            on_step_toggle: Callback при переключении чекбокса
            on_run_step: Callback при запуске этапа
        """
        super().__init__(parent, **kwargs)
        
        self.workflow_state = workflow_state
        self.on_step_toggle = on_step_toggle
        self.on_run_step = on_run_step
        
        # Словарь чекбоксов {step_name: checkbox_widget}
        self.checkboxes: Dict[str, ctk.CTkCheckBox] = {}
        
        # Словарь кнопок запуска {step_name: button_widget}
        self.run_buttons: Dict[str, ctk.CTkButton] = {}
        
        # Словарь индикаторов статуса {step_name: label_widget}
        self.status_labels: Dict[str, ctk.CTkLabel] = {}
        
        self._setup_ui()
        
    def _setup_ui(self):
        """Создание UI панели"""
        
        # Заголовок панели
        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        title_label = ctk.CTkLabel(
            title_frame,
            text="Workflow Steps",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        title_label.pack(side="left")
        
        # Кнопки управления всеми этапами
        control_frame = ctk.CTkFrame(title_frame, fg_color="transparent")
        control_frame.pack(side="right")
        
        select_all_btn = ctk.CTkButton(
            control_frame,
            text="Select All",
            width=80,
            height=24,
            font=ctk.CTkFont(size=11),
            command=self._select_all_steps,
        )
        select_all_btn.pack(side="left", padx=2)
        
        deselect_all_btn = ctk.CTkButton(
            control_frame,
            text="Deselect All",
            width=80,
            height=24,
            font=ctk.CTkFont(size=11),
            command=self._deselect_all_steps,
        )
        deselect_all_btn.pack(side="left", padx=2)
        
        # Разделитель
        separator = ctk.CTkFrame(self, height=2)
        separator.pack(fill="x", padx=10, pady=5)
        
        # Создаем чекбоксы и кнопки для каждого этапа
        for step in WorkflowState.WORKFLOW_STEPS:
            self._create_step_row(step)
            
        # Разделитель перед кнопкой запуска
        separator2 = ctk.CTkFrame(self, height=2)
        separator2.pack(fill="x", padx=10, pady=(15, 10))
        
        # Кнопка запуска выбранных этапов
        run_frame = ctk.CTkFrame(self, fg_color="transparent")
        run_frame.pack(fill="x", padx=10, pady=10)
        
        self.run_workflow_btn = ctk.CTkButton(
            run_frame,
            text="▶️ Run Selected Steps",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40,
            command=self._run_selected_steps,
        )
        self.run_workflow_btn.pack(fill="x")
        
        # Индикатор прогресса
        self.progress_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="gray60",
        )
        self.progress_label.pack(pady=5)
        
    def _create_step_row(self, step: str):
        """Создание строки для одного этапа"""
        
        # Контейнер для строки
        row_frame = ctk.CTkFrame(self, fg_color="transparent")
        row_frame.pack(fill="x", padx=10, pady=3)
        
        # Левая часть: чекбокс
        checkbox = ctk.CTkCheckBox(
            row_frame,
            text=self.STEP_LABELS.get(step, step),
            font=ctk.CTkFont(size=13),
            command=lambda: self._on_checkbox_toggle(step),
        )
        
        # Устанавливаем начальное состояние из workflow_state
        if self.workflow_state:
            is_enabled = self.workflow_state.is_step_enabled(step)
            checkbox.select() if is_enabled else checkbox.deselect()
        else:
            checkbox.select()  # По умолчанию все включены
            
        checkbox.pack(side="left", fill="x", expand=True)
        self.checkboxes[step] = checkbox
        
        # Средняя часть: индикатор статуса
        status_label = ctk.CTkLabel(
            row_frame,
            text="",
            width=80,
            font=ctk.CTkFont(size=11),
        )
        status_label.pack(side="left", padx=5)
        self.status_labels[step] = status_label
        
        # Обновляем статус
        self._update_step_status(step)
        
        # Правая часть: кнопка запуска одного этапа
        run_btn = ctk.CTkButton(
            row_frame,
            text="▶",
            width=30,
            height=24,
            font=ctk.CTkFont(size=12),
            command=lambda: self._run_single_step(step),
        )
        run_btn.pack(side="right")
        self.run_buttons[step] = run_btn
        
    def _on_checkbox_toggle(self, step: str):
        """Обработка переключения чекбокса"""
        is_checked = self.checkboxes[step].get()
        
        # Обновляем workflow_state
        if self.workflow_state:
            if is_checked:
                self.workflow_state.enable_step(step)
            else:
                self.workflow_state.disable_step(step)
        
        # Вызываем callback если есть
        if self.on_step_toggle:
            self.on_step_toggle(step, is_checked)
            
        # Обновляем индикатор прогресса
        self._update_progress()
        
    def _run_single_step(self, step: str):
        """Запуск одного этапа"""
        if self.on_run_step:
            self.on_run_step(step)
        else:
            print(f"Running step: {step}")
            
    def _run_selected_steps(self):
        """Запуск всех выбранных этапов"""
        selected_steps = [
            step for step, checkbox in self.checkboxes.items()
            if checkbox.get()
        ]
        
        if not selected_steps:
            print("No steps selected")
            return
            
        print(f"Running {len(selected_steps)} steps: {selected_steps}")
        
        # TODO: Реализовать последовательный запуск этапов
        for step in selected_steps:
            self._run_single_step(step)
            
    def _select_all_steps(self):
        """Выбрать все этапы"""
        for checkbox in self.checkboxes.values():
            checkbox.select()
            
        # Обновляем workflow_state
        if self.workflow_state:
            for step in WorkflowState.WORKFLOW_STEPS:
                self.workflow_state.enable_step(step)
                
        self._update_progress()
        
    def _deselect_all_steps(self):
        """Снять выбор со всех этапов"""
        for checkbox in self.checkboxes.values():
            checkbox.deselect()
            
        # Обновляем workflow_state
        if self.workflow_state:
            for step in WorkflowState.WORKFLOW_STEPS:
                self.workflow_state.disable_step(step)
                
        self._update_progress()
        
    def _update_step_status(self, step: str):
        """Обновление индикатора статуса этапа"""
        if not self.workflow_state:
            return
            
        status_label = self.status_labels[step]
        
        if self.workflow_state.is_step_completed(step):
            status_label.configure(text="✓ Done", text_color="green")
        elif not self.workflow_state.is_step_enabled(step):
            status_label.configure(text="Disabled", text_color="gray50")
        else:
            error = self.workflow_state.steps_status[step].get("error")
            if error:
                status_label.configure(text="✗ Error", text_color="red")
            else:
                status_label.configure(text="○ Pending", text_color="gray60")
                
    def _update_progress(self):
        """Обновление индикатора общего прогресса"""
        if not self.workflow_state:
            return
            
        enabled_steps = [
            step for step in WorkflowState.WORKFLOW_STEPS
            if self.workflow_state.is_step_enabled(step)
        ]
        
        completed_steps = [
            step for step in enabled_steps
            if self.workflow_state.is_step_completed(step)
        ]
        
        if not enabled_steps:
            self.progress_label.configure(text="No steps selected")
        else:
            progress_text = (
                f"Progress: {len(completed_steps)}/{len(enabled_steps)} "
                f"steps completed"
            )
            self.progress_label.configure(text=progress_text)
            
    def refresh(self):
        """Обновление всех индикаторов статуса"""
        for step in WorkflowState.WORKFLOW_STEPS:
            self._update_step_status(step)
        self._update_progress()
        
    def set_step_completed(self, step: str):
        """Отметить этап как завершенный"""
        if self.workflow_state:
            self.workflow_state.mark_completed(step)
        self._update_step_status(step)
        self._update_progress()
        
    def set_step_error(self, step: str, error_message: str):
        """Отметить ошибку на этапе"""
        if self.workflow_state:
            self.workflow_state.mark_error(step, error_message)
        self._update_step_status(step)
