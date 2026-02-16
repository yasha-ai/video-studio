"""
Gemini API Transcription & Text Processing Module

Provides cloud-based transcription using Google Gemini API.
Includes AI-powered text correction, timestamp generation, and highlight extraction.
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


class GeminiTranscriber:
    """
    Cloud transcription using Google Gemini API.
    
    Features:
    - Audio/video file transcription
    - AI-powered text correction (punctuation, formatting)
    - Timestamp generation
    - Highlight extraction
    - Progress tracking
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-2.5-flash",
        progress_callback: Optional[Callable[[float, str], None]] = None
    ):
        """
        Initialize GeminiTranscriber.
        
        Args:
            api_key: Google Gemini API key (or from env GOOGLE_GEMINI_API_KEY)
            model: Model name (default: gemini-2.5-flash)
            progress_callback: Callback(progress, status) for UI updates
        """
        api_key = api_key or os.getenv("GOOGLE_GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "Gemini API key required. "
                "Set GOOGLE_GEMINI_API_KEY environment variable or pass api_key parameter."
            )
        
        self.model_name = model
        self.progress_callback = progress_callback
        
        # Initialize Gemini client (new API)
        self.client = genai.Client(api_key=api_key)
        
        logger.info(f"GeminiTranscriber initialized with model: {model}")
    
    def _update_progress(self, progress: float, status: str):
        """Update progress via callback."""
        if self.progress_callback:
            self.progress_callback(progress, status)
        logger.debug(f"Progress: {progress:.0%} - {status}")
    
    def transcribe(
        self,
        audio_path: Path,
        language: Optional[str] = None,
        output_path: Optional[Path] = None
    ) -> str:
        """
        Transcribe audio/video file using Gemini API.
        
        Args:
            audio_path: Path to audio/video file
            language: Language code (optional, auto-detected if None)
            output_path: Path to save transcription (optional)
        
        Returns:
            Transcription text
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        self._update_progress(0.1, "Uploading audio file...")
        
        # Upload file to Gemini
        try:
            uploaded_file = self.client.files.upload(file=str(audio_path))
            self._update_progress(0.3, "Audio uploaded, waiting for processing...")
            
            # Wait for file to be processed
            import time
            while uploaded_file.state == "PROCESSING":
                time.sleep(1)
                uploaded_file = self.client.files.get(name=uploaded_file.name)
            
            if uploaded_file.state == "FAILED":
                raise RuntimeError(f"File processing failed")
            
            self._update_progress(0.5, "Transcribing audio...")
            
            # Create prompt for transcription
            lang_hint = f" (in {language})" if language else ""
            prompt = (
                f"Transcribe the following audio file{lang_hint}. "
                "Provide ONLY the transcription text, no additional commentary. "
                "Preserve all speech, including filler words and pauses."
            )
            
            # Generate transcription
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[uploaded_file, prompt]
            )
            transcription = response.text.strip()
            
            self._update_progress(0.9, "Transcription complete")
            
            # Save to file if requested
            if output_path:
                output_path.write_text(transcription, encoding="utf-8")
                logger.info(f"Transcription saved to: {output_path}")
            
            self._update_progress(1.0, "Done")
            
            return transcription
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise RuntimeError(f"Gemini transcription failed: {e}")
    
    def fix_transcription(
        self,
        text: str,
        output_path: Optional[Path] = None
    ) -> str:
        """
        Fix transcription using AI (punctuation, formatting, error correction).
        
        Args:
            text: Raw transcription text
            output_path: Path to save fixed text (optional)
        
        Returns:
            Fixed transcription text
        """
        self._update_progress(0.1, "Fixing transcription...")
        
        prompt = f"""Fix the following transcription text:

1. Add proper punctuation (commas, periods, question marks)
2. Fix capitalization
3. Correct obvious transcription errors
4. Format into readable paragraphs
5. Remove excessive filler words (um, uh, like) if too frequent
6. Keep the original meaning and content intact

Transcription:
{text}

Fixed transcription:"""
        
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            fixed_text = response.text.strip()
            
            self._update_progress(0.9, "Transcription fixed")
            
            # Save to file if requested
            if output_path:
                output_path.write_text(fixed_text, encoding="utf-8")
                logger.info(f"Fixed transcription saved to: {output_path}")
            
            self._update_progress(1.0, "Done")
            
            return fixed_text
            
        except Exception as e:
            logger.error(f"Transcription fix failed: {e}")
            raise RuntimeError(f"Failed to fix transcription: {e}")
    
    def generate_timestamps(
        self,
        audio_path: Path,
        transcription: str,
        output_path: Optional[Path] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate timestamps for transcription segments.
        
        Args:
            audio_path: Path to audio/video file
            transcription: Transcription text
            output_path: Path to save timestamps JSON (optional)
        
        Returns:
            List of timestamp segments: [{"start": 0.0, "end": 5.2, "text": "..."}]
        """
        self._update_progress(0.1, "Generating timestamps...")
        
        prompt = f"""Given the transcription below, generate logical segments with approximate timestamps.
Each segment should be 5-15 seconds long (estimate based on sentence length).
Provide output as JSON array with format: [{{"start": 0.0, "end": 5.2, "text": "sentence"}}]

Transcription:
{transcription}

Timestamps JSON:"""
        
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            response_text = response.text.strip()
            
            # Extract JSON from response (remove markdown code blocks if present)
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            timestamps = json.loads(response_text)
            
            self._update_progress(0.9, "Timestamps generated")
            
            # Save to file if requested
            if output_path:
                output_path.write_text(
                    json.dumps(timestamps, indent=2, ensure_ascii=False),
                    encoding="utf-8"
                )
                logger.info(f"Timestamps saved to: {output_path}")
            
            self._update_progress(1.0, "Done")
            
            return timestamps
            
        except Exception as e:
            logger.error(f"Timestamp generation failed: {e}")
            raise RuntimeError(f"Failed to generate timestamps: {e}")
    
    def extract_highlights(
        self,
        transcription: str,
        max_highlights: int = 5,
        output_path: Optional[Path] = None
    ) -> List[Dict[str, str]]:
        """
        Extract key highlights from transcription.
        
        Args:
            transcription: Transcription text
            max_highlights: Maximum number of highlights (default: 5)
            output_path: Path to save highlights JSON (optional)
        
        Returns:
            List of highlights: [{"timestamp": "00:05", "text": "...", "reason": "..."}]
        """
        self._update_progress(0.1, "Extracting highlights...")
        
        prompt = f"""Analyze the following transcription and extract the {max_highlights} most important highlights.
For each highlight:
1. Identify key moments (insights, important statements, actionable items)
2. Provide approximate timestamp (estimate based on position in text)
3. Explain why it's important

Provide output as JSON array: [{{"timestamp": "00:05", "text": "quote", "reason": "why important"}}]

Transcription:
{transcription}

Highlights JSON:"""
        
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            response_text = response.text.strip()
            
            # Extract JSON from response
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            highlights = json.loads(response_text)
            
            self._update_progress(0.9, "Highlights extracted")
            
            # Save to file if requested
            if output_path:
                output_path.write_text(
                    json.dumps(highlights, indent=2, ensure_ascii=False),
                    encoding="utf-8"
                )
                logger.info(f"Highlights saved to: {output_path}")
            
            self._update_progress(1.0, "Done")
            
            return highlights
            
        except Exception as e:
            logger.error(f"Highlight extraction failed: {e}")
            raise RuntimeError(f"Failed to extract highlights: {e}")


# CLI for standalone testing
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Gemini API Transcription CLI")
    parser.add_argument("audio", type=Path, help="Audio/video file to transcribe")
    parser.add_argument("--api-key", help="Gemini API key (or set GOOGLE_GEMINI_API_KEY)")
    parser.add_argument("--model", default="gemini-2.5-flash", help="Model name")
    parser.add_argument("--language", help="Language code (optional)")
    parser.add_argument("--output", "-o", type=Path, help="Output file path")
    parser.add_argument("--fix", action="store_true", help="Fix transcription after generation")
    parser.add_argument("--timestamps", action="store_true", help="Generate timestamps")
    parser.add_argument("--highlights", action="store_true", help="Extract highlights")
    
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    
    def progress_callback(progress: float, status: str):
        print(f"[{progress:.0%}] {status}")
    
    try:
        transcriber = GeminiTranscriber(
            api_key=args.api_key,
            model=args.model,
            progress_callback=progress_callback
        )
        
        # Transcribe
        transcription = transcriber.transcribe(
            audio_path=args.audio,
            language=args.language,
            output_path=args.output
        )
        
        print("\n=== Transcription ===")
        print(transcription)
        
        # Fix transcription if requested
        if args.fix:
            fixed_output = args.output.with_suffix(".fixed.txt") if args.output else None
            fixed_text = transcriber.fix_transcription(
                text=transcription,
                output_path=fixed_output
            )
            print("\n=== Fixed Transcription ===")
            print(fixed_text)
        
        # Generate timestamps if requested
        if args.timestamps:
            timestamps_output = args.output.with_suffix(".timestamps.json") if args.output else None
            timestamps = transcriber.generate_timestamps(
                audio_path=args.audio,
                transcription=transcription,
                output_path=timestamps_output
            )
            print(f"\n=== Timestamps ({len(timestamps)} segments) ===")
            for segment in timestamps[:3]:  # Show first 3
                print(f"{segment['start']:.1f}s - {segment['end']:.1f}s: {segment['text'][:50]}...")
        
        # Extract highlights if requested
        if args.highlights:
            highlights_output = args.output.with_suffix(".highlights.json") if args.output else None
            highlights = transcriber.extract_highlights(
                transcription=transcription,
                output_path=highlights_output
            )
            print(f"\n=== Highlights ({len(highlights)} items) ===")
            for hl in highlights:
                print(f"[{hl['timestamp']}] {hl['text'][:60]}...")
                print(f"  → {hl['reason']}")
        
        print("\n✅ Success!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        exit(1)
