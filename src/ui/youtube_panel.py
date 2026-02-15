"""
YouTube Upload Panel UI Component

Provides interface for uploading processed videos to YouTube.
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path
from typing import Optional, Callable
import threading


class YouTubePanel(ctk.CTkFrame):
    """
    YouTube upload panel with OAuth setup and upload controls.
    
    Features:
    - OAuth credentials configuration
    - Video metadata input (title, description, tags)
    - Privacy settings selection
    - Thumbnail selection
    - Upload progress tracking
    - Status display
    """
    
    def __init__(self, master, artifacts_manager, **kwargs):
        super().__init__(master, **kwargs)
        
        self.artifacts_manager = artifacts_manager
        self.uploader = None
        self.credentials_path = None
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Create panel widgets."""
        # Header
        header = ctk.CTkLabel(
            self,
            text="📤 YouTube Upload",
            font=("Arial", 20, "bold")
        )
        header.pack(pady=(0, 20))
        
        # ===== AUTHENTICATION SECTION =====
        auth_frame = ctk.CTkFrame(self, fg_color="transparent")
        auth_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(
            auth_frame,
            text="🔑 Authentication",
            font=("Arial", 14, "bold")
        ).pack(anchor="w", pady=(0, 10))
        
        # Credentials file selection
        creds_container = ctk.CTkFrame(auth_frame)
        creds_container.pack(fill="x", pady=5)
        
        self.creds_label = ctk.CTkLabel(
            creds_container,
            text="No credentials file selected",
            text_color="gray"
        )
        self.creds_label.pack(side="left", padx=5)
        
        ctk.CTkButton(
            creds_container,
            text="Select credentials.json",
            command=self._select_credentials,
            width=180
        ).pack(side="right", padx=5)
        
        # Auth status
        self.auth_status = ctk.CTkLabel(
            auth_frame,
            text="⚪ Not authenticated",
            text_color="gray"
        )
        self.auth_status.pack(anchor="w", pady=5)
        
        ctk.CTkButton(
            auth_frame,
            text="🔐 Authenticate",
            command=self._authenticate,
            width=150
        ).pack(anchor="w", pady=10)
        
        # Separator
        ctk.CTkFrame(self, height=2, fg_color="gray30").pack(fill="x", pady=20)
        
        # ===== METADATA SECTION =====
        metadata_frame = ctk.CTkFrame(self, fg_color="transparent")
        metadata_frame.pack(fill="both", expand=True, pady=10)
        
        ctk.CTkLabel(
            metadata_frame,
            text="📝 Video Metadata",
            font=("Arial", 14, "bold")
        ).pack(anchor="w", pady=(0, 10))
        
        # Title
        ctk.CTkLabel(metadata_frame, text="Title:").pack(anchor="w", pady=(5, 0))
        self.title_entry = ctk.CTkEntry(
            metadata_frame,
            placeholder_text="Enter video title (max 100 chars)"
        )
        self.title_entry.pack(fill="x", pady=5)
        
        # Description
        ctk.CTkLabel(metadata_frame, text="Description:").pack(anchor="w", pady=(10, 0))
        self.desc_textbox = ctk.CTkTextbox(metadata_frame, height=100)
        self.desc_textbox.pack(fill="x", pady=5)
        
        # Tags
        ctk.CTkLabel(metadata_frame, text="Tags (comma-separated):").pack(anchor="w", pady=(10, 0))
        self.tags_entry = ctk.CTkEntry(
            metadata_frame,
            placeholder_text="tech, tutorial, education"
        )
        self.tags_entry.pack(fill="x", pady=5)
        
        # Privacy & Category row
        options_row = ctk.CTkFrame(metadata_frame, fg_color="transparent")
        options_row.pack(fill="x", pady=10)
        
        # Privacy
        privacy_frame = ctk.CTkFrame(options_row, fg_color="transparent")
        privacy_frame.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        ctk.CTkLabel(privacy_frame, text="Privacy:").pack(anchor="w")
        self.privacy_var = ctk.StringVar(value="unlisted")
        privacy_menu = ctk.CTkOptionMenu(
            privacy_frame,
            values=["public", "unlisted", "private"],
            variable=self.privacy_var
        )
        privacy_menu.pack(fill="x", pady=5)
        
        # Category
        category_frame = ctk.CTkFrame(options_row, fg_color="transparent")
        category_frame.pack(side="right", fill="x", expand=True)
        
        ctk.CTkLabel(category_frame, text="Category:").pack(anchor="w")
        self.category_var = ctk.StringVar(value="Science & Technology")
        category_menu = ctk.CTkOptionMenu(
            category_frame,
            values=[
                "Film & Animation",
                "Music",
                "Gaming",
                "Education",
                "Science & Technology",
                "People & Blogs",
                "Entertainment"
            ],
            variable=self.category_var
        )
        category_menu.pack(fill="x", pady=5)
        
        # Thumbnail selection
        thumb_frame = ctk.CTkFrame(metadata_frame, fg_color="transparent")
        thumb_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(thumb_frame, text="Thumbnail:").pack(anchor="w")
        
        thumb_row = ctk.CTkFrame(thumb_frame)
        thumb_row.pack(fill="x", pady=5)
        
        self.thumb_label = ctk.CTkLabel(
            thumb_row,
            text="No thumbnail selected (optional)",
            text_color="gray"
        )
        self.thumb_label.pack(side="left", padx=5)
        
        ctk.CTkButton(
            thumb_row,
            text="Select Image",
            command=self._select_thumbnail,
            width=120
        ).pack(side="right", padx=5)
        
        # Separator
        ctk.CTkFrame(self, height=2, fg_color="gray30").pack(fill="x", pady=20)
        
        # ===== UPLOAD SECTION =====
        upload_frame = ctk.CTkFrame(self, fg_color="transparent")
        upload_frame.pack(fill="x", pady=10)
        
        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(upload_frame)
        self.progress_bar.pack(fill="x", pady=10)
        self.progress_bar.set(0)
        
        self.status_label = ctk.CTkLabel(
            upload_frame,
            text="Ready to upload",
            text_color="gray"
        )
        self.status_label.pack(pady=5)
        
        # Upload button
        self.upload_btn = ctk.CTkButton(
            upload_frame,
            text="🚀 Upload to YouTube",
            command=self._start_upload,
            height=40,
            font=("Arial", 14, "bold"),
            state="disabled"
        )
        self.upload_btn.pack(pady=10)
    
    def _select_credentials(self):
        """Open file dialog to select OAuth credentials JSON."""
        filepath = filedialog.askopenfilename(
            title="Select OAuth2 Credentials",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filepath:
            self.credentials_path = filepath
            filename = Path(filepath).name
            self.creds_label.configure(text=f"✓ {filename}", text_color="green")
    
    def _authenticate(self):
        """Authenticate with YouTube API."""
        if not self.credentials_path:
            messagebox.showerror(
                "Error",
                "Please select OAuth2 credentials file first"
            )
            return
        
        try:
            # Import here to avoid circular dependencies
            from ..processors.youtube_uploader import YouTubeUploader
            
            self.status_label.configure(text="Authenticating...", text_color="yellow")
            self.auth_status.configure(text="🔄 Authenticating...", text_color="yellow")
            
            # Run auth in thread to avoid blocking UI
            def auth_thread():
                self.uploader = YouTubeUploader(self.credentials_path)
                success = self.uploader.authenticate()
                
                # Update UI from main thread
                self.after(0, lambda: self._auth_complete(success))
            
            threading.Thread(target=auth_thread, daemon=True).start()
            
        except Exception as e:
            self.auth_status.configure(text=f"❌ Error: {str(e)}", text_color="red")
            self.status_label.configure(text="Authentication failed", text_color="red")
    
    def _auth_complete(self, success: bool):
        """Handle authentication completion."""
        if success:
            self.auth_status.configure(text="✅ Authenticated", text_color="green")
            self.status_label.configure(text="Ready to upload", text_color="green")
            self.upload_btn.configure(state="normal")
        else:
            self.auth_status.configure(text="❌ Authentication failed", text_color="red")
            self.status_label.configure(text="Authentication failed", text_color="red")
    
    def _select_thumbnail(self):
        """Open file dialog to select thumbnail image."""
        filepath = filedialog.askopenfilename(
            title="Select Thumbnail",
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png"),
                ("All files", "*.*")
            ]
        )
        
        if filepath:
            self.thumbnail_path = filepath
            filename = Path(filepath).name
            self.thumb_label.configure(text=f"✓ {filename}", text_color="green")
    
    def _start_upload(self):
        """Start video upload in background thread."""
        if not self.uploader:
            messagebox.showerror("Error", "Please authenticate first")
            return
        
        # Get video path from artifacts
        video_artifact = self.artifacts_manager.get("final_video")
        if not video_artifact:
            messagebox.showerror("Error", "No final video found in artifacts")
            return
        
        video_path = video_artifact['path']
        
        # Validate inputs
        title = self.title_entry.get().strip()
        if not title:
            messagebox.showerror("Error", "Please enter a video title")
            return
        
        # Get metadata
        description = self.desc_textbox.get("1.0", "end-1c").strip()
        tags_str = self.tags_entry.get().strip()
        tags = [t.strip() for t in tags_str.split(",")] if tags_str else None
        
        # Category mapping
        from ..processors.youtube_uploader import YouTubeUploader
        category_map = YouTubeUploader.CATEGORIES
        category_id = category_map.get(self.category_var.get(), "22")
        
        # Disable upload button
        self.upload_btn.configure(state="disabled")
        self.status_label.configure(text="Uploading...", text_color="yellow")
        
        # Upload in thread
        def upload_thread():
            def progress_callback(uploaded, total):
                progress = uploaded / total
                self.after(0, lambda: self._update_progress(progress))
            
            result = self.uploader.upload_video(
                video_path=video_path,
                title=title,
                description=description,
                tags=tags,
                category_id=category_id,
                privacy_status=self.privacy_var.get(),
                thumbnail_path=getattr(self, 'thumbnail_path', None),
                progress_callback=progress_callback
            )
            
            # Update UI from main thread
            self.after(0, lambda: self._upload_complete(result))
        
        threading.Thread(target=upload_thread, daemon=True).start()
    
    def _update_progress(self, progress: float):
        """Update progress bar."""
        self.progress_bar.set(progress)
        self.status_label.configure(
            text=f"Uploading... {progress*100:.0f}%",
            text_color="yellow"
        )
    
    def _upload_complete(self, result: Optional[dict]):
        """Handle upload completion."""
        self.upload_btn.configure(state="normal")
        
        if result:
            self.progress_bar.set(1.0)
            self.status_label.configure(
                text=f"✅ Uploaded successfully!",
                text_color="green"
            )
            
            messagebox.showinfo(
                "Upload Successful",
                f"Video uploaded!\n\n"
                f"Title: {result['title']}\n"
                f"URL: {result['url']}\n"
                f"Status: {result['status']}"
            )
        else:
            self.progress_bar.set(0)
            self.status_label.configure(
                text="❌ Upload failed",
                text_color="red"
            )
            
            messagebox.showerror(
                "Upload Failed",
                "Video upload failed. Check console for details."
            )
