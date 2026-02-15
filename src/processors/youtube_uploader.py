"""
YouTube Uploader Module

Handles video upload to YouTube using Google YouTube Data API v3.
Supports OAuth2 authentication, metadata setting, and thumbnail upload.
"""

import os
import pickle
from pathlib import Path
from typing import Optional, Dict, Any, List
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError


class YouTubeUploader:
    """
    YouTube video uploader with OAuth2 authentication.
    
    Features:
    - OAuth2 authentication (saves credentials for reuse)
    - Video upload with metadata (title, description, tags, category)
    - Thumbnail upload
    - Privacy settings (public, unlisted, private)
    - Progress callback support
    """
    
    # OAuth2 scopes required for upload
    SCOPES = ['https://www.googleapis.com/auth/youtube.upload',
              'https://www.googleapis.com/auth/youtube']
    
    # API service details
    API_SERVICE_NAME = 'youtube'
    API_VERSION = 'v3'
    
    # Video categories (common ones)
    CATEGORIES = {
        'Film & Animation': '1',
        'Autos & Vehicles': '2',
        'Music': '10',
        'Pets & Animals': '15',
        'Sports': '17',
        'Travel & Events': '19',
        'Gaming': '20',
        'People & Blogs': '22',
        'Comedy': '23',
        'Entertainment': '24',
        'News & Politics': '25',
        'Howto & Style': '26',
        'Education': '27',
        'Science & Technology': '28',
        'Nonprofits & Activism': '29'
    }
    
    def __init__(self, credentials_path: str, token_path: str = 'token.pickle'):
        """
        Initialize YouTube uploader.
        
        Args:
            credentials_path: Path to OAuth2 client secrets JSON file
                            (downloaded from Google Cloud Console)
            token_path: Path to save/load authentication token (pickle)
        """
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.credentials: Optional[Credentials] = None
        self.youtube = None
        
    def authenticate(self) -> bool:
        """
        Authenticate with YouTube API using OAuth2.
        
        Returns:
            True if authentication successful, False otherwise
            
        Notes:
            - First run: Opens browser for user authorization
            - Subsequent runs: Uses saved token (if valid)
            - Token auto-refreshes if expired
        """
        try:
            # Load saved credentials if available
            if os.path.exists(self.token_path):
                with open(self.token_path, 'rb') as token:
                    self.credentials = pickle.load(token)
            
            # Refresh or re-authenticate if needed
            if not self.credentials or not self.credentials.valid:
                if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                    # Refresh expired token
                    self.credentials.refresh(Request())
                else:
                    # New authentication flow
                    if not os.path.exists(self.credentials_path):
                        raise FileNotFoundError(
                            f"OAuth2 credentials file not found: {self.credentials_path}\n"
                            f"Download it from Google Cloud Console:\n"
                            f"https://console.cloud.google.com/apis/credentials"
                        )
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, self.SCOPES
                    )
                    self.credentials = flow.run_local_server(port=0)
                
                # Save credentials for next run
                with open(self.token_path, 'wb') as token:
                    pickle.dump(self.credentials, token)
            
            # Build YouTube API client
            self.youtube = build(
                self.API_SERVICE_NAME,
                self.API_VERSION,
                credentials=self.credentials
            )
            
            return True
            
        except Exception as e:
            print(f"Authentication failed: {e}")
            return False
    
    def upload_video(
        self,
        video_path: str,
        title: str,
        description: str = "",
        tags: Optional[List[str]] = None,
        category_id: str = "22",  # People & Blogs by default
        privacy_status: str = "unlisted",  # public, unlisted, private
        thumbnail_path: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Upload video to YouTube.
        
        Args:
            video_path: Path to video file
            title: Video title (max 100 chars)
            description: Video description (max 5000 chars)
            tags: List of tags (max 500 chars total)
            category_id: YouTube category ID (see CATEGORIES)
            privacy_status: "public", "unlisted", or "private"
            thumbnail_path: Optional path to thumbnail image (JPG/PNG)
            progress_callback: Optional callback(bytes_uploaded, total_bytes)
            
        Returns:
            Video metadata dict with 'id', 'url', 'title' if successful
            None if upload fails
        """
        if not self.youtube:
            if not self.authenticate():
                return None
        
        try:
            # Validate video file
            video_path = Path(video_path)
            if not video_path.exists():
                raise FileNotFoundError(f"Video file not found: {video_path}")
            
            # Prepare metadata
            body = {
                'snippet': {
                    'title': title[:100],  # Max 100 chars
                    'description': description[:5000],  # Max 5000 chars
                    'categoryId': category_id
                },
                'status': {
                    'privacyStatus': privacy_status,
                    'selfDeclaredMadeForKids': False
                }
            }
            
            # Add tags if provided
            if tags:
                # Combine tags (max 500 chars total)
                tags_str = ','.join(tags)
                if len(tags_str) <= 500:
                    body['snippet']['tags'] = tags
            
            # Prepare media upload
            media = MediaFileUpload(
                str(video_path),
                mimetype='video/*',
                resumable=True,
                chunksize=1024*1024  # 1MB chunks
            )
            
            # Create upload request
            request = self.youtube.videos().insert(
                part=','.join(body.keys()),
                body=body,
                media_body=media
            )
            
            # Upload with progress tracking
            response = None
            while response is None:
                status, response = request.next_chunk()
                
                if status and progress_callback:
                    progress_callback(
                        status.resumable_progress,
                        status.total_size
                    )
            
            # Upload thumbnail if provided
            if thumbnail_path and response:
                self.upload_thumbnail(response['id'], thumbnail_path)
            
            # Return video info
            video_id = response['id']
            return {
                'id': video_id,
                'url': f'https://www.youtube.com/watch?v={video_id}',
                'title': response['snippet']['title'],
                'status': response['status']['privacyStatus']
            }
            
        except HttpError as e:
            print(f"YouTube API error: {e}")
            return None
        except Exception as e:
            print(f"Upload failed: {e}")
            return None
    
    def upload_thumbnail(self, video_id: str, thumbnail_path: str) -> bool:
        """
        Upload custom thumbnail for a video.
        
        Args:
            video_id: YouTube video ID
            thumbnail_path: Path to thumbnail image (JPG/PNG, max 2MB)
            
        Returns:
            True if successful, False otherwise
            
        Notes:
            - Image must be JPG or PNG
            - Max size: 2MB
            - Recommended resolution: 1280x720 (16:9)
        """
        if not self.youtube:
            if not self.authenticate():
                return False
        
        try:
            thumbnail_path = Path(thumbnail_path)
            if not thumbnail_path.exists():
                raise FileNotFoundError(f"Thumbnail not found: {thumbnail_path}")
            
            # Check file size (max 2MB)
            if thumbnail_path.stat().st_size > 2 * 1024 * 1024:
                raise ValueError("Thumbnail size exceeds 2MB limit")
            
            # Upload thumbnail
            self.youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(str(thumbnail_path))
            ).execute()
            
            return True
            
        except Exception as e:
            print(f"Thumbnail upload failed: {e}")
            return False
    
    def get_upload_status(self, video_id: str) -> Optional[Dict[str, Any]]:
        """
        Get video upload/processing status.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Status dict with 'uploadStatus' and 'privacyStatus'
            None if request fails
        """
        if not self.youtube:
            if not self.authenticate():
                return None
        
        try:
            request = self.youtube.videos().list(
                part='status,processingDetails',
                id=video_id
            )
            response = request.execute()
            
            if response['items']:
                item = response['items'][0]
                return {
                    'uploadStatus': item['status'].get('uploadStatus'),
                    'privacyStatus': item['status'].get('privacyStatus'),
                    'processingStatus': item.get('processingDetails', {}).get('processingStatus')
                }
            
            return None
            
        except Exception as e:
            print(f"Failed to get status: {e}")
            return None


# CLI для тестирования
if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 4:
        print("Usage: python youtube_uploader.py <credentials.json> <video.mp4> <title>")
        sys.exit(1)
    
    credentials_path = sys.argv[1]
    video_path = sys.argv[2]
    title = sys.argv[3]
    
    uploader = YouTubeUploader(credentials_path)
    
    def progress(uploaded, total):
        percent = (uploaded / total) * 100
        print(f"Upload progress: {percent:.1f}%")
    
    result = uploader.upload_video(
        video_path=video_path,
        title=title,
        description="Uploaded via Video Studio",
        privacy_status="unlisted",
        progress_callback=progress
    )
    
    if result:
        print(f"\n✅ Upload successful!")
        print(f"Video ID: {result['id']}")
        print(f"URL: {result['url']}")
    else:
        print("\n❌ Upload failed")
