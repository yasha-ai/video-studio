"""
Timeline Panel - Панель редактирования видео с timeline
"""

import customtkinter as ctk
from tkinter import Canvas, messagebox
from pathlib import Path
import threading
from typing import Optional, Callable
import sys

sys.path.append(str(Path(__file__).parent.parent))
from core.artifacts import ArtifactsManager
from processors.video_processor import VideoProcessor


class TimelinePanel(ctk.CTkFrame):
    """Панель редактирования видео с timeline виджетом"""
    
    def __init__(
        self,
        parent,
        on_video_edited: Optional[Callable[[str], None]] = None,
        **kwargs
    ):
        super().__init__(parent, **kwargs)
        
        self.on_video_edited = on_video_edited
        
        # Создаём менеджер артефактов для временных файлов
        self.artifacts = ArtifactsManager()
        self.processor = VideoProcessor(self.artifacts)
        
        # Данные проекта
        self.video_path: Optional[Path] = None
        self.duration: float = 0.0  # Длительность видео в секундах
        self.start_time: float = 0.0  # Начало выделения
        self.end_time: float = 0.0  # Конец выделения
        
        # Timeline настройки
        self.timeline_height = 80
        self.timeline_padding = 40
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Создание UI элементов"""
        
        # Заголовок
        header = ctk.CTkLabel(
            self,
            text="✂️ Edit & Trim",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        header.pack(pady=(10, 5), padx=20, anchor="w")
        
        description = ctk.CTkLabel(
            self,
            text="Обрежьте видео, выделив нужный фрагмент на timeline",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        description.pack(pady=(0, 15), padx=20, anchor="w")
        
        # Основной контейнер
        main_container = ctk.CTkFrame(self)
        main_container.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Информация о видео
        info_frame = ctk.CTkFrame(main_container)
        info_frame.pack(fill="x", padx=10, pady=10)
        
        self.info_label = ctk.CTkLabel(
            info_frame,
            text="📹 Видео не загружено",
            font=ctk.CTkFont(size=14)
        )
        self.info_label.pack(pady=10)
        
        # Timeline виджет (Canvas)
        timeline_frame = ctk.CTkFrame(main_container)
        timeline_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.timeline_canvas = Canvas(
            timeline_frame,
            height=self.timeline_height,
            bg="#2b2b2b",
            highlightthickness=0
        )
        self.timeline_canvas.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Привязка событий мыши
        self.timeline_canvas.bind("<Button-1>", self._on_timeline_click)
        self.timeline_canvas.bind("<B1-Motion>", self._on_timeline_drag)
        self.timeline_canvas.bind("<ButtonRelease-1>", self._on_timeline_release)
        
        # Контролы времени
        controls_frame = ctk.CTkFrame(main_container)
        controls_frame.pack(fill="x", padx=10, pady=10)
        
        # Start time
        start_frame = ctk.CTkFrame(controls_frame)
        start_frame.pack(side="left", padx=(10, 20))
        
        ctk.CTkLabel(
            start_frame,
            text="▶️ Начало:",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(side="left", padx=(0, 10))
        
        self.start_entry = ctk.CTkEntry(
            start_frame,
            width=100,
            placeholder_text="00:00:00"
        )
        self.start_entry.pack(side="left")
        self.start_entry.bind("<Return>", lambda e: self._on_time_changed())
        
        # End time
        end_frame = ctk.CTkFrame(controls_frame)
        end_frame.pack(side="left", padx=(0, 20))
        
        ctk.CTkLabel(
            end_frame,
            text="⏹️ Конец:",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(side="left", padx=(0, 10))
        
        self.end_entry = ctk.CTkEntry(
            end_frame,
            width=100,
            placeholder_text="00:00:00"
        )
        self.end_entry.pack(side="left")
        self.end_entry.bind("<Return>", lambda e: self._on_time_changed())
        
        # Duration
        duration_frame = ctk.CTkFrame(controls_frame)
        duration_frame.pack(side="left")
        
        ctk.CTkLabel(
            duration_frame,
            text="⏱️ Длительность:",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(side="left", padx=(0, 10))
        
        self.duration_label = ctk.CTkLabel(
            duration_frame,
            text="00:00:00",
            font=ctk.CTkFont(size=12)
        )
        self.duration_label.pack(side="left")
        
        # Кнопки действий
        actions_frame = ctk.CTkFrame(main_container)
        actions_frame.pack(fill="x", padx=10, pady=10)
        
        # Trim button
        self.trim_button = ctk.CTkButton(
            actions_frame,
            text="✂️ Обрезать видео",
            command=self._trim_video,
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40,
            state="disabled"
        )
        self.trim_button.pack(side="left", padx=(10, 10), expand=True, fill="x")
        
        # Reset button
        self.reset_button = ctk.CTkButton(
            actions_frame,
            text="🔄 Сбросить",
            command=self._reset_selection,
            font=ctk.CTkFont(size=14),
            height=40,
            fg_color="gray40",
            hover_color="gray30",
            state="disabled"
        )
        self.reset_button.pack(side="left", padx=(0, 10), expand=True, fill="x")
        
        # Статус
        self.status_label = ctk.CTkLabel(
            main_container,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.status_label.pack(pady=5)
    
    def load_video(self, video_path: Path):
        """Загрузить видео для редактирования"""
        self.video_path = video_path
        
        # Получить длительность видео через VideoProcessor
        try:
            # Используем metadata или пробуем extract_audio для получения длительности
            import subprocess
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)],
                capture_output=True,
                text=True,
                check=True
            )
            self.duration = float(result.stdout.strip())
            
            # Установить по умолчанию всё видео
            self.start_time = 0.0
            self.end_time = self.duration
            
            # Обновить UI
            self._update_info()
            self._draw_timeline()
            self._update_time_controls()
            
            # Активировать кнопки
            self.trim_button.configure(state="normal")
            self.reset_button.configure(state="normal")
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить видео:\n{e}")
    
    def _update_info(self):
        """Обновить информацию о видео"""
        if not self.video_path:
            self.info_label.configure(text="📹 Видео не загружено")
            return
        
        duration_str = self._format_time(self.duration)
        self.info_label.configure(
            text=f"📹 {self.video_path.name} • Длительность: {duration_str}"
        )
    
    def _draw_timeline(self):
        """Отрисовать timeline"""
        self.timeline_canvas.delete("all")
        
        if self.duration == 0:
            return
        
        width = self.timeline_canvas.winfo_width()
        height = self.timeline_height
        
        if width <= 1:  # Canvas еще не отрисован
            self.after(100, self._draw_timeline)
            return
        
        # Фон timeline
        self.timeline_canvas.create_rectangle(
            self.timeline_padding, 10,
            width - self.timeline_padding, height - 10,
            fill="#1a1a1a",
            outline="#444444",
            width=2
        )
        
        # Выделенная область
        timeline_width = width - 2 * self.timeline_padding
        start_x = self.timeline_padding + (self.start_time / self.duration) * timeline_width
        end_x = self.timeline_padding + (self.end_time / self.duration) * timeline_width
        
        self.timeline_canvas.create_rectangle(
            start_x, 10,
            end_x, height - 10,
            fill="#3b8eea",
            stipple="gray50",
            outline="#5aa5ff",
            width=2
        )
        
        # Маркеры начала и конца
        # Начало (зеленый)
        self.timeline_canvas.create_line(
            start_x, 10, start_x, height - 10,
            fill="#4CAF50",
            width=3,
            tags="start_marker"
        )
        self.timeline_canvas.create_oval(
            start_x - 5, height//2 - 5,
            start_x + 5, height//2 + 5,
            fill="#4CAF50",
            outline="white",
            width=2,
            tags="start_marker"
        )
        
        # Конец (красный)
        self.timeline_canvas.create_line(
            end_x, 10, end_x, height - 10,
            fill="#F44336",
            width=3,
            tags="end_marker"
        )
        self.timeline_canvas.create_oval(
            end_x - 5, height//2 - 5,
            end_x + 5, height//2 + 5,
            fill="#F44336",
            outline="white",
            width=2,
            tags="end_marker"
        )
        
        # Временные метки (каждые 10% длительности)
        for i in range(0, 11):
            x = self.timeline_padding + (i / 10) * timeline_width
            time = (i / 10) * self.duration
            time_str = self._format_time(time)
            
            self.timeline_canvas.create_line(
                x, height - 10, x, height - 5,
                fill="#666666",
                width=1
            )
            
            self.timeline_canvas.create_text(
                x, height - 3,
                text=time_str,
                fill="#888888",
                font=("Arial", 8),
                anchor="n"
            )
    
    def _on_timeline_click(self, event):
        """Обработка клика на timeline"""
        if self.duration == 0:
            return
        
        width = self.timeline_canvas.winfo_width()
        timeline_width = width - 2 * self.timeline_padding
        
        # Конвертировать клик в время
        click_time = ((event.x - self.timeline_padding) / timeline_width) * self.duration
        click_time = max(0, min(self.duration, click_time))
        
        # Определить, на какой маркер кликнули (ближайший)
        start_x = self.timeline_padding + (self.start_time / self.duration) * timeline_width
        end_x = self.timeline_padding + (self.end_time / self.duration) * timeline_width
        
        dist_to_start = abs(event.x - start_x)
        dist_to_end = abs(event.x - end_x)
        
        if dist_to_start < 20:
            self.dragging = "start"
        elif dist_to_end < 20:
            self.dragging = "end"
        else:
            # Создать новый выбор
            self.start_time = click_time
            self.end_time = click_time
            self.dragging = "end"
        
        self._draw_timeline()
        self._update_time_controls()
    
    def _on_timeline_drag(self, event):
        """Обработка перетаскивания на timeline"""
        if self.duration == 0 or not hasattr(self, 'dragging'):
            return
        
        width = self.timeline_canvas.winfo_width()
        timeline_width = width - 2 * self.timeline_padding
        
        # Конвертировать позицию в время
        drag_time = ((event.x - self.timeline_padding) / timeline_width) * self.duration
        drag_time = max(0, min(self.duration, drag_time))
        
        # Обновить соответствующий маркер
        if self.dragging == "start":
            self.start_time = min(drag_time, self.end_time)
        elif self.dragging == "end":
            self.end_time = max(drag_time, self.start_time)
        
        self._draw_timeline()
        self._update_time_controls()
    
    def _on_timeline_release(self, event):
        """Обработка отпускания мыши"""
        if hasattr(self, 'dragging'):
            del self.dragging
    
    def _update_time_controls(self):
        """Обновить поля ввода времени"""
        self.start_entry.delete(0, "end")
        self.start_entry.insert(0, self._format_time(self.start_time))
        
        self.end_entry.delete(0, "end")
        self.end_entry.insert(0, self._format_time(self.end_time))
        
        selected_duration = self.end_time - self.start_time
        self.duration_label.configure(text=self._format_time(selected_duration))
    
    def _on_time_changed(self):
        """Обработка ручного ввода времени"""
        try:
            start_str = self.start_entry.get()
            end_str = self.end_entry.get()
            
            self.start_time = self._parse_time(start_str)
            self.end_time = self._parse_time(end_str)
            
            # Валидация
            self.start_time = max(0, min(self.duration, self.start_time))
            self.end_time = max(self.start_time, min(self.duration, self.end_time))
            
            self._draw_timeline()
            self._update_time_controls()
            
        except ValueError:
            messagebox.showerror("Ошибка", "Неверный формат времени. Используйте HH:MM:SS")
    
    def _format_time(self, seconds: float) -> str:
        """Форматировать время в HH:MM:SS"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    def _parse_time(self, time_str: str) -> float:
        """Парсить время из HH:MM:SS в секунды"""
        parts = time_str.split(":")
        if len(parts) == 3:
            hours, minutes, seconds = map(int, parts)
            return hours * 3600 + minutes * 60 + seconds
        elif len(parts) == 2:
            minutes, seconds = map(int, parts)
            return minutes * 60 + seconds
        elif len(parts) == 1:
            return int(parts[0])
        else:
            raise ValueError("Invalid time format")
    
    def _reset_selection(self):
        """Сбросить выделение на всё видео"""
        self.start_time = 0.0
        self.end_time = self.duration
        self._draw_timeline()
        self._update_time_controls()
    
    def _trim_video(self):
        """Обрезать видео"""
        if not self.video_path:
            return
        
        if self.start_time >= self.end_time:
            messagebox.showerror("Ошибка", "Начало должно быть меньше конца")
            return
        
        self.trim_button.configure(state="disabled", text="⏳ Обработка...")
        self.status_label.configure(text="Обрезаем видео...")
        
        def trim_thread():
            try:
                # Формат вывода: video_trimmed_START-END.mp4
                output_filename = f"{self.video_path.stem}_trimmed_{int(self.start_time)}-{int(self.end_time)}.mp4"
                output_path = self.video_path.parent / output_filename
                
                # Обрезка через VideoProcessor
                self.processor.trim_video(
                    video_path=str(self.video_path),
                    output_path=str(output_path),
                    start_time=self.start_time,
                    end_time=self.end_time
                )
                
                self.after(0, lambda: self._trim_complete(output_path))
                
            except Exception as e:
                self.after(0, lambda: self._trim_error(str(e)))
        
        thread = threading.Thread(target=trim_thread, daemon=True)
        thread.start()
    
    def _trim_complete(self, output_path: Path):
        """Обработка завершения обрезки"""
        self.trim_button.configure(state="normal", text="✂️ Обрезать видео")
        self.status_label.configure(
            text=f"✅ Видео обрезано: {output_path.name}",
            text_color="green"
        )
        
        messagebox.showinfo(
            "Готово",
            f"Видео успешно обрезано!\n\nСохранено: {output_path.name}"
        )
        
        # Вызвать callback если есть
        if self.on_video_edited:
            self.on_video_edited(str(output_path))
    
    def _trim_error(self, error_msg: str):
        """Обработка ошибки обрезки"""
        self.trim_button.configure(state="normal", text="✂️ Обрезать видео")
        self.status_label.configure(
            text=f"❌ Ошибка: {error_msg}",
            text_color="red"
        )
        
        messagebox.showerror("Ошибка", f"Не удалось обрезать видео:\n{error_msg}")
