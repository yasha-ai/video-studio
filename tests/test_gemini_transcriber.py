"""
Unit tests for GeminiTranscriber
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import json
from src.processors.gemini_transcriber import GeminiTranscriber


class TestGeminiTranscriber(unittest.TestCase):
    """Test cases for GeminiTranscriber."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.api_key = "test_api_key_123"
        self.mock_audio = Path("/tmp/test_audio.mp3")
    
    @patch("src.processors.gemini_transcriber.genai")
    def test_init_with_api_key(self, mock_genai):
        """Test initialization with API key."""
        transcriber = GeminiTranscriber(api_key=self.api_key)
        
        self.assertEqual(transcriber.api_key, self.api_key)
        self.assertEqual(transcriber.model_name, "gemini-2.5-flash")
        mock_genai.configure.assert_called_once_with(api_key=self.api_key)
    
    @patch.dict("os.environ", {"GOOGLE_GEMINI_API_KEY": "env_api_key"})
    @patch("src.processors.gemini_transcriber.genai")
    def test_init_from_env(self, mock_genai):
        """Test initialization from environment variable."""
        transcriber = GeminiTranscriber()
        
        self.assertEqual(transcriber.api_key, "env_api_key")
        mock_genai.configure.assert_called_once_with(api_key="env_api_key")
    
    @patch.dict("os.environ", {}, clear=True)
    def test_init_no_api_key_raises(self):
        """Test initialization without API key raises ValueError."""
        with self.assertRaises(ValueError) as cm:
            GeminiTranscriber()
        
        self.assertIn("API key required", str(cm.exception))
    
    @patch("src.processors.gemini_transcriber.genai")
    def test_transcribe_success(self, mock_genai):
        """Test successful transcription."""
        # Mock uploaded file
        mock_uploaded_file = MagicMock()
        mock_uploaded_file.name = "test_file"
        mock_uploaded_file.state.name = "ACTIVE"
        mock_genai.upload_file.return_value = mock_uploaded_file
        mock_genai.get_file.return_value = mock_uploaded_file
        
        # Mock model response
        mock_response = Mock()
        mock_response.text = "This is a test transcription."
        
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        
        transcriber = GeminiTranscriber(api_key=self.api_key)
        
        # Mock file existence
        with patch.object(Path, "exists", return_value=True):
            result = transcriber.transcribe(self.mock_audio)
        
        self.assertEqual(result, "This is a test transcription.")
        mock_genai.upload_file.assert_called_once_with(str(self.mock_audio))
    
    @patch("src.processors.gemini_transcriber.genai")
    def test_transcribe_file_not_found(self, mock_genai):
        """Test transcription with non-existent file."""
        transcriber = GeminiTranscriber(api_key=self.api_key)
        
        with self.assertRaises(FileNotFoundError):
            transcriber.transcribe(Path("/nonexistent/file.mp3"))
    
    @patch("src.processors.gemini_transcriber.genai")
    def test_transcribe_with_language(self, mock_genai):
        """Test transcription with language hint."""
        mock_uploaded_file = MagicMock()
        mock_uploaded_file.state.name = "ACTIVE"
        mock_genai.upload_file.return_value = mock_uploaded_file
        
        mock_response = Mock()
        mock_response.text = "Тестовая транскрипция."
        
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        
        transcriber = GeminiTranscriber(api_key=self.api_key)
        
        with patch.object(Path, "exists", return_value=True):
            result = transcriber.transcribe(self.mock_audio, language="Russian")
        
        self.assertIn("Тестовая", result)
        # Verify language hint was used in prompt
        call_args = mock_model.generate_content.call_args[0][0]
        self.assertTrue(any("Russian" in str(arg) for arg in call_args))
    
    @patch("src.processors.gemini_transcriber.genai")
    def test_fix_transcription(self, mock_genai):
        """Test transcription fixing."""
        mock_response = Mock()
        mock_response.text = "This is a properly formatted transcription. It has correct punctuation."
        
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        
        transcriber = GeminiTranscriber(api_key=self.api_key)
        
        raw_text = "this is a raw transcription it has no punctuation"
        result = transcriber.fix_transcription(raw_text)
        
        self.assertIn("properly formatted", result)
        mock_model.generate_content.assert_called_once()
    
    @patch("src.processors.gemini_transcriber.genai")
    def test_generate_timestamps(self, mock_genai):
        """Test timestamp generation."""
        timestamps_data = [
            {"start": 0.0, "end": 5.2, "text": "First sentence."},
            {"start": 5.2, "end": 10.5, "text": "Second sentence."}
        ]
        
        mock_response = Mock()
        mock_response.text = f"```json\n{json.dumps(timestamps_data)}\n```"
        
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        
        transcriber = GeminiTranscriber(api_key=self.api_key)
        
        result = transcriber.generate_timestamps(
            self.mock_audio,
            "Test transcription text"
        )
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["text"], "First sentence.")
        self.assertEqual(result[1]["start"], 5.2)
    
    @patch("src.processors.gemini_transcriber.genai")
    def test_generate_timestamps_plain_json(self, mock_genai):
        """Test timestamp generation with plain JSON response."""
        timestamps_data = [{"start": 0.0, "end": 3.0, "text": "Test"}]
        
        mock_response = Mock()
        mock_response.text = json.dumps(timestamps_data)  # No markdown
        
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        
        transcriber = GeminiTranscriber(api_key=self.api_key)
        
        result = transcriber.generate_timestamps(self.mock_audio, "Test")
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["text"], "Test")
    
    @patch("src.processors.gemini_transcriber.genai")
    def test_extract_highlights(self, mock_genai):
        """Test highlight extraction."""
        highlights_data = [
            {
                "timestamp": "00:15",
                "text": "Important quote here",
                "reason": "Key insight"
            },
            {
                "timestamp": "02:30",
                "text": "Another important point",
                "reason": "Actionable item"
            }
        ]
        
        mock_response = Mock()
        mock_response.text = f"```json\n{json.dumps(highlights_data)}\n```"
        
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        
        transcriber = GeminiTranscriber(api_key=self.api_key)
        
        result = transcriber.extract_highlights("Test transcription", max_highlights=5)
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["timestamp"], "00:15")
        self.assertEqual(result[1]["reason"], "Actionable item")
    
    @patch("src.processors.gemini_transcriber.genai")
    def test_progress_callback(self, mock_genai):
        """Test progress callback is called."""
        mock_uploaded_file = MagicMock()
        mock_uploaded_file.state.name = "ACTIVE"
        mock_genai.upload_file.return_value = mock_uploaded_file
        
        mock_response = Mock()
        mock_response.text = "Test"
        
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        
        progress_calls = []
        def callback(progress, status):
            progress_calls.append((progress, status))
        
        transcriber = GeminiTranscriber(
            api_key=self.api_key,
            progress_callback=callback
        )
        
        with patch.object(Path, "exists", return_value=True):
            transcriber.transcribe(self.mock_audio)
        
        self.assertGreater(len(progress_calls), 0)
        self.assertEqual(progress_calls[-1][0], 1.0)  # Final progress is 100%
    
    @patch("src.processors.gemini_transcriber.genai")
    def test_save_to_file(self, mock_genai):
        """Test saving transcription to file."""
        mock_uploaded_file = MagicMock()
        mock_uploaded_file.state.name = "ACTIVE"
        mock_genai.upload_file.return_value = mock_uploaded_file
        
        mock_response = Mock()
        mock_response.text = "Test transcription"
        
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        
        transcriber = GeminiTranscriber(api_key=self.api_key)
        
        output_file = Path("/tmp/test_output.txt")
        
        with patch.object(Path, "exists", return_value=True), \
             patch.object(Path, "write_text") as mock_write:
            
            transcriber.transcribe(self.mock_audio, output_path=output_file)
            
            mock_write.assert_called_once_with("Test transcription", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
