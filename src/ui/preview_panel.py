"""
Preview Panel - Панель предпросмотра видео
"""

import customtkinter as ctk
from tkinter import messagebox
from pathlib import Path
import subprocess
import platform
from typing import Optional, Callable


class PreviewPanel(ctk.CTkFrame):
    """Панель предпросмотра видео"""
    
    def __init__(
        self,
        parent,
        on_preview_error: Optional[Callable[[str], None]] = None,
        **kwargs
    ):
        super().__init__(parent, **kwargs)
        
        self.on_preview_error = on_preview_error
        self.video_path: Optional[Path] = None
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Создание UI элементов"""
        
        # Заголовок
        header = ctk.CTkLabel(
            self,
            text="▶️ Preview",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        header.pack(pady=(10, 5), padx=20, anchor="w")
        
        description = ctk.CTkLabel(
            self,
            text="Просмотрите видео перед публикацией",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        description.pack(pady=(0, 15), padx=20, anchor="w")
        
        # Основной контейнер
        main_container = ctk.CTkFrame(self)
        main_container.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Превью зона (заглушка - видео будет открываться в системном плеере)
        preview_zone = ctk.CTkFrame(
            main_container,
            fg_color="#1a1a1a",
            corner_radius=10
        )
        preview_zone.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Центральная иконка
        icon_label = ctk.CTkLabel(
            preview_zone,
            text="🎬",
            font=ctk.CTkFont(size=120)
        )
        icon_label.place(relx=0.5, rely=0.4, anchor="center")
        
        self.video_name_label = ctk.CTkLabel(
            preview_zone,
            text="Видео не загружено",
            font=ctk.CTkFont(size=16),
            text_color="gray"
        )
        self.video_name_label.place(relx=0.5, rely=0.6, anchor="center")
        
        # Кнопки управления
        controls_frame = ctk.CTkFrame(main_container)
        controls_frame.pack(fill="x", padx=10, pady=10)
        
        # Play button
        self.play_button = ctk.CTkButton(
            controls_frame,
            text="▶️ Открыть в плеере",
            command=self._play_video,
            font=ctk.CTkFont(size=14, weight="bold"),
            height=50,
            state="disabled"
        )
        self.play_button.pack(side="left", padx=(10, 5), expand=True, fill="x")
        
        # Quick Preview button (first 30 seconds)
        self.quick_preview_button = ctk.CTkButton(
            controls_frame,
            text="⚡ Быстрый просмотр (30 сек)",
            command=self._quick_preview,
            font=ctk.CTkFont(size=14),
            height=50,
            fg_color="gray40",
            hover_color="gray30",
            state="disabled"
        )
        self.quick_preview_button.pack(side="left", padx=5, expand=True, fill="x")
        
        # Open folder button
        self.folder_button = ctk.CTkButton(
            controls_frame,
            text="📂 Открыть папку",
            command=self._open_folder,
            font=ctk.CTkFont(size=14),
            height=50,
            fg_color="gray40",
            hover_color="gray30",
            state="disabled"
        )
        self.folder_button.pack(side="left", padx=(5, 10), expand=True, fill="x")
        
        # Информация о видео
        info_frame = ctk.CTkFrame(main_container)
        info_frame.pack(fill="x", padx=10, pady=10)
        
        self.info_text = ctk.CTkTextbox(
            info_frame,
            height=120,
            font=ctk.CTkFont(size=12),
            wrap="word"
        )
        self.info_text.pack(fill="both", expand=True, padx=10, pady=10)
        self.info_text.insert("1.0", "ℹ️ Информация о видео появится здесь после загрузки")
        self.info_text.configure(state="disabled")
        
        # Подсказка о поддерживаемых плеерах
        hint_label = ctk.CTkLabel(
            main_container,
            text="💡 Поддерживаемые плееры: VLC, MPV, QuickTime, Windows Media Player",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        hint_label.pack(pady=5)
    
    def load_video(self, video_path: Path):
        """Загрузить видео для предпросмотра"""
        self.video_path = video_path
        
        # Обновить название
        self.video_name_label.configure(text=video_path.name)
        
        # Активировать кнопки
        self.play_button.configure(state="normal")
        self.quick_preview_button.configure(state="normal")
        self.folder_button.configure(state="normal")
        
        # Получить информацию о видео
        self._load_video_info()
    
    def _load_video_info(self):
        """Загрузить информацию о видео через ffprobe"""
        if not self.video_path:
            return
        
        try:
            # Получить метаданные через ffprobe
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v", "error",
                    "-show_entries", "format=duration,size,bit_rate:stream=width,height,codec_name,r_frame_rate",
                    "-of", "default=noprint_wrappers=1",
                    str(self.video_path)
                ],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Парсинг вывода
            info_lines = result.stdout.strip().split("\n")
            info_dict = {}
            for line in info_lines:
                if "=" in line:
                    key, value = line.split("=", 1)
                    info_dict[key] = value
            
            # Форматирование информации
            info_text = f"""📹 **Информация о видео**

📁 Файл: {self.video_path.name}
📏 Размер: {self._format_size(int(info_dict.get('size', 0)))}
⏱️ Длительность: {self._format_duration(float(info_dict.get('duration', 0)))}

🎥 Разрешение: {info_dict.get('width', 'N/A')}x{info_dict.get('height', 'N/A')}
🎞️ Кодек: {info_dict.get('codec_name', 'N/A')}
📊 Битрейт: {self._format_bitrate(int(info_dict.get('bit_rate', 0)))}
🎬 FPS: {self._format_fps(info_dict.get('r_frame_rate', 'N/A'))}

📍 Путь: {self.video_path.absolute()}
"""
            
            self.info_text.configure(state="normal")
            self.info_text.delete("1.0", "end")
            self.info_text.insert("1.0", info_text)
            self.info_text.configure(state="disabled")
            
        except subprocess.CalledProcessError as e:
            error_msg = f"Не удалось получить информацию о видео:\n{e.stderr}"
            self.info_text.configure(state="normal")
            self.info_text.delete("1.0", "end")
            self.info_text.insert("1.0", f"❌ {error_msg}")
            self.info_text.configure(state="disabled")
            
            if self.on_preview_error:
                self.on_preview_error(error_msg)
        
        except FileNotFoundError:
            error_msg = "ffprobe не найден. Установите FFmpeg для просмотра информации о видео."
            self.info_text.configure(state="normal")
            self.info_text.delete("1.0", "end")
            self.info_text.insert("1.0", f"⚠️ {error_msg}")
            self.info_text.configure(state="disabled")
    
    def _play_video(self):
        """Открыть видео в системном плеере"""
        if not self.video_path:
            return
        
        try:
            system = platform.system()
            
            if system == "Darwin":  # macOS
                subprocess.run(["open", str(self.video_path)], check=True)
            elif system == "Windows":
                subprocess.run(["start", str(self.video_path)], shell=True, check=True)
            else:  # Linux
                # Пробуем разные плееры
                players = ["xdg-open", "vlc", "mpv", "mplayer"]
                for player in players:
                    try:
                        subprocess.run([player, str(self.video_path)], check=True)
                        return
                    except FileNotFoundError:
                        continue
                
                raise FileNotFoundError("Не найден видеоплеер. Установите VLC или MPV.")
        
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть видео:\n{e}")
            if self.on_preview_error:
                self.on_preview_error(str(e))
    
    def _quick_preview(self):
        """Быстрый просмотр (первые 30 секунд)"""
        if not self.video_path:
            return
        
        try:
            # Создаем временный файл с первыми 30 секундами
            temp_output = self.video_path.parent / f"{self.video_path.stem}_preview_30s.mp4"
            
            # Используем ffmpeg для создания превью
            subprocess.run(
                [
                    "ffmpeg",
                    "-i", str(self.video_path),
                    "-t", "30",
                    "-c", "copy",
                    "-y",
                    str(temp_output)
                ],
                capture_output=True,
                check=True
            )
            
            # Открываем превью
            system = platform.system()
            
            if system == "Darwin":  # macOS
                subprocess.run(["open", str(temp_output)], check=True)
            elif system == "Windows":
                subprocess.run(["start", str(temp_output)], shell=True, check=True)
            else:  # Linux
                players = ["xdg-open", "vlc", "mpv"]
                for player in players:
                    try:
                        subprocess.run([player, str(temp_output)], check=True)
                        return
                    except FileNotFoundError:
                        continue
        
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Ошибка", f"Не удалось создать превью:\n{e.stderr}")
            if self.on_preview_error:
                self.on_preview_error(str(e))
        
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть превью:\n{e}")
            if self.on_preview_error:
                self.on_preview_error(str(e))
    
    def _open_folder(self):
        """Открыть папку с видео"""
        if not self.video_path:
            return
        
        try:
            folder = self.video_path.parent
            system = platform.system()
            
            if system == "Darwin":  # macOS
                subprocess.run(["open", str(folder)], check=True)
            elif system == "Windows":
                subprocess.run(["explorer", str(folder)], check=True)
            else:  # Linux
                subprocess.run(["xdg-open", str(folder)], check=True)
        
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть папку:\n{e}")
            if self.on_preview_error:
                self.on_preview_error(str(e))
    
    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Форматировать размер файла"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    @staticmethod
    def _format_duration(seconds: float) -> str:
        """Форматировать длительность"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes}:{secs:02d}"
    
    @staticmethod
    def _format_bitrate(bitrate: int) -> str:
        """Форматировать битрейт"""
        if bitrate == 0:
            return "N/A"
        
        if bitrate >= 1_000_000:
            return f"{bitrate / 1_000_000:.1f} Mbps"
        else:
            return f"{bitrate / 1000:.0f} kbps"
    
    @staticmethod
    def _format_fps(fps_str: str) -> str:
        """Форматировать FPS"""
        if "/" in fps_str:
            try:
                num, den = map(int, fps_str.split("/"))
                return f"{num / den:.2f} fps"
            except:
                return fps_str
        return fps_str
