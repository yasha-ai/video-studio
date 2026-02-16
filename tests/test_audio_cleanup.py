"""
Unit tests for Audio Cleanup Module
"""

import os
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import subprocess

# Add src to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from processors.audio_cleanup import AudioCleanup


class TestAudioCleanupBuiltin:
    """Tests for built-in cleanup mode."""
    
    def test_init_builtin_mode(self):
        """Test initialization in builtin mode."""
        cleanup = AudioCleanup(mode='builtin')
        assert cleanup.mode == 'builtin'
    
    def test_init_auphonic_mode_without_key(self):
        """Test that auphonic mode requires API key."""
        with pytest.raises(ValueError, match="Auphonic API key required"):
            AudioCleanup(mode='auphonic')
    
    def test_init_auphonic_mode_with_key(self):
        """Test initialization in auphonic mode with API key."""
        cleanup = AudioCleanup(mode='auphonic', auphonic_api_key='test-key')
        assert cleanup.mode == 'auphonic'
        assert cleanup.auphonic_api_key == 'test-key'
    
    @patch('subprocess.run')
    def test_builtin_cleanup_light_preset(self, mock_run):
        """Test built-in cleanup with light preset."""
        mock_run.return_value = Mock(returncode=0, stdout='', stderr='')
        
        cleanup = AudioCleanup(mode='builtin')
        
        # Mock input file
        with patch('pathlib.Path.exists', return_value=True):
            output = cleanup.cleanup(
                input_path='test_audio.wav',
                output_path='test_audio_cleaned.wav',
                preset='light'
            )
        
        # Check ffmpeg was called
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        
        assert cmd[0] == 'ffmpeg'
        assert 'test_audio.wav' in cmd
        assert 'test_audio_cleaned.wav' in cmd
        assert '-af' in cmd
        
        # Check filter chain includes expected filters
        filter_idx = cmd.index('-af')
        filter_chain = cmd[filter_idx + 1]
        
        assert 'highpass' in filter_chain
        assert 'lowpass' in filter_chain
        assert 'afftdn' in filter_chain
        assert 'loudnorm' in filter_chain
    
    @patch('subprocess.run')
    def test_builtin_cleanup_medium_preset(self, mock_run):
        """Test built-in cleanup with medium preset."""
        mock_run.return_value = Mock(returncode=0, stdout='', stderr='')
        
        cleanup = AudioCleanup(mode='builtin')
        
        with patch('pathlib.Path.exists', return_value=True):
            output = cleanup.cleanup(
                input_path='test.wav',
                preset='medium'
            )
        
        mock_run.assert_called_once()
    
    @patch('subprocess.run')
    def test_builtin_cleanup_aggressive_preset(self, mock_run):
        """Test built-in cleanup with aggressive preset."""
        mock_run.return_value = Mock(returncode=0, stdout='', stderr='')
        
        cleanup = AudioCleanup(mode='builtin')
        
        with patch('pathlib.Path.exists', return_value=True):
            output = cleanup.cleanup(
                input_path='test.wav',
                preset='aggressive'
            )
        
        mock_run.assert_called_once()
    
    @patch('subprocess.run')
    def test_builtin_cleanup_custom_params(self, mock_run):
        """Test built-in cleanup with custom parameters."""
        mock_run.return_value = Mock(returncode=0, stdout='', stderr='')
        
        cleanup = AudioCleanup(mode='builtin')
        
        custom = {
            'highpass': 150,
            'lowpass': 9000,
            'nr_amount': 7
        }
        
        with patch('pathlib.Path.exists', return_value=True):
            output = cleanup.cleanup(
                input_path='test.wav',
                preset='medium',
                custom_params=custom
            )
        
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        filter_chain = cmd[cmd.index('-af') + 1]
        
        assert 'highpass=f=150' in filter_chain
        assert 'lowpass=f=9000' in filter_chain
    
    @patch('subprocess.run')
    def test_builtin_cleanup_progress_callback(self, mock_run):
        """Test progress callback during built-in cleanup."""
        mock_run.return_value = Mock(returncode=0, stdout='', stderr='')
        
        cleanup = AudioCleanup(mode='builtin')
        progress_values = []
        
        def progress_cb(p: float):
            progress_values.append(p)
        
        with patch('pathlib.Path.exists', return_value=True):
            cleanup.cleanup(
                input_path='test.wav',
                progress_callback=progress_cb
            )
        
        # Should have start and end progress updates
        assert len(progress_values) >= 2
        assert progress_values[0] == 0.1  # Starting
        assert progress_values[-1] == 1.0  # Complete
    
    def test_cleanup_file_not_found(self):
        """Test error when input file doesn't exist."""
        cleanup = AudioCleanup(mode='builtin')
        
        with pytest.raises(FileNotFoundError):
            cleanup.cleanup(input_path='nonexistent.wav')
    
    @patch('subprocess.run')
    def test_cleanup_ffmpeg_error(self, mock_run):
        """Test error handling when ffmpeg fails."""
        mock_run.side_effect = subprocess.CalledProcessError(
            1, 'ffmpeg', stderr='Error processing audio'
        )
        
        cleanup = AudioCleanup(mode='builtin')
        
        with patch('pathlib.Path.exists', return_value=True):
            with pytest.raises(RuntimeError, match="ffmpeg audio cleanup failed"):
                cleanup.cleanup(input_path='test.wav')


class TestAudioCleanupAuphonic:
    """Tests for Auphonic API mode."""
    
    @patch('requests.post')
    @patch('requests.get')
    def test_auphonic_cleanup_success(self, mock_get, mock_post):
        """Test successful Auphonic cleanup."""
        # Mock API responses
        mock_post.return_value.json.return_value = {
            'data': {'uuid': 'test-uuid'}
        }
        mock_post.return_value.raise_for_status = Mock()
        
        # Mock status polling
        mock_get.return_value.json.return_value = {
            'data': {
                'status_string': 'Done',
                'completion': 100,
                'output_files': [{
                    'download_url': 'http://example.com/output.wav'
                }]
            }
        }
        mock_get.return_value.raise_for_status = Mock()
        mock_get.return_value.iter_content = Mock(return_value=[b'audio data'])
        
        cleanup = AudioCleanup(mode='auphonic', auphonic_api_key='test-key')
        
        with patch('pathlib.Path.exists', return_value=True):
            with patch('builtins.open', create=True) as mock_open:
                output = cleanup.cleanup(
                    input_path='test.wav',
                    output_path='output.wav',
                    preset='podcast'
                )
        
        # Verify API was called
        assert mock_post.call_count >= 2  # Create production + upload + start
        assert mock_get.call_count >= 1   # Status polling + download
    
    @patch('requests.post')
    @patch('requests.get')
    def test_auphonic_cleanup_error(self, mock_get, mock_post):
        """Test Auphonic error handling."""
        # Mock production creation
        mock_post.return_value.json.return_value = {
            'data': {'uuid': 'test-uuid'}
        }
        mock_post.return_value.raise_for_status = Mock()
        
        # Mock error status
        mock_get.return_value.json.return_value = {
            'data': {
                'status_string': 'Error',
                'error_message': 'Processing failed'
            }
        }
        mock_get.return_value.raise_for_status = Mock()
        
        cleanup = AudioCleanup(mode='auphonic', auphonic_api_key='test-key')
        
        with patch('pathlib.Path.exists', return_value=True):
            with patch('builtins.open', create=True):
                with pytest.raises(RuntimeError, match="Auphonic processing failed"):
                    cleanup.cleanup(
                        input_path='test.wav',
                        preset='podcast'
                    )
    
    @patch('requests.post')
    @patch('requests.get')
    @patch('time.sleep')  # Mock sleep to speed up test
    def test_auphonic_cleanup_timeout(self, mock_sleep, mock_get, mock_post):
        """Test Auphonic timeout handling."""
        # Mock production creation
        mock_post.return_value.json.return_value = {
            'data': {'uuid': 'test-uuid'}
        }
        mock_post.return_value.raise_for_status = Mock()
        
        # Mock perpetual processing status
        mock_get.return_value.json.return_value = {
            'data': {
                'status_string': 'Processing',
                'completion': 50
            }
        }
        mock_get.return_value.raise_for_status = Mock()
        
        cleanup = AudioCleanup(mode='auphonic', auphonic_api_key='test-key')
        
        # Reduce max_wait for faster test
        with patch.object(cleanup, '_cleanup_auphonic') as mock_method:
            mock_method.side_effect = TimeoutError("Auphonic processing timeout")
            
            with patch('pathlib.Path.exists', return_value=True):
                with patch('builtins.open', create=True):
                    with pytest.raises(TimeoutError):
                        cleanup.cleanup(
                            input_path='test.wav',
                            preset='podcast'
                        )


class TestPresets:
    """Tests for cleanup presets."""
    
    def test_builtin_presets_exist(self):
        """Test that all builtin presets are defined."""
        assert 'light' in AudioCleanup.BUILTIN_PRESETS
        assert 'medium' in AudioCleanup.BUILTIN_PRESETS
        assert 'aggressive' in AudioCleanup.BUILTIN_PRESETS
    
    def test_auphonic_presets_exist(self):
        """Test that all Auphonic presets are defined."""
        assert 'podcast' in AudioCleanup.AUPHONIC_PRESETS
        assert 'video' in AudioCleanup.AUPHONIC_PRESETS
        assert 'speech' in AudioCleanup.AUPHONIC_PRESETS
    
    def test_builtin_preset_structure(self):
        """Test built-in preset structure."""
        preset = AudioCleanup.BUILTIN_PRESETS['medium']
        
        assert 'highpass' in preset
        assert 'lowpass' in preset
        assert 'nr_amount' in preset
        assert 'gate' in preset
        assert 'normalize' in preset
    
    def test_auphonic_preset_structure(self):
        """Test Auphonic preset structure."""
        preset = AudioCleanup.AUPHONIC_PRESETS['podcast']
        
        assert 'output_basename' in preset
        assert 'algorithms' in preset
        assert isinstance(preset['algorithms'], dict)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
