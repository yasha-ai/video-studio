"""
Unit tests for YouTube Uploader module.
"""

import pytest
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from processors.youtube_uploader import YouTubeUploader


class TestYouTubeUploader:
    """Test suite for YouTubeUploader class."""
    
    @pytest.fixture
    def mock_credentials(self, tmp_path):
        """Create mock credentials file."""
        creds_file = tmp_path / "credentials.json"
        creds_file.write_text('{"installed": {"client_id": "test"}}')
        return str(creds_file)
    
    @pytest.fixture
    def mock_token(self, tmp_path):
        """Path for mock token file."""
        return str(tmp_path / "token.pickle")
    
    @pytest.fixture
    def uploader(self, mock_credentials, mock_token):
        """Create YouTubeUploader instance with mocks."""
        return YouTubeUploader(
            credentials_path=mock_credentials,
            token_path=mock_token
        )
    
    @pytest.fixture
    def mock_video(self, tmp_path):
        """Create a mock video file."""
        video_file = tmp_path / "test_video.mp4"
        video_file.write_bytes(b"fake video data")
        return str(video_file)
    
    @pytest.fixture
    def mock_thumbnail(self, tmp_path):
        """Create a mock thumbnail file."""
        thumb_file = tmp_path / "thumbnail.jpg"
        thumb_file.write_bytes(b"fake image data")
        return str(thumb_file)
    
    # ===== INITIALIZATION TESTS =====
    
    def test_init(self, uploader, mock_credentials, mock_token):
        """Test uploader initialization."""
        assert uploader.credentials_path == mock_credentials
        assert uploader.token_path == mock_token
        assert uploader.credentials is None
        assert uploader.youtube is None
    
    def test_category_constants(self):
        """Test category ID mapping exists."""
        assert 'Science & Technology' in YouTubeUploader.CATEGORIES
        assert YouTubeUploader.CATEGORIES['Science & Technology'] == '28'
        assert YouTubeUploader.CATEGORIES['Music'] == '10'
    
    # ===== AUTHENTICATION TESTS =====
    
    @patch('processors.youtube_uploader.build')
    @patch('processors.youtube_uploader.InstalledAppFlow')
    def test_authenticate_new_user(self, mock_flow, mock_build, uploader):
        """Test first-time authentication (no saved token)."""
        # Mock OAuth flow
        mock_creds = Mock()
        mock_creds.valid = True
        mock_flow.from_client_secrets_file.return_value.run_local_server.return_value = mock_creds
        
        # Mock YouTube service
        mock_service = Mock()
        mock_build.return_value = mock_service
        
        # Authenticate
        result = uploader.authenticate()
        
        assert result is True
        assert uploader.credentials == mock_creds
        assert uploader.youtube == mock_service
        
        # Check token saved
        assert os.path.exists(uploader.token_path)
    
    @patch('processors.youtube_uploader.build')
    @patch('builtins.open', create=True)
    @patch('processors.youtube_uploader.pickle')
    def test_authenticate_existing_valid_token(self, mock_pickle, mock_open, mock_build, uploader, mock_token):
        """Test authentication with existing valid token."""
        # Mock existing valid credentials
        mock_creds = Mock()
        mock_creds.valid = True
        mock_pickle.load.return_value = mock_creds
        
        # Create fake token file
        Path(mock_token).write_bytes(b"fake token")
        
        # Mock YouTube service
        mock_service = Mock()
        mock_build.return_value = mock_service
        
        # Authenticate
        result = uploader.authenticate()
        
        assert result is True
        assert uploader.credentials == mock_creds
    
    @patch('processors.youtube_uploader.build')
    @patch('builtins.open', create=True)
    @patch('processors.youtube_uploader.pickle')
    @patch('processors.youtube_uploader.Request')
    def test_authenticate_refresh_expired_token(self, mock_request, mock_pickle, mock_open, mock_build, uploader, mock_token):
        """Test token refresh when expired."""
        # Mock expired credentials with refresh token
        mock_creds = Mock()
        mock_creds.valid = False
        mock_creds.expired = True
        mock_creds.refresh_token = "refresh_token_xyz"
        mock_pickle.load.return_value = mock_creds
        
        # Create fake token file
        Path(mock_token).write_bytes(b"fake token")
        
        # Mock refresh
        def refresh_side_effect(request):
            mock_creds.valid = True
        mock_creds.refresh.side_effect = refresh_side_effect
        
        # Mock YouTube service
        mock_service = Mock()
        mock_build.return_value = mock_service
        
        # Authenticate
        result = uploader.authenticate()
        
        assert result is True
        mock_creds.refresh.assert_called_once()
    
    def test_authenticate_missing_credentials_file(self, mock_token):
        """Test authentication fails with missing credentials file."""
        uploader = YouTubeUploader(
            credentials_path="nonexistent.json",
            token_path=mock_token
        )
        
        result = uploader.authenticate()
        
        assert result is False
    
    # ===== UPLOAD TESTS =====
    
    @patch('processors.youtube_uploader.MediaFileUpload')
    def test_upload_video_not_authenticated(self, mock_media, uploader, mock_video):
        """Test upload fails if not authenticated."""
        result = uploader.upload_video(
            video_path=mock_video,
            title="Test Video"
        )
        
        assert result is None
    
    @patch('processors.youtube_uploader.MediaFileUpload')
    def test_upload_video_success(self, mock_media, uploader, mock_video):
        """Test successful video upload."""
        # Mock authenticated state
        uploader.youtube = Mock()
        
        # Mock upload response
        mock_response = {
            'id': 'test_video_id_123',
            'snippet': {'title': 'Test Video'},
            'status': {'privacyStatus': 'unlisted'}
        }
        
        # Mock request/response flow
        mock_request = Mock()
        mock_request.next_chunk.side_effect = [
            (Mock(resumable_progress=500, total_size=1000), None),
            (Mock(resumable_progress=1000, total_size=1000), mock_response)
        ]
        
        uploader.youtube.videos().insert.return_value = mock_request
        
        # Upload
        result = uploader.upload_video(
            video_path=mock_video,
            title="Test Video",
            description="Test description",
            privacy_status="unlisted"
        )
        
        assert result is not None
        assert result['id'] == 'test_video_id_123'
        assert result['url'] == 'https://www.youtube.com/watch?v=test_video_id_123'
        assert result['title'] == 'Test Video'
    
    @patch('processors.youtube_uploader.MediaFileUpload')
    def test_upload_video_with_tags(self, mock_media, uploader, mock_video):
        """Test upload with tags."""
        # Mock authenticated state
        uploader.youtube = Mock()
        
        mock_response = {
            'id': 'vid123',
            'snippet': {'title': 'Test'},
            'status': {'privacyStatus': 'public'}
        }
        
        mock_request = Mock()
        mock_request.next_chunk.return_value = (None, mock_response)
        uploader.youtube.videos().insert.return_value = mock_request
        
        # Upload with tags
        result = uploader.upload_video(
            video_path=mock_video,
            title="Test",
            tags=["tech", "tutorial", "python"]
        )
        
        # Check tags were included in request
        insert_call = uploader.youtube.videos().insert
        call_kwargs = insert_call.call_args[1]
        assert 'tags' in call_kwargs['body']['snippet']
        assert call_kwargs['body']['snippet']['tags'] == ["tech", "tutorial", "python"]
    
    @patch('processors.youtube_uploader.MediaFileUpload')
    def test_upload_video_progress_callback(self, mock_media, uploader, mock_video):
        """Test progress callback is called during upload."""
        # Mock authenticated state
        uploader.youtube = Mock()
        
        mock_response = {'id': 'vid123', 'snippet': {'title': 'Test'}, 'status': {'privacyStatus': 'public'}}
        
        # Mock chunked upload
        mock_status_1 = Mock(resumable_progress=500, total_size=1000)
        mock_status_2 = Mock(resumable_progress=1000, total_size=1000)
        
        mock_request = Mock()
        mock_request.next_chunk.side_effect = [
            (mock_status_1, None),
            (mock_status_2, mock_response)
        ]
        
        uploader.youtube.videos().insert.return_value = mock_request
        
        # Track progress calls
        progress_calls = []
        def progress_cb(uploaded, total):
            progress_calls.append((uploaded, total))
        
        # Upload
        uploader.upload_video(
            video_path=mock_video,
            title="Test",
            progress_callback=progress_cb
        )
        
        # Check progress was tracked
        assert len(progress_calls) == 2
        assert progress_calls[0] == (500, 1000)
        assert progress_calls[1] == (1000, 1000)
    
    def test_upload_video_missing_file(self, uploader):
        """Test upload fails with missing video file."""
        uploader.youtube = Mock()
        
        result = uploader.upload_video(
            video_path="nonexistent.mp4",
            title="Test"
        )
        
        assert result is None
    
    @patch('processors.youtube_uploader.MediaFileUpload')
    def test_upload_video_title_truncation(self, mock_media, uploader, mock_video):
        """Test title is truncated to 100 chars."""
        uploader.youtube = Mock()
        
        mock_response = {'id': 'vid', 'snippet': {'title': 'x'*100}, 'status': {'privacyStatus': 'public'}}
        mock_request = Mock()
        mock_request.next_chunk.return_value = (None, mock_response)
        uploader.youtube.videos().insert.return_value = mock_request
        
        # Upload with long title
        long_title = "x" * 150
        uploader.upload_video(
            video_path=mock_video,
            title=long_title
        )
        
        # Check title was truncated
        call_kwargs = uploader.youtube.videos().insert.call_args[1]
        assert len(call_kwargs['body']['snippet']['title']) == 100
    
    # ===== THUMBNAIL TESTS =====
    
    @patch('processors.youtube_uploader.MediaFileUpload')
    def test_upload_thumbnail_success(self, mock_media, uploader, mock_thumbnail):
        """Test successful thumbnail upload."""
        uploader.youtube = Mock()
        
        result = uploader.upload_thumbnail(
            video_id="test_video_123",
            thumbnail_path=mock_thumbnail
        )
        
        assert result is True
        uploader.youtube.thumbnails().set.assert_called_once()
    
    def test_upload_thumbnail_missing_file(self, uploader):
        """Test thumbnail upload fails with missing file."""
        uploader.youtube = Mock()
        
        result = uploader.upload_thumbnail(
            video_id="test_video",
            thumbnail_path="nonexistent.jpg"
        )
        
        assert result is False
    
    @patch('processors.youtube_uploader.MediaFileUpload')
    def test_upload_thumbnail_size_limit(self, mock_media, uploader, tmp_path):
        """Test thumbnail upload fails if > 2MB."""
        uploader.youtube = Mock()
        
        # Create 3MB file
        large_thumb = tmp_path / "large.jpg"
        large_thumb.write_bytes(b"x" * (3 * 1024 * 1024))
        
        result = uploader.upload_thumbnail(
            video_id="test",
            thumbnail_path=str(large_thumb)
        )
        
        assert result is False
    
    # ===== STATUS CHECK TESTS =====
    
    def test_get_upload_status_success(self, uploader):
        """Test successful status retrieval."""
        uploader.youtube = Mock()
        
        mock_response = {
            'items': [{
                'status': {
                    'uploadStatus': 'uploaded',
                    'privacyStatus': 'public'
                },
                'processingDetails': {
                    'processingStatus': 'succeeded'
                }
            }]
        }
        
        uploader.youtube.videos().list().execute.return_value = mock_response
        
        status = uploader.get_upload_status("test_video_id")
        
        assert status['uploadStatus'] == 'uploaded'
        assert status['privacyStatus'] == 'public'
        assert status['processingStatus'] == 'succeeded'
    
    def test_get_upload_status_not_found(self, uploader):
        """Test status retrieval when video not found."""
        uploader.youtube = Mock()
        
        mock_response = {'items': []}
        uploader.youtube.videos().list().execute.return_value = mock_response
        
        status = uploader.get_upload_status("nonexistent_id")
        
        assert status is None
    
    def test_get_upload_status_not_authenticated(self, uploader):
        """Test status check fails if not authenticated."""
        result = uploader.get_upload_status("test_id")
        
        assert result is None


# ===== INTEGRATION TESTS =====
# (These require actual OAuth credentials and are skipped by default)

@pytest.mark.skip(reason="Requires OAuth credentials")
class TestYouTubeUploaderIntegration:
    """Integration tests with real YouTube API."""
    
    def test_real_upload(self):
        """Test real video upload (requires credentials)."""
        # This would use actual credentials and upload a test video
        # Only run manually with: pytest -m integration
        pass


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
