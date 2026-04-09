#!/usr/bin/env python3
"""
Video Processor — обработка видео через ffmpeg.

Основные функции:
- Склейка видео (intro + main + outro)
- Нарезка видео (trim)
- Отделение звука от видео
- Оверлей видео поверх основного
- Оверлей аудио с регулировкой громкости
- Subscribe overlay с хромакеем
- Восстановление оригинального аудио
- Микширование аудио оверлея
"""

import json
import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any, Callable
from dataclasses import dataclass

from src.core.artifacts import ArtifactsManager

try:
    from config.settings import Settings
except ImportError:
    Settings = None

logger = logging.getLogger(__name__)


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
        self.ffmpeg = Settings.get_ffmpeg() if Settings else "ffmpeg"
        self.ffprobe = Settings.get_ffprobe() if Settings else "ffprobe"
        self._check_ffmpeg()

    def _check_ffmpeg(self):
        """Проверка наличия ffmpeg."""
        try:
            result = subprocess.run(
                [self.ffmpeg, "-version"],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                raise RuntimeError("FFmpeg not installed or not accessible")
        except FileNotFoundError:
            raise RuntimeError(
                "FFmpeg not found. Install it (brew install ffmpeg / apt install ffmpeg) "
                "or set FFMPEG_PATH in Settings."
            )

    def _has_audio_stream(self, video_path: str) -> bool:
        """Check if a video file contains an audio stream using ffprobe.

        Args:
            video_path: Path to the video file

        Returns:
            True if the file has at least one audio stream, False otherwise
        """
        cmd = [
            self.ffprobe,
            "-v", "error",
            "-select_streams", "a",
            "-show_entries", "stream=codec_type",
            "-of", "json",
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return False
        try:
            data = json.loads(result.stdout)
            return len(data.get("streams", [])) > 0
        except (json.JSONDecodeError, KeyError):
            return False

    def _get_duration(self, video_path: str) -> float:
        """Get duration of a media file in seconds.

        Args:
            video_path: Path to the media file

        Returns:
            Duration in seconds
        """
        cmd = [
            self.ffprobe,
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "json",
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffprobe error: {result.stderr}")
        data = json.loads(result.stdout)
        return float(data["format"]["duration"])

    def _run_ffmpeg(
        self,
        cmd: List[str],
        total_duration: float = 0,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> str:
        """Run ffmpeg command with optional progress parsing.

        Args:
            cmd: ffmpeg command as list
            total_duration: Expected output duration (seconds) for progress calc
            progress_callback: callback(progress_0_to_100, status_message)

        Returns:
            stderr output

        Raises:
            RuntimeError: if ffmpeg exits with error
        """
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        if progress_callback and total_duration > 0:
            # Read stderr line-by-line to parse progress
            stderr_lines = []
            time_re = re.compile(r"time=(\d+):(\d+):(\d+)\.(\d+)")
            for line in process.stderr:
                stderr_lines.append(line)
                m = time_re.search(line)
                if m:
                    h, mn, s, ms = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
                    current = h * 3600 + mn * 60 + s + ms / 100
                    pct = min(100.0, (current / total_duration) * 100)
                    progress_callback(pct, f"Обработка... {pct:.0f}%")
            process.wait()
            stderr = "".join(stderr_lines)
            if progress_callback:
                progress_callback(100, "Готово")
        else:
            _, stderr = process.communicate()

        if process.returncode != 0:
            raise RuntimeError(stderr)

        return stderr

    def get_video_info(self, video_path: str) -> VideoInfo:
        """Получить информацию о видеофайле через ffprobe.

        Args:
            video_path: Путь к видеофайлу

        Returns:
            VideoInfo с параметрами видео
        """
        cmd = [
            self.ffprobe,
            "-v", "error",
            "-show_entries", "stream=codec_name,codec_type,width,height,r_frame_rate,duration",
            "-show_entries", "format=duration",
            "-of", "json",
            video_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Ошибка ffprobe: {result.stderr}")

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

        Handles videos with different resolutions by using pillarbox/letterbox
        (black bars) to preserve original aspect ratios. Also handles videos
        that are missing audio tracks by generating silence.

        Args:
            videos: Список путей к видео для склейки
            output_name: Название выходного артефакта
            progress_callback: Колбэк для отслеживания прогресса

        Returns:
            Путь к склеенному видео
        """
        if not videos:
            raise ValueError("Список видео пуст")

        temp_output = self.artifacts.project_dir / f"{output_name}.mp4"

        # Check if all videos have same resolution/codec and audio presence
        infos = []
        total_dur = 0
        audio_flags = []
        for v in videos:
            try:
                info = self.get_video_info(v)
                infos.append(info)
                total_dur += info.duration
                audio_flags.append(self._has_audio_stream(v))
            except Exception:
                infos.append(None)
                audio_flags.append(False)

        # Determine if we can use fast copy or need re-encoding
        for i, (v, info) in enumerate(zip(videos, infos)):
            if info:
                logger.info(
                    f"Video {i+1}: {Path(v).name} — {info.width}x{info.height} "
                    f"{info.codec} {info.fps}fps audio={audio_flags[i]}"
                )

        can_copy = True
        all_have_audio = all(audio_flags)

        if len(infos) > 1:
            base = infos[0]
            for idx, info in enumerate(infos[1:], 1):
                if info is None or base is None:
                    can_copy = False
                    break
                if (info.width != base.width or info.height != base.height
                        or info.codec != base.codec):
                    can_copy = False
                    break

        # If any file lacks audio, we must re-encode to generate silence
        if not all_have_audio:
            can_copy = False

        if can_copy:
            logger.info("Using fast concat (stream copy) — all videos have matching params")
            # Fast concat with stream copy
            concat_list = self.artifacts.project_dir / "concat_list.txt"
            with open(concat_list, "w") as f:
                for video in videos:
                    f.write(f"file '{Path(video).absolute()}'\n")

            cmd = [
                self.ffmpeg, "-y",
                "-f", "concat", "-safe", "0",
                "-i", str(concat_list),
                "-c", "copy",
                str(temp_output)
            ]
        else:
            logger.info("Re-encoding required — videos have different resolution/codec or missing audio")
            # Re-encode to match — use main video (largest) as target resolution
            target = max((i for i in infos if i), key=lambda i: i.width * i.height)
            w, h = target.width, target.height
            fps = target.fps

            # Build inputs and filter_complex
            inputs = []
            filters = []
            input_idx = 0  # Track ffmpeg input index

            for i, video in enumerate(videos):
                has_audio = audio_flags[i]
                vid_duration = infos[i].duration if infos[i] else 0

                # Video input
                inputs.extend(["-i", video])
                vid_input_idx = input_idx
                input_idx += 1

                # Audio: either from file or generate silence
                if has_audio:
                    audio_input_idx = vid_input_idx  # same file
                else:
                    # Add anullsrc as a separate input for this file
                    inputs.extend([
                        "-f", "lavfi",
                        "-t", str(vid_duration),
                        "-i", f"anullsrc=channel_layout=stereo:sample_rate=48000"
                    ])
                    audio_input_idx = input_idx
                    input_idx += 1

                # Video filter: scale with aspect ratio preservation + pad with black bars
                filters.append(
                    f"[{vid_input_idx}:v]"
                    f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
                    f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black,"
                    f"fps={fps},setsar=1[v{i}]"
                )

                # Audio filter
                filters.append(
                    f"[{audio_input_idx}:a]aresample=48000[a{i}]"
                )

            concat_inputs = "".join(f"[v{i}][a{i}]" for i in range(len(videos)))
            filters.append(f"{concat_inputs}concat=n={len(videos)}:v=1:a=1[outv][outa]")

            cmd = [self.ffmpeg, "-y"] + inputs + [
                "-filter_complex", ";".join(filters),
                "-map", "[outv]", "-map", "[outa]",
                "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                "-c:a", "aac", "-b:a", "192k",
                str(temp_output)
            ]

        try:
            self._run_ffmpeg(cmd, total_dur, progress_callback)
        except RuntimeError as e:
            raise RuntimeError(f"Ошибка склейки: {e}")

        # Cleanup concat list if exists
        concat_list_path = self.artifacts.project_dir / "concat_list.txt"
        if concat_list_path.exists():
            concat_list_path.unlink()

        # Сохраняем артефакт (определяем тип по имени или используем merged_video)
        artifact_type = output_name if output_name in self.artifacts.ARTIFACT_TYPES else "merged_video"
        saved_path = self.artifacts.save_artifact(
            artifact_type,
            temp_output,
            {"sources": videos, "method": "concat", "custom_name": output_name}
        )

        # Удаляем временные файлы если они ещё существуют
        if temp_output.exists() and str(temp_output) != str(saved_path):
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
            self.ffmpeg, "-y",
            "-ss", str(start_time),
            "-i", input_path,
            "-t", str(duration),
            "-c", "copy",
            str(temp_output)
        ]

        try:
            self._run_ffmpeg(cmd, duration, progress_callback)
        except RuntimeError as e:
            raise RuntimeError(f"Ошибка обрезки: {e}")

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

        if temp_output.exists() and str(temp_output) != str(saved_path):
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
            self.ffmpeg, "-y",
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

        if temp_output.exists() and str(temp_output) != str(saved_path):
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
            self.ffmpeg, "-y",
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

        if temp_output.exists() and str(temp_output) != str(saved_path):
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
            self.ffmpeg, "-y",
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

        if temp_output.exists() and str(temp_output) != str(saved_path):
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
            self.ffmpeg, "-y",
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

        if temp_output.exists() and str(temp_output) != str(saved_path):
            temp_output.unlink()

        return str(saved_path)

    def apply_subscribe_overlay(
        self,
        base_video: str,
        overlay_video: str,
        output_name: str = "with_overlay",
        start_time: float = 120.0,
        position: str = "bottom-left",
        overlay_width: int = 576,
        chromakey_color: str = "0x00FF00",
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> str:
        """Apply a green-screen overlay (e.g. subscribe animation) onto the base video.

        Uses chromakey to remove the green background, trims the overlay to
        the first 10 seconds, and positions it at the given screen corner
        starting at *start_time* seconds into the base video.

        Args:
            base_video: Path to the main video
            overlay_video: Path to the overlay video (with green screen)
            output_name: Output artifact name
            start_time: When the overlay should appear (seconds)
            position: One of bottom-left, bottom-right, top-left, top-right
            overlay_width: Width to scale overlay to (-1 keeps aspect ratio)
            chromakey_color: Hex colour of the chroma key (default green)
            progress_callback: Optional progress callback

        Returns:
            Path to the resulting video file
        """
        temp_output = self.artifacts.project_dir / f"{output_name}.mp4"

        base_info = self.get_video_info(base_video)
        total_dur = base_info.duration

        # Position mapping
        pos_map = {
            "top-left": "20:20",
            "top-center": "(W-w)/2:20",
            "top-right": "W-w-20:20",
            "center-left": "20:(H-h)/2",
            "center": "(W-w)/2:(H-h)/2",
            "center-right": "W-w-20:(H-h)/2",
            "bottom-left": "20:H-h-20",
            "bottom-center": "(W-w)/2:H-h-20",
            "bottom-right": "W-w-20:H-h-20",
        }
        overlay_pos = pos_map.get(position, pos_map["bottom-left"])

        # Filter complex:
        # 1. Trim overlay to first 10s, remove green via chromakey
        # 2. Scale overlay
        # 3. Shift PTS so overlay appears at start_time
        # 4. Overlay onto base with eof_action=pass
        filter_complex = (
            f"[1:v]trim=0:10,setpts=PTS-STARTPTS,"
            f"chromakey={chromakey_color}:0.1:0.2,"
            f"scale={overlay_width}:-1,"
            f"setpts=PTS-STARTPTS+{start_time}/TB[ovr];"
            f"[0:v][ovr]overlay={overlay_pos}:eof_action=pass[outv]"
        )

        cmd = [
            self.ffmpeg, "-y",
            "-i", base_video,
            "-i", overlay_video,
            "-filter_complex", filter_complex,
            "-map", "[outv]",
            "-map", "0:a?",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-c:a", "copy",
            str(temp_output)
        ]

        try:
            self._run_ffmpeg(cmd, total_dur, progress_callback)
        except RuntimeError as e:
            raise RuntimeError(f"Ошибка наложения subscribe overlay: {e}")

        artifact_type = output_name if output_name in self.artifacts.ARTIFACT_TYPES else "merged_video"
        saved_path = self.artifacts.save_artifact(
            artifact_type,
            temp_output,
            {
                "base": base_video,
                "overlay": overlay_video,
                "start_time": start_time,
                "position": position,
                "overlay_width": overlay_width,
                "custom_name": output_name,
            }
        )

        if temp_output.exists() and str(temp_output) != str(saved_path):
            temp_output.unlink()

        return str(saved_path)

    def restore_original_audio(
        self,
        processed_video: str,
        original_sources: list,
        output_name: str = "final_video",
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> str:
        """Replace audio in processed_video with audio extracted from original sources.

        This is useful after re-encoding (e.g. concat with scaling) when you
        want to keep the higher-quality original audio tracks rather than the
        re-encoded ones.

        Args:
            processed_video: Path to the re-encoded video (video stream will be copied)
            original_sources: List of tuples [(path, has_audio), ...] in concat order
                              (e.g. intro, main, outro). For files without audio,
                              silence matching their duration is generated.
            output_name: Output artifact name
            progress_callback: Optional progress callback

        Returns:
            Path to the resulting video file
        """
        temp_output = self.artifacts.project_dir / f"{output_name}.mp4"

        video_dur = self._get_duration(processed_video)

        # Build inputs and audio filter chain
        inputs = ["-i", processed_video]  # input 0 = processed video
        audio_parts = []
        input_idx = 1  # 0 is the processed video

        for src_path, has_audio in original_sources:
            if has_audio:
                inputs.extend(["-i", src_path])
                audio_parts.append(f"[{input_idx}:a]aresample=48000[a{input_idx}]")
                input_idx += 1
            else:
                # Generate silence matching source duration
                src_dur = self._get_duration(src_path)
                inputs.extend([
                    "-f", "lavfi",
                    "-t", str(src_dur),
                    "-i", f"anullsrc=channel_layout=stereo:sample_rate=48000"
                ])
                audio_parts.append(f"[{input_idx}:a]aresample=48000[a{input_idx}]")
                input_idx += 1

        # Concat all audio parts
        n_parts = len(original_sources)
        if n_parts == 1:
            # Single source — just use it directly
            idx = 1  # first audio input after processed video
            filter_complex = f"[1:a]aresample=48000[outa]"
        else:
            concat_labels = "".join(f"[a{i}]" for i in range(1, 1 + n_parts))
            filter_parts = audio_parts + [
                f"{concat_labels}concat=n={n_parts}:v=0:a=1[outa]"
            ]
            filter_complex = ";".join(filter_parts)

        cmd = [self.ffmpeg, "-y"] + inputs + [
            "-filter_complex", filter_complex,
            "-map", "0:v",
            "-map", "[outa]",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "256k",
            str(temp_output)
        ]

        try:
            self._run_ffmpeg(cmd, video_dur, progress_callback)
        except RuntimeError as e:
            raise RuntimeError(f"Ошибка восстановления аудио: {e}")

        artifact_type = output_name if output_name in self.artifacts.ARTIFACT_TYPES else "final_video"
        saved_path = self.artifacts.save_artifact(
            artifact_type,
            temp_output,
            {
                "processed_video": processed_video,
                "original_sources": [(s, a) for s, a in original_sources],
                "custom_name": output_name,
            }
        )

        if temp_output.exists() and str(temp_output) != str(saved_path):
            temp_output.unlink()

        return str(saved_path)

    def mix_overlay_audio(
        self,
        video_path: str,
        overlay_audio_source: str,
        overlay_start_ms: int,
        output_name: str = "final_with_sound",
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> str:
        """Mix the first 10 seconds of overlay audio into the video at a given offset.

        Extracts the first 10s of audio from *overlay_audio_source*, delays it
        by *overlay_start_ms* milliseconds, and mixes it with the main video
        audio. The video stream is copied without re-encoding.

        Args:
            video_path: Path to the video (must have an audio track)
            overlay_audio_source: Path to overlay video/audio file
            overlay_start_ms: Delay in milliseconds before overlay audio starts
            output_name: Output artifact name
            progress_callback: Optional progress callback

        Returns:
            Path to the resulting video file
        """
        temp_output = self.artifacts.project_dir / f"{output_name}.mp4"

        video_dur = self._get_duration(video_path)

        # Filter:
        # [1:a] trim first 10s -> delay by overlay_start_ms -> mix with [0:a]
        filter_complex = (
            f"[1:a]atrim=0:10,asetpts=PTS-STARTPTS,"
            f"adelay={overlay_start_ms}|{overlay_start_ms}[delayed];"
            f"[0:a][delayed]amix=inputs=2:duration=longest[outa]"
        )

        cmd = [
            self.ffmpeg, "-y",
            "-i", video_path,
            "-i", overlay_audio_source,
            "-filter_complex", filter_complex,
            "-map", "0:v",
            "-map", "[outa]",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "256k",
            str(temp_output)
        ]

        try:
            self._run_ffmpeg(cmd, video_dur, progress_callback)
        except RuntimeError as e:
            raise RuntimeError(f"Ошибка микширования overlay audio: {e}")

        artifact_type = output_name if output_name in self.artifacts.ARTIFACT_TYPES else "final_video"
        saved_path = self.artifacts.save_artifact(
            artifact_type,
            temp_output,
            {
                "video": video_path,
                "overlay_audio_source": overlay_audio_source,
                "overlay_start_ms": overlay_start_ms,
                "custom_name": output_name,
            }
        )

        if temp_output.exists() and str(temp_output) != str(saved_path):
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
        print(f"Склейка завершена: {result}")

    elif args.action == "trim":
        if not all([args.input, args.start is not None, args.end is not None]):
            parser.error("--input, --start, --end required for trim")
        result = processor.trim_video(args.input, args.start, args.end, args.output)
        print(f"Обрезка завершена: {result}")

    elif args.action == "extract_audio":
        if not args.input:
            parser.error("--input required for extract_audio")
        result = processor.extract_audio(args.input, args.output)
        print(f"Аудио извлечено: {result}")

    elif args.action == "merge":
        if not all([args.input, args.audio]):
            parser.error("--input and --audio required for merge")
        result = processor.merge_video_audio(args.input, args.audio, args.output)
        print(f"Видео и аудио объединены: {result}")

    else:
        print(f"Действие {args.action} пока не реализовано в CLI")
