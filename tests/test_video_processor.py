#!/usr/bin/env python3
"""
Unit-тесты для VideoProcessor.
"""

import pytest
import tempfile
import shutil
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json

from src.processors.video_processor import VideoProcessor, VideoInfo
from src.core.artifacts import ArtifactsManager


@pytest.fixture
def temp_project_dir():
    """Временная директория проекта."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def artifacts(temp_project_dir):
    """Менеджер артефактов для тестов."""
    return ArtifactsManager(temp_project_dir)


@pytest.fixture
def processor(artifacts):
    """VideoProcessor с моком ffmpeg."""
    with patch('subprocess.run') as mock_run:
        # Мок для проверки ffmpeg
        mock_run.return_value = Mock(returncode=0, stdout="ffmpeg version 4.4.2", stderr="")
        proc = VideoProcessor(artifacts)
    return proc


@pytest.fixture
def mock_ffmpeg(artifacts):
    """Универсальный мок ffmpeg, который создаёт выходные файлы."""
    def create_output_file(*args, **kwargs):
        """Создаёт пустой выходной файл на основе команды ffmpeg."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_result.stdout = ""
        
        # Извлекаем имя выходного файла из команды
        cmd = args[0] if args else kwargs.get("cmd", [])
        for i, arg in enumerate(cmd):
            if i > 0 and not arg.startswith("-") and (cmd[i-1] not in ["-i", "-f", "-c", "-filter_complex", "-map"]):
                # Это вероятно выходной файл
                output_path = Path(arg)
                output_path.touch()
                break
        
        return mock_result
    
    return create_output_file


class TestVideoProcessor:
    """Тесты VideoProcessor."""
    
    def test_init(self, artifacts):
        """Тест инициализации."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)
            proc = VideoProcessor(artifacts)
            assert proc.artifacts == artifacts
            mock_run.assert_called_once()
    
    def test_init_no_ffmpeg(self, artifacts):
        """Тест ошибки при отсутствии ffmpeg."""
        with patch('subprocess.run', side_effect=FileNotFoundError()):
            with pytest.raises(RuntimeError, match="ffmpeg не найден"):
                VideoProcessor(artifacts)
    
    def test_get_video_info(self, processor):
        """Тест получения информации о видео."""
        mock_output = json.dumps({
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 1920,
                    "height": 1080,
                    "r_frame_rate": "30/1"
                },
                {
                    "codec_type": "audio",
                    "codec_name": "aac"
                }
            ],
            "format": {
                "duration": "120.5"
            }
        })
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=mock_output, stderr="")
            info = processor.get_video_info("test.mp4")
        
        assert info.duration == 120.5
        assert info.width == 1920
        assert info.height == 1080
        assert info.codec == "h264"
        assert info.fps == 30.0
        assert info.has_audio is True
    
    def test_concat_videos(self, processor, artifacts):
        """Тест склейки видео."""
        videos = ["video1.mp4", "video2.mp4", "video3.mp4"]
        
        def mock_popen_side_effect(*args, **kwargs):
            """Создаём пустой файл после 'запуска' ffmpeg."""
            mock_process = Mock()
            mock_process.communicate.return_value = ("", "")
            mock_process.returncode = 0
            # Создаём пустой файл merged.mp4
            temp_file = artifacts.project_dir / "merged.mp4"
            temp_file.touch()
            return mock_process
        
        with patch('subprocess.Popen', side_effect=mock_popen_side_effect):
            with patch.object(artifacts, 'save_artifact') as mock_save:
                mock_save.return_value = artifacts.folders["video"] / "merged.mp4"
                result = processor.concat_videos(videos, "merged")
        
        # Проверяем, что файл создан
        assert "merged.mp4" in result
        
        # Проверяем, что save_artifact был вызван
        assert mock_save.called
    
    def test_concat_videos_empty(self, processor):
        """Тест ошибки при пустом списке."""
        with pytest.raises(ValueError, match="Список видео пуст"):
            processor.concat_videos([])
    
    def test_trim_video(self, processor, artifacts):
        """Тест обрезки видео."""
        def mock_run_side_effect(*args, **kwargs):
            # Создаём пустой файл
            temp_file = artifacts.project_dir / "trimmed.mp4"
            temp_file.touch()
            return Mock(returncode=0, stderr="")
        
        with patch('subprocess.run', side_effect=mock_run_side_effect):
            with patch.object(artifacts, 'save_artifact') as mock_save:
                mock_save.return_value = artifacts.folders["video"] / "trimmed.mp4"
                result = processor.trim_video("input.mp4", 10.0, 30.0, "trimmed")
        
        assert "trimmed.mp4" in result
        assert mock_save.called
    
    def test_trim_video_invalid_time(self, processor):
        """Тест ошибки при некорректном времени."""
        with pytest.raises(ValueError, match="start_time должен быть меньше end_time"):
            processor.trim_video("input.mp4", 30.0, 10.0)
    
    def test_extract_audio(self, processor, artifacts):
        """Тест извлечения аудио."""
        def mock_run_side_effect(*args, **kwargs):
            temp_file = artifacts.project_dir / "audio.mp3"
            temp_file.touch()
            return Mock(returncode=0, stderr="")
        
        with patch('subprocess.run', side_effect=mock_run_side_effect):
            with patch.object(artifacts, 'save_artifact') as mock_save:
                mock_save.return_value = artifacts.folders["audio"] / "audio.mp3"
                result = processor.extract_audio("video.mp4", "audio", format="mp3", bitrate="192k")
        
        assert "audio.mp3" in result
        assert mock_save.called
    
    def test_overlay_video(self, processor, artifacts):
        """Тест оверлея видео."""
        def mock_run_side_effect(*args, **kwargs):
            temp_file = artifacts.project_dir / "overlay_result.mp4"
            temp_file.touch()
            return Mock(returncode=0, stderr="")
        
        with patch('subprocess.run', side_effect=mock_run_side_effect):
            with patch.object(artifacts, 'save_artifact') as mock_save:
                mock_save.return_value = artifacts.folders["video"] / "overlay_result.mp4"
                result = processor.overlay_video(
                    "base.mp4",
                    "overlay.mp4",
                    position=(100, 100),
                    size=(640, 360),
                    opacity=0.8,
                    output_name="overlay_result"
                )
        
        assert "overlay_result.mp4" in result
        assert mock_save.called
    
    def test_overlay_audio(self, processor, artifacts):
        """Тест микширования аудио."""
        def mock_run_side_effect(*args, **kwargs):
            temp_file = artifacts.project_dir / "mixed.mp3"
            temp_file.touch()
            return Mock(returncode=0, stderr="")
        
        with patch('subprocess.run', side_effect=mock_run_side_effect):
            with patch.object(artifacts, 'save_artifact') as mock_save:
                mock_save.return_value = artifacts.folders["audio"] / "mixed.mp3"
                result = processor.overlay_audio(
                    "base.mp3",
                    "overlay.mp3",
                    overlay_volume=0.5,
                    output_name="mixed"
                )
        
        assert "mixed.mp3" in result
        assert mock_save.called
    
    def test_merge_video_audio(self, processor, artifacts):
        """Тест объединения видео и аудио."""
        def mock_run_side_effect(*args, **kwargs):
            temp_file = artifacts.project_dir / "final.mp4"
            temp_file.touch()
            return Mock(returncode=0, stderr="")
        
        with patch('subprocess.run', side_effect=mock_run_side_effect):
            with patch.object(artifacts, 'save_artifact') as mock_save:
                mock_save.return_value = artifacts.folders["video"] / "final.mp4"
                result = processor.merge_video_audio("video.mp4", "audio.mp3", "final")
        
        assert "final.mp4" in result
        assert mock_save.called
    
    def test_ffmpeg_error_handling(self, processor):
        """Тест обработки ошибок ffmpeg."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=1, stderr="FFmpeg error")
            
            with pytest.raises(RuntimeError, match="Ошибка обрезки"):
                processor.trim_video("input.mp4", 0, 10)


# Integration tests (требуют реального ffmpeg)
@pytest.mark.integration
class TestVideoProcessorIntegration:
    """Интеграционные тесты с реальным ffmpeg."""
    
    @pytest.fixture
    def sample_video(self, temp_project_dir):
        """Создание тестового видео через ffmpeg."""
        video_path = Path(temp_project_dir) / "test_video.mp4"
        
        # Генерация 5-секундного видео (цветная полоса + тишина)
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "testsrc=duration=5:size=1280x720:rate=30",
            "-f", "lavfi", "-i", "anullsrc=duration=5",
            "-c:v", "libx264", "-c:a", "aac",
            str(video_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            pytest.skip("Не удалось создать тестовое видео")
        
        yield str(video_path)
        video_path.unlink()
    
    def test_real_video_info(self, processor, sample_video):
        """Тест получения реальной информации о видео."""
        info = processor.get_video_info(sample_video)
        
        assert info.width == 1280
        assert info.height == 720
        assert info.fps == 30.0
        assert info.has_audio is True
        assert 4.9 <= info.duration <= 5.1  # ~5 секунд
    
    def test_real_trim(self, processor, sample_video):
        """Тест реальной обрезки видео."""
        result = processor.trim_video(sample_video, 1.0, 3.0, "trimmed_real")
        
        assert Path(result).exists()
        
        # Проверяем длительность
        info = processor.get_video_info(result)
        assert 1.9 <= info.duration <= 2.1  # ~2 секунды
    
    def test_real_extract_audio(self, processor, sample_video):
        """Тест реального извлечения аудио."""
        result = processor.extract_audio(sample_video, "audio_real")
        
        assert Path(result).exists()
        assert result.endswith(".mp3")
