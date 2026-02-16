"""
Unit tests for CoverGenerator module
"""

import pytest
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from src.processors.cover_generator import CoverGenerator


@pytest.fixture
def mock_api_key():
    """Mock API key for testing"""
    return "test-api-key-12345"


@pytest.fixture
def generator(mock_api_key):
    """Create CoverGenerator instance with mocked API key"""
    with patch.dict(os.environ, {'GOOGLE_GEMINI_API_KEY': mock_api_key}):
        return CoverGenerator()


@pytest.fixture
def mock_image_data():
    """Mock image data (fake JPEG bytes)"""
    return b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'


class TestCoverGeneratorInit:
    """Test CoverGenerator initialization"""
    
    def test_init_with_api_key(self, mock_api_key):
        """Test initialization with explicit API key"""
        gen = CoverGenerator(api_key=mock_api_key)
        assert gen.api_key == mock_api_key
    
    def test_init_from_env(self, mock_api_key):
        """Test initialization from environment variable"""
        with patch.dict(os.environ, {'GOOGLE_GEMINI_API_KEY': mock_api_key}):
            gen = CoverGenerator()
            assert gen.api_key == mock_api_key
    
    def test_init_without_api_key(self):
        """Test initialization fails without API key"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="API key required"):
                CoverGenerator()


class TestPromptGeneration:
    """Test prompt generation methods"""
    
    def test_generate_prompt_basic(self, generator):
        """Test basic prompt generation"""
        prompt = generator.generate_prompt(
            title="Amazing Python Tutorial",
            style="modern"
        )
        
        assert "Amazing Python Tutorial" in prompt
        assert "1280x720" in prompt
        assert "modern minimalist" in prompt
    
    def test_generate_prompt_with_description(self, generator):
        """Test prompt generation with description"""
        prompt = generator.generate_prompt(
            title="Test Video",
            description="This is a test video about coding",
            style="cinematic"
        )
        
        assert "Test Video" in prompt
        assert "coding" in prompt
        assert "cinematic" in prompt
    
    def test_generate_prompt_custom_style(self, generator):
        """Test prompt with custom style string"""
        custom_style = "retro 80s neon aesthetic"
        prompt = generator.generate_prompt(
            title="Test",
            style=custom_style
        )
        
        assert custom_style in prompt
    
    def test_generate_prompt_custom_elements(self, generator):
        """Test prompt with custom elements"""
        prompt = generator.generate_prompt(
            title="Test",
            custom_elements="robot in the background, blue tones"
        )
        
        assert "robot in the background" in prompt
        assert "blue tones" in prompt


class TestCoverGeneration:
    """Test cover generation methods"""
    
    @patch('src.processors.cover_generator.requests.post')
    def test_generate_single_cover(self, mock_post, generator, mock_image_data, tmp_path):
        """Test generating a single cover"""
        # Mock API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'candidates': [{
                'content': {
                    'parts': [{
                        'inlineData': {
                            'data': mock_image_data.hex()
                        }
                    }]
                }
            }]
        }
        mock_post.return_value = mock_response
        
        # Generate cover
        paths = generator.generate_covers(
            title="Test Video",
            count=1,
            output_dir=tmp_path
        )
        
        assert len(paths) == 1
        assert paths[0].exists()
        assert paths[0].suffix == '.jpg'
    
    @patch('src.processors.cover_generator.requests.post')
    def test_generate_multiple_covers(self, mock_post, generator, mock_image_data, tmp_path):
        """Test generating 4 covers"""
        # Mock API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'candidates': [{
                'content': {
                    'parts': [{
                        'inlineData': {
                            'data': mock_image_data.hex()
                        }
                    }]
                }
            }]
        }
        mock_post.return_value = mock_response
        
        # Generate 4 covers
        paths = generator.generate_covers(
            title="Test Video",
            count=4,
            output_dir=tmp_path
        )
        
        assert len(paths) == 4
        assert mock_post.call_count == 4
        for path in paths:
            assert path.exists()
    
    def test_generate_covers_invalid_count(self, generator):
        """Test invalid cover count raises ValueError"""
        with pytest.raises(ValueError, match="between 1 and 4"):
            generator.generate_covers(title="Test", count=5)
        
        with pytest.raises(ValueError, match="between 1 and 4"):
            generator.generate_covers(title="Test", count=0)
    
    @patch('src.processors.cover_generator.requests.post')
    def test_generate_covers_with_styles(self, mock_post, generator, mock_image_data, tmp_path):
        """Test generating covers with specific styles"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'candidates': [{
                'content': {
                    'parts': [{
                        'inlineData': {
                            'data': mock_image_data.hex()
                        }
                    }]
                }
            }]
        }
        mock_post.return_value = mock_response
        
        styles = ['modern', 'dark']
        paths = generator.generate_covers(
            title="Test",
            count=2,
            styles=styles,
            output_dir=tmp_path
        )
        
        assert len(paths) == 2
        # Check that prompts were called with correct styles
        calls = mock_post.call_args_list
        assert 'modern minimalist' in str(calls[0])
        assert 'dark moody' in str(calls[1])
    
    @patch('src.processors.cover_generator.requests.post')
    def test_generate_covers_progress_callback(self, mock_post, generator, mock_image_data, tmp_path):
        """Test progress callback is called"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'candidates': [{
                'content': {
                    'parts': [{
                        'inlineData': {
                            'data': mock_image_data.hex()
                        }
                    }]
                }
            }]
        }
        mock_post.return_value = mock_response
        
        progress_calls = []
        def progress_callback(current, total, message):
            progress_calls.append((current, total, message))
        
        generator.generate_covers(
            title="Test",
            count=2,
            output_dir=tmp_path,
            progress_callback=progress_callback
        )
        
        # Should be called 4 times (2 "Generating" + 2 "Saved")
        assert len(progress_calls) == 4
        assert progress_calls[0][0] == 1  # First generation
        assert progress_calls[1][0] == 1  # First save
        assert progress_calls[2][0] == 2  # Second generation


class TestAPICall:
    """Test Gemini API call method"""
    
    @patch('src.processors.cover_generator.requests.post')
    def test_call_gemini_api_success(self, mock_post, generator, mock_image_data):
        """Test successful API call"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'candidates': [{
                'content': {
                    'parts': [{
                        'inlineData': {
                            'data': mock_image_data.hex()
                        }
                    }]
                }
            }]
        }
        mock_post.return_value = mock_response
        
        result = generator._call_gemini_api("test prompt")
        
        assert isinstance(result, bytes)
        assert len(result) > 0
    
    @patch('src.processors.cover_generator.requests.post')
    def test_call_gemini_api_network_error(self, mock_post, generator):
        """Test API call with network error"""
        mock_post.side_effect = Exception("Network error")
        
        with pytest.raises(RuntimeError, match="Failed to process"):
            generator._call_gemini_api("test prompt")
    
    @patch('src.processors.cover_generator.requests.post')
    def test_call_gemini_api_invalid_response(self, mock_post, generator):
        """Test API call with invalid response format"""
        mock_response = MagicMock()
        mock_response.json.return_value = {'error': 'Invalid request'}
        mock_post.return_value = mock_response
        
        with pytest.raises(RuntimeError, match="No image data"):
            generator._call_gemini_api("test prompt")


class TestUtilityMethods:
    """Test utility methods"""
    
    def test_get_available_styles(self, generator):
        """Test getting list of available styles"""
        styles = generator.get_available_styles()
        
        assert isinstance(styles, list)
        assert len(styles) > 0
        assert 'modern' in styles
        assert 'cinematic' in styles
        assert 'vibrant' in styles
