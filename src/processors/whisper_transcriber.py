"""
Whisper Model Download & Transcription Module

Provides local transcription using OpenAI Whisper models.
Supports automatic model download and progress tracking.
"""

import os
import subprocess
from pathlib import Path
from typing import Optional, Callable, Dict, Any
import logging

logger = logging.getLogger(__name__)


class WhisperTranscriber:
    """
    Local transcription using OpenAI Whisper models.
    
    Features:
    - Automatic model download
    - Progress tracking
    - Multiple model sizes (tiny, base, small, medium, large)
    - Timestamp support
    - Language detection
    """
    
    MODELS = {
        "tiny": {"size_mb": 39, "ram_gb": 1, "speed": "fastest", "quality": "basic"},
        "base": {"size_mb": 74, "ram_gb": 1, "speed": "fast", "quality": "good"},
        "small": {"size_mb": 244, "ram_gb": 2, "speed": "medium", "quality": "better"},
        "medium": {"size_mb": 769, "ram_gb": 5, "speed": "slow", "quality": "great"},
        "large": {"size_mb": 1550, "ram_gb": 10, "speed": "slowest", "quality": "best"}
    }
    
    def __init__(
        self,
        model: str = "base",
        models_dir: Optional[Path] = None,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ):
        """
        Initialize WhisperTranscriber.
        
        Args:
            model: Model name (tiny, base, small, medium, large)
            models_dir: Directory to store models (default: ~/.cache/whisper)
            progress_callback: Callback(progress, status) for UI updates
        """
        if model not in self.MODELS:
            raise ValueError(f"Invalid model: {model}. Choose from: {list(self.MODELS.keys())}")
        
        self.model_name = model
        self.models_dir = models_dir or Path.home() / ".cache" / "whisper"
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.progress_callback = progress_callback
        
        # Model will be loaded on first transcription
        self._model = None
    
    def _update_progress(self, progress: float, status: str):
        """Update progress via callback."""
        if self.progress_callback:
            self.progress_callback(progress, status)
    
    def is_model_available(self) -> bool:
        """Check if model is already downloaded."""
        try:
            import whisper
            # Try to load model (will use cached version if available)
            whisper.load_model(self.model_name, download_root=str(self.models_dir))
            return True
        except Exception as e:
            logger.debug(f"Model not available: {e}")
            return False
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the selected model."""
        info = self.MODELS[self.model_name].copy()
        info["name"] = self.model_name
        info["available"] = self.is_model_available()
        info["models_dir"] = str(self.models_dir)
        return info
    
    def download_model(self) -> bool:
        """
        Download Whisper model if not already available.
        
        Returns:
            True if model is ready, False on error
        """
        if self.is_model_available():
            self._update_progress(100, f"Model '{self.model_name}' already available")
            return True
        
        try:
            import whisper
            
            model_info = self.MODELS[self.model_name]
            self._update_progress(0, f"Downloading {self.model_name} model ({model_info['size_mb']} MB)...")
            
            # Load model (will download if needed)
            self._model = whisper.load_model(
                self.model_name,
                download_root=str(self.models_dir)
            )
            
            self._update_progress(100, f"Model '{self.model_name}' ready!")
            return True
            
        except Exception as e:
            error_msg = f"Failed to download model: {e}"
            logger.error(error_msg)
            self._update_progress(0, error_msg)
            return False
    
    def transcribe(
        self,
        video_path: str,
        language: Optional[str] = None,
        timestamps: bool = True,
        output_path: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Transcribe video/audio file using Whisper.
        
        Args:
            video_path: Path to video or audio file
            language: Language code (e.g., 'en', 'ru') or None for auto-detect
            timestamps: Include word/segment timestamps
            output_path: Optional path to save transcription (text file)
        
        Returns:
            Dictionary with transcription results or None on error
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        # Ensure model is loaded
        if not self._model:
            if not self.download_model():
                return None
        
        try:
            import whisper
            
            if not self._model:
                self._update_progress(10, "Loading model...")
                self._model = whisper.load_model(
                    self.model_name,
                    download_root=str(self.models_dir)
                )
            
            self._update_progress(30, "Transcribing...")
            
            # Transcribe
            options = {
                "verbose": False,
                "word_timestamps": timestamps
            }
            if language:
                options["language"] = language
            
            result = self._model.transcribe(video_path, **options)
            
            self._update_progress(90, "Processing results...")
            
            # Prepare output
            output = {
                "text": result["text"],
                "language": result["language"],
                "segments": result.get("segments", []),
                "model": self.model_name
            }
            
            # Save to file if requested
            if output_path:
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(output["text"])
                logger.info(f"Transcription saved to: {output_path}")
            
            self._update_progress(100, "Transcription complete!")
            return output
            
        except Exception as e:
            error_msg = f"Transcription failed: {e}"
            logger.error(error_msg)
            self._update_progress(0, error_msg)
            return None
    
    def format_timestamps(self, segments: list) -> str:
        """
        Format segments with timestamps for display.
        
        Args:
            segments: List of segments from transcription result
        
        Returns:
            Formatted string with timestamps
        """
        lines = []
        for seg in segments:
            start = self._format_time(seg["start"])
            end = self._format_time(seg["end"])
            text = seg["text"].strip()
            lines.append(f"[{start} -> {end}] {text}")
        return "\n".join(lines)
    
    @staticmethod
    def _format_time(seconds: float) -> str:
        """Format seconds as HH:MM:SS."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def main():
    """CLI for testing WhisperTranscriber."""
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(description="Whisper Transcription Tool")
    parser.add_argument("video", help="Path to video/audio file")
    parser.add_argument("--model", default="base", choices=list(WhisperTranscriber.MODELS.keys()),
                       help="Whisper model to use (default: base)")
    parser.add_argument("--language", help="Language code (e.g., en, ru) or auto-detect")
    parser.add_argument("--output", "-o", help="Output file for transcription")
    parser.add_argument("--no-timestamps", action="store_true", help="Disable timestamps")
    parser.add_argument("--info", action="store_true", help="Show model info and exit")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s'
    )
    
    def progress_callback(progress: float, status: str):
        print(f"[{progress:.0f}%] {status}")
    
    # Create transcriber
    transcriber = WhisperTranscriber(
        model=args.model,
        progress_callback=progress_callback
    )
    
    # Show model info
    if args.info:
        info = transcriber.get_model_info()
        print(f"\nModel: {info['name']}")
        print(f"Size: {info['size_mb']} MB")
        print(f"RAM: ~{info['ram_gb']} GB")
        print(f"Speed: {info['speed']}")
        print(f"Quality: {info['quality']}")
        print(f"Available: {'✅ Yes' if info['available'] else '❌ No'}")
        print(f"Models directory: {info['models_dir']}")
        return
    
    # Check video file
    if not os.path.exists(args.video):
        print(f"Error: Video file not found: {args.video}", file=sys.stderr)
        sys.exit(1)
    
    # Transcribe
    print(f"\nTranscribing: {args.video}")
    print(f"Model: {args.model}\n")
    
    result = transcriber.transcribe(
        video_path=args.video,
        language=args.language,
        timestamps=not args.no_timestamps,
        output_path=args.output
    )
    
    if not result:
        print("Transcription failed!", file=sys.stderr)
        sys.exit(1)
    
    print(f"\n{'='*60}")
    print(f"Language: {result['language']}")
    print(f"{'='*60}\n")
    print(result["text"])
    
    if not args.no_timestamps and result.get("segments"):
        print(f"\n{'='*60}")
        print("TIMESTAMPS")
        print(f"{'='*60}\n")
        print(transcriber.format_timestamps(result["segments"]))
    
    if args.output:
        print(f"\nSaved to: {args.output}")


if __name__ == "__main__":
    main()
