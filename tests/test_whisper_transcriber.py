"""
Unit tests for WhisperTranscriber
"""

import pytest
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Mock whisper module before importing WhisperTranscriber
sys.modules['whisper'] = MagicMock()

from src.processors.whisper_transcriber import WhisperTranscriber


class TestWhisperTranscriber:
    """Test WhisperTranscriber class."""
    
    def test_init_default(self):
        """Test initialization with defaults."""
        transcriber = WhisperTranscriber()
        assert transcriber.model_name == "base"
        assert transcriber.models_dir == Path.home() / ".cache" / "whisper"
        assert transcriber.progress_callback is None
    
    def test_init_custom_model(self):
        """Test initialization with custom model."""
        transcriber = WhisperTranscriber(model="small")
        assert transcriber.model_name == "small"
    
    def test_init_invalid_model(self):
        """Test initialization with invalid model raises error."""
        with pytest.raises(ValueError, match="Invalid model"):
            WhisperTranscriber(model="invalid")
    
    def test_init_custom_models_dir(self):
        """Test initialization with custom models directory."""
        custom_dir = Path("/tmp/custom_models")
        transcriber = WhisperTranscriber(models_dir=custom_dir)
        assert transcriber.models_dir == custom_dir
    
    def test_init_with_callback(self):
        """Test initialization with progress callback."""
        callback = Mock()
        transcriber = WhisperTranscriber(progress_callback=callback)
        assert transcriber.progress_callback == callback
    
    def test_get_model_info(self):
        """Test get_model_info returns correct structure."""
        transcriber = WhisperTranscriber(model="tiny")
        info = transcriber.get_model_info()
        
        assert info["name"] == "tiny"
        assert info["size_mb"] == 39
        assert info["ram_gb"] == 1
        assert info["speed"] == "fastest"
        assert info["quality"] == "basic"
        assert "available" in info
        assert "models_dir" in info
    
    def test_models_structure(self):
        """Test MODELS constant has all required fields."""
        for model_name, info in WhisperTranscriber.MODELS.items():
            assert "size_mb" in info
            assert "ram_gb" in info
            assert "speed" in info
            assert "quality" in info
    
    def test_is_model_available_true(self):
        """Test is_model_available returns True when model exists."""
        with patch('whisper.load_model') as mock_load:
            mock_load.return_value = MagicMock()
            
            transcriber = WhisperTranscriber()
            assert transcriber.is_model_available() is True
            mock_load.assert_called_once()
    
    def test_is_model_available_false(self):
        """Test is_model_available returns False when model not found."""
        with patch('whisper.load_model', side_effect=Exception("Model not found")):
            transcriber = WhisperTranscriber()
            assert transcriber.is_model_available() is False
    
    def test_download_model_success(self):
        """Test download_model downloads and loads model."""
        with patch('whisper.load_model') as mock_load:
            mock_model = MagicMock()
            # First call (is_model_available check) raises exception
            # Second call (actual download) succeeds
            mock_load.side_effect = [Exception("Not found"), mock_model]
            callback = Mock()
            
            transcriber = WhisperTranscriber(progress_callback=callback)
            result = transcriber.download_model()
            
            assert result is True
            assert transcriber._model == mock_model
            callback.assert_called()
    
    def test_download_model_already_available(self):
        """Test download_model skips if model already available."""
        with patch('whisper.load_model') as mock_load:
            mock_load.return_value = MagicMock()
            callback = Mock()
            
            transcriber = WhisperTranscriber(progress_callback=callback)
            result = transcriber.download_model()
            
            assert result is True
            callback.assert_called()
    
    def test_download_model_failure(self):
        """Test download_model handles errors."""
        with patch('whisper.load_model', side_effect=Exception("Download failed")):
            callback = Mock()
            
            transcriber = WhisperTranscriber(progress_callback=callback)
            result = transcriber.download_model()
            
            assert result is False
            callback.assert_called()
    
    def test_transcribe_success(self, tmp_path):
        """Test transcription with mocked whisper."""
        # Create fake video file
        video_path = tmp_path / "test_video.mp4"
        video_path.write_text("fake video")
        
        # Mock whisper
        mock_model = MagicMock()
        mock_model.transcribe = Mock(return_value={
            "text": "Hello world",
            "language": "en",
            "segments": [
                {"start": 0.0, "end": 1.5, "text": "Hello world"}
            ]
        })
        
        callback = Mock()
        transcriber = WhisperTranscriber(progress_callback=callback)
        transcriber._model = mock_model
        
        result = transcriber.transcribe(str(video_path))
        
        assert result is not None
        assert result["text"] == "Hello world"
        assert result["language"] == "en"
        assert result["model"] == "base"
        assert len(result["segments"]) == 1
        mock_model.transcribe.assert_called_once()
    
    def test_transcribe_with_output_file(self, tmp_path):
        """Test transcription saves to file."""
        video_path = tmp_path / "test_video.mp4"
        video_path.write_text("fake video")
        output_path = tmp_path / "transcription.txt"
        
        mock_model = MagicMock()
        mock_model.transcribe = Mock(return_value={
            "text": "Test transcription",
            "language": "en",
            "segments": []
        })
        
        transcriber = WhisperTranscriber()
        transcriber._model = mock_model
        
        result = transcriber.transcribe(str(video_path), output_path=str(output_path))
        
        assert result is not None
        assert output_path.exists()
        assert output_path.read_text() == "Test transcription"
    
    def test_transcribe_file_not_found(self):
        """Test transcription raises error for missing file."""
        transcriber = WhisperTranscriber()
        
        with pytest.raises(FileNotFoundError):
            transcriber.transcribe("/nonexistent/video.mp4")
    
    def test_transcribe_with_language(self, tmp_path):
        """Test transcription with specific language."""
        video_path = tmp_path / "test_video.mp4"
        video_path.write_text("fake video")
        
        mock_model = MagicMock()
        mock_model.transcribe = Mock(return_value={
            "text": "Привет мир",
            "language": "ru",
            "segments": []
        })
        
        transcriber = WhisperTranscriber()
        transcriber._model = mock_model
        
        result = transcriber.transcribe(str(video_path), language="ru")
        
        assert result is not None
        mock_model.transcribe.assert_called_once()
        call_kwargs = mock_model.transcribe.call_args[1]
        assert call_kwargs["language"] == "ru"
    
    def test_format_timestamps(self):
        """Test timestamp formatting."""
        transcriber = WhisperTranscriber()
        segments = [
            {"start": 0.0, "end": 2.5, "text": "First segment"},
            {"start": 2.5, "end": 5.0, "text": " Second segment"}
        ]
        
        formatted = transcriber.format_timestamps(segments)
        
        assert "[00:00:00 -> 00:00:02] First segment" in formatted
        assert "[00:00:02 -> 00:00:05] Second segment" in formatted
    
    def test_format_time(self):
        """Test time formatting helper."""
        assert WhisperTranscriber._format_time(0) == "00:00:00"
        assert WhisperTranscriber._format_time(61) == "00:01:01"
        assert WhisperTranscriber._format_time(3661) == "01:01:01"
        assert WhisperTranscriber._format_time(7325) == "02:02:05"


# Integration tests (require actual Whisper installation)
# Uncomment to run with real Whisper models

# @pytest.mark.integration
# def test_real_download_tiny(tmp_path):
#     """Test downloading tiny model (fastest)."""
#     transcriber = WhisperTranscriber(model="tiny", models_dir=tmp_path)
#     assert transcriber.download_model() is True

# @pytest.mark.integration
# def test_real_transcribe(tmp_path):
#     """Test real transcription (requires test audio file)."""
#     # Create or use real audio file
#     video_path = "path/to/test/audio.wav"
#     if not os.path.exists(video_path):
#         pytest.skip("Test audio file not available")
#     
#     transcriber = WhisperTranscriber(model="tiny")
#     result = transcriber.transcribe(video_path)
#     
#     assert result is not None
#     assert "text" in result
#     assert len(result["text"]) > 0
