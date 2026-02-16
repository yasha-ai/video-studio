#!/usr/bin/env python3
"""
Video Processor — обработка видео через ffmpeg.

Основные функции:
- Склейка видео (intro + main + outro)
- Нарезка видео (trim)
- Отделение звука от видео
- Оверлей видео поверх основного
- Оверлей аудио с регулировкой громкости
"""

import os
import subprocess
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any
from dataclasses import dataclass

from src.core.artifacts import ArtifactsManager


@dataclass
class VideoInfo:
    """Информация о видеофайле."""
    duration: float  # Длительность в секундах
    width: int
    height: int
    codec: str
    fps: float
    has_audio: bool


class VideoProcessor:
    """Обработчик видео на базе ffmpeg."""
    
    def __init__(self, artifacts: ArtifactsManager):
        """
        Args:
            artifacts: Менеджер артефактов проекта
        """
        self.artifacts = artifacts
        self._check_ffmpeg()
    
    def _check_ffmpeg(self):
        """Проверка наличия ffmpeg."""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                raise RuntimeError("ffmpeg не установлен или не доступен")
        except FileNotFoundError:
            raise RuntimeError(
                "ffmpeg не найден. Установите его: sudo apt install ffmpeg"
            )
    
    def get_video_info(self, video_path: str) -> VideoInfo:
        """Получить информацию о видеофайле через ffprobe.
        
        Args:
            video_path: Путь к видеофайлу
            
        Returns:
            VideoInfo с параметрами видео
        """
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "stream=codec_name,width,height,r_frame_rate,duration",
            "-show_entries", "format=duration",
            "-of", "json",
            video_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Ошибка ffprobe: {result.stderr}")
        
        import json
        data = json.loads(result.stdout)
        
        # Извлечение данных
        video_stream = next(
            (s for s in data.get("streams", []) if s.get("codec_type") == "video"),
            None
        )
        audio_stream = next(
            (s for s in data.get("streams", []) if s.get("codec_type") == "audio"),
            None
        )
        
        if not video_stream:
            raise ValueError("Видеопоток не найден")
        
        duration = float(data["format"]["duration"])
        fps_str = video_stream.get("r_frame_rate", "30/1")
        num, den = map(int, fps_str.split("/"))
        fps = num / den if den != 0 else 30.0
        
        return VideoInfo(
            duration=duration,
            width=int(video_stream["width"]),
            height=int(video_stream["height"]),
            codec=video_stream["codec_name"],
            fps=fps,
            has_audio=audio_stream is not None
        )
    
    def concat_videos(
        self,
        videos: List[str],
        output_name: str = "merged_video",
        progress_callback: Optional[callable] = None
    ) -> str:
        """Склейка видео в одно.
        
        Args:
            videos: Список путей к видео для склейки
            output_name: Название выходного артефакта
            progress_callback: Колбэк для отслеживания прогресса
            
        Returns:
            Путь к склеенному видео
        """
        if not videos:
            raise ValueError("Список видео пуст")
        
        # Создаем временный файл со списком видео для concat
        concat_list = self.artifacts.project_dir / "concat_list.txt"
        with open(concat_list, "w") as f:
            for video in videos:
                f.write(f"file '{Path(video).absolute()}'\n")
        
        # Создаём файл во временной папке (потом save_artifact скопирует в нужную)
        temp_output = self.artifacts.project_dir / f"{output_name}.mp4"
        
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_list),
            "-c", "copy",
            str(temp_output)
        ]
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # TODO: Парсинг прогресса из stderr
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            raise RuntimeError(f"Ошибка склейки: {stderr}")
        
        # Сохраняем артефакт (определяем тип по имени или используем merged_video)
        artifact_type = output_name if output_name in self.artifacts.ARTIFACT_TYPES else "merged_video"
        saved_path = self.artifacts.save_artifact(
            artifact_type,
            temp_output,
            {"sources": videos, "method": "concat", "custom_name": output_name}
        )
        
        # Удаляем временные файлы
        concat_list.unlink()
        if temp_output != saved_path:
            temp_output.unlink()
        
        return str(saved_path)
    
    def trim_video(
        self,
        input_path: str,
        start_time: float,
        end_time: float,
        output_name: str = "trimmed_video",
        progress_callback: Optional[callable] = None
    ) -> str:
        """Обрезка видео по времени.
        
        Args:
            input_path: Путь к исходному видео
            start_time: Время начала (секунды)
            end_time: Время окончания (секунды)
            output_name: Название выходного артефакта
            progress_callback: Колбэк для прогресса
            
        Returns:
            Путь к обрезанному видео
        """
        if start_time >= end_time:
            raise ValueError("start_time должен быть меньше end_time")
        
        temp_output = self.artifacts.project_dir / f"{output_name}.mp4"
        duration = end_time - start_time
        
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start_time),
            "-i", input_path,
            "-t", str(duration),
            "-c", "copy",
            str(temp_output)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Ошибка обрезки: {result.stderr}")
        
        artifact_type = output_name if output_name in self.artifacts.ARTIFACT_TYPES else "merged_video"
        saved_path = self.artifacts.save_artifact(
            artifact_type,
            temp_output,
            {
                "source": input_path,
                "start_time": start_time,
                "end_time": end_time,
                "duration": duration,
                "custom_name": output_name
            }
        )
        
        if temp_output != saved_path:
            temp_output.unlink()
        
        return str(saved_path)
    
    def extract_audio(
        self,
        video_path: str,
        output_name: str = "original_audio",
        format: str = "mp3",
        bitrate: str = "192k"
    ) -> str:
        """Извлечение аудио из видео.
        
        Args:
            video_path: Путь к видео
            output_name: Название артефакта
            format: Формат аудио (mp3, wav, aac)
            bitrate: Битрейт (например, 192k)
            
        Returns:
            Путь к извлеченному аудио
        """
        temp_output = self.artifacts.project_dir / f"{output_name}.{format}"
        
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vn",  # Без видео
            "-acodec", "libmp3lame" if format == "mp3" else format,
            "-ab", bitrate,
            str(temp_output)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Ошибка извлечения аудио: {result.stderr}")
        
        artifact_type = output_name if output_name in self.artifacts.ARTIFACT_TYPES else "original_audio"
        saved_path = self.artifacts.save_artifact(
            artifact_type,
            temp_output,
            {"source": video_path, "format": format, "bitrate": bitrate, "custom_name": output_name}
        )
        
        if temp_output != saved_path:
            temp_output.unlink()
        
        return str(saved_path)
    
    def overlay_video(
        self,
        base_video: str,
        overlay_video: str,
        position: Tuple[int, int] = (10, 10),
        size: Optional[Tuple[int, int]] = None,
        opacity: float = 1.0,
        output_name: str = "overlay_video"
    ) -> str:
        """Наложение видео поверх основного.
        
        Args:
            base_video: Путь к основному видео
            overlay_video: Путь к оверлейному видео
            position: Позиция (x, y) в пикселях
            size: Размер оверлея (width, height). None = оригинальный размер
            opacity: Прозрачность (0.0-1.0)
            output_name: Название артефакта
            
        Returns:
            Путь к видео с оверлеем
        """
        temp_output = self.artifacts.project_dir / f"{output_name}.mp4"
        x, y = position
        
        # Строим filter
        filters = []
        
        # Масштабирование оверлея
        if size:
            w, h = size
            filters.append(f"[1:v]scale={w}:{h}[ovr]")
            overlay_input = "[ovr]"
        else:
            overlay_input = "[1:v]"
        
        # Opacity (если не 1.0)
        if opacity < 1.0:
            filters.append(f"{overlay_input}format=rgba,colorchannelmixer=aa={opacity}[ovr_alpha]")
            overlay_input = "[ovr_alpha]"
        
        # Overlay
        filters.append(f"[0:v]{overlay_input}overlay={x}:{y}")
        
        filter_complex = ";".join(filters)
        
        cmd = [
            "ffmpeg", "-y",
            "-i", base_video,
            "-i", overlay_video,
            "-filter_complex", filter_complex,
            "-c:a", "copy",
            str(temp_output)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Ошибка оверлея видео: {result.stderr}")
        
        artifact_type = output_name if output_name in self.artifacts.ARTIFACT_TYPES else "merged_video"
        saved_path = self.artifacts.save_artifact(
            artifact_type,
            temp_output,
            {
                "base": base_video,
                "overlay": overlay_video,
                "position": position,
                "size": size,
                "opacity": opacity,
                "custom_name": output_name
            }
        )
        
        if temp_output != saved_path:
            temp_output.unlink()
        
        return str(saved_path)
    
    def overlay_audio(
        self,
        base_audio: str,
        overlay_audio: str,
        overlay_volume: float = 1.0,
        output_name: str = "mixed_audio",
        format: str = "mp3"
    ) -> str:
        """Микширование аудио (наложение одного на другое).
        
        Args:
            base_audio: Основное аудио
            overlay_audio: Накладываемое аудио
            overlay_volume: Громкость наложенного аудио (0.0-1.0)
            output_name: Название артефакта
            format: Формат выходного аудио
            
        Returns:
            Путь к смикшированному аудио
        """
        temp_output = self.artifacts.project_dir / f"{output_name}.{format}"
        
        filter_complex = f"[1:a]volume={overlay_volume}[a1];[0:a][a1]amix=inputs=2:duration=longest"
        
        cmd = [
            "ffmpeg", "-y",
            "-i", base_audio,
            "-i", overlay_audio,
            "-filter_complex", filter_complex,
            "-c:a", "libmp3lame" if format == "mp3" else format,
            str(temp_output)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Ошибка микширования аудио: {result.stderr}")
        
        artifact_type = output_name if output_name in self.artifacts.ARTIFACT_TYPES else "final_audio"
        saved_path = self.artifacts.save_artifact(
            artifact_type,
            temp_output,
            {
                "base": base_audio,
                "overlay": overlay_audio,
                "overlay_volume": overlay_volume,
                "custom_name": output_name
            }
        )
        
        if temp_output != saved_path:
            temp_output.unlink()
        
        return str(saved_path)
    
    def merge_video_audio(
        self,
        video_path: str,
        audio_path: str,
        output_name: str = "final_video"
    ) -> str:
        """Объединение видео и аудио.
        
        Args:
            video_path: Путь к видео (без звука или с заменяемым звуком)
            audio_path: Путь к аудио
            output_name: Название артефакта
            
        Returns:
            Путь к итоговому видео
        """
        temp_output = self.artifacts.project_dir / f"{output_name}.mp4"
        
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-map", "0:v:0",
            "-map", "1:a:0",
            str(temp_output)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Ошибка слияния видео и аудио: {result.stderr}")
        
        artifact_type = output_name if output_name in self.artifacts.ARTIFACT_TYPES else "final_video"
        saved_path = self.artifacts.save_artifact(
            artifact_type,
            temp_output,
            {"video": video_path, "audio": audio_path, "custom_name": output_name}
        )
        
        if temp_output != saved_path:
            temp_output.unlink()
        
        return str(saved_path)


# CLI для тестирования
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Video Processor CLI")
    parser.add_argument("--project", required=True, help="Папка проекта")
    parser.add_argument("--action", required=True, 
                        choices=["concat", "trim", "extract_audio", "overlay_video", "overlay_audio", "merge"],
                        help="Действие")
    parser.add_argument("--input", help="Входное видео/аудио")
    parser.add_argument("--inputs", nargs="+", help="Список видео для concat")
    parser.add_argument("--overlay", help="Оверлейное видео/аудио")
    parser.add_argument("--audio", help="Аудио для merge")
    parser.add_argument("--start", type=float, help="Время начала (trim)")
    parser.add_argument("--end", type=float, help="Время окончания (trim)")
    parser.add_argument("--output", default="output", help="Имя выходного файла")
    
    args = parser.parse_args()
    
    # Создание проекта и процессора
    artifacts = ArtifactsManager(args.project)
    processor = VideoProcessor(artifacts)
    
    # Выполнение действия
    if args.action == "concat":
        if not args.inputs:
            parser.error("--inputs required for concat")
        result = processor.concat_videos(args.inputs, args.output)
        print(f"✅ Склейка завершена: {result}")
    
    elif args.action == "trim":
        if not all([args.input, args.start is not None, args.end is not None]):
            parser.error("--input, --start, --end required for trim")
        result = processor.trim_video(args.input, args.start, args.end, args.output)
        print(f"✅ Обрезка завершена: {result}")
    
    elif args.action == "extract_audio":
        if not args.input:
            parser.error("--input required for extract_audio")
        result = processor.extract_audio(args.input, args.output)
        print(f"✅ Аудио извлечено: {result}")
    
    elif args.action == "merge":
        if not all([args.input, args.audio]):
            parser.error("--input and --audio required for merge")
        result = processor.merge_video_audio(args.input, args.audio, args.output)
        print(f"✅ Видео и аудио объединены: {result}")
    
    else:
        print(f"❌ Действие {args.action} пока не реализовано в CLI")
