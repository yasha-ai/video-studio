"""
Cover Image Generator Module

Generates YouTube thumbnail images using Google Gemini Image API.
Supports multiple style variations and prompt templates.
"""

import os
import base64
import requests
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime


class CoverGenerator:
    """
    YouTube cover/thumbnail image generator using Gemini 2.5 Flash Image.
    
    Features:
    - Generate 1-4 cover variations
    - Custom prompts or template-based generation
    - Multiple artistic styles
    - Saves high-quality JPG/PNG images
    - Artifacts system integration
    """
    
    # Gemini Image API endpoint
    API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent"
    
    # Default image generation parameters
    DEFAULT_WIDTH = 1280
    DEFAULT_HEIGHT = 720  # YouTube thumbnail aspect ratio 16:9
    DEFAULT_FORMAT = 'image/jpeg'
    
    # Style templates for cover generation
    STYLE_TEMPLATES = {
        'modern': 'modern minimalist design with bold typography, clean lines, high contrast',
        'cinematic': 'cinematic movie poster style, dramatic lighting, epic composition',
        'vibrant': 'vibrant colorful aesthetic, energetic vibe, eye-catching elements',
        'professional': 'professional business style, clean layout, corporate colors',
        'creative': 'creative artistic design, unique visual elements, expressive colors',
        'dark': 'dark moody atmosphere, dramatic shadows, mysterious vibe',
        'bright': 'bright cheerful design, warm colors, inviting atmosphere',
        'tech': 'futuristic tech style, neon accents, digital elements'
    }
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Cover Generator.
        
        Args:
            api_key: Google Gemini API key (or loaded from env GOOGLE_GEMINI_API_KEY)
        """
        self.api_key = api_key or os.getenv('GOOGLE_GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError(
                "Google Gemini API key required. "
                "Set GOOGLE_GEMINI_API_KEY env variable or pass api_key parameter."
            )
    
    def generate_prompt(
        self,
        title: str,
        description: Optional[str] = None,
        style: str = 'modern',
        custom_elements: Optional[str] = None
    ) -> str:
        """
        Generate AI prompt for cover image based on video metadata.
        
        Args:
            title: Video title (main focus of the cover)
            description: Optional video description for context
            style: Visual style from STYLE_TEMPLATES or custom
            custom_elements: Additional custom prompt elements
        
        Returns:
            Complete prompt for image generation
        """
        # Get style template or use custom
        style_desc = self.STYLE_TEMPLATES.get(style, style)
        
        # Build prompt
        prompt_parts = [
            f"Create a YouTube thumbnail image for a video titled: \"{title}\"",
            f"Visual style: {style_desc}",
            "Requirements:",
            "- 1280x720 pixels (16:9 aspect ratio)",
            "- Bold, readable text for the title",
            "- Eye-catching visual composition",
            "- Professional quality",
            "- No watermarks or logos"
        ]
        
        if description:
            prompt_parts.insert(1, f"Video context: {description[:200]}")
        
        if custom_elements:
            prompt_parts.append(f"Additional elements: {custom_elements}")
        
        return "\n".join(prompt_parts)
    
    def generate_covers(
        self,
        title: str,
        description: Optional[str] = None,
        count: int = 4,
        styles: Optional[List[str]] = None,
        custom_prompts: Optional[List[str]] = None,
        output_dir: Optional[Path] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> List[Path]:
        """
        Generate multiple cover image variations.
        
        Args:
            title: Video title
            description: Video description (optional)
            count: Number of covers to generate (1-4)
            styles: List of styles to use (or auto-select if None)
            custom_prompts: Use custom prompts instead of generated ones
            output_dir: Directory to save images (default: tmp/thumbnails/)
            progress_callback: Optional callback(current, total, status_msg)
        
        Returns:
            List of Paths to generated image files
        
        Raises:
            ValueError: If count > 4 or invalid parameters
            RuntimeError: If API request fails
        """
        if not 1 <= count <= 4:
            raise ValueError("Cover count must be between 1 and 4")
        
        # Prepare output directory
        if output_dir is None:
            output_dir = Path('tmp/thumbnails')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Prepare prompts
        if custom_prompts:
            prompts = custom_prompts[:count]
        else:
            # Auto-select diverse styles
            if styles is None:
                default_styles = ['modern', 'cinematic', 'vibrant', 'creative']
                styles = default_styles[:count]
            else:
                styles = styles[:count]
            
            prompts = [
                self.generate_prompt(title, description, style)
                for style in styles
            ]
        
        # Generate covers
        generated_paths = []
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        for i, prompt in enumerate(prompts, 1):
            if progress_callback:
                progress_callback(i, count, f"Generating cover {i}/{count}...")
            
            # Call Gemini Image API
            image_data = self._call_gemini_api(prompt)
            
            # Save image
            filename = f"cover_{timestamp}_{i:02d}.jpg"
            filepath = output_dir / filename
            
            with open(filepath, 'wb') as f:
                f.write(image_data)
            
            generated_paths.append(filepath)
            
            if progress_callback:
                progress_callback(i, count, f"Saved: {filename}")
        
        return generated_paths
    
    def _call_gemini_api(self, prompt: str) -> bytes:
        """
        Call Gemini Image API to generate image from prompt.
        
        Args:
            prompt: Text prompt for image generation
        
        Returns:
            Image data as bytes (JPEG format)
        
        Raises:
            RuntimeError: If API call fails
        """
        headers = {
            'Content-Type': 'application/json'
        }
        
        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }],
            "generationConfig": {
                "temperature": 0.7,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 8192,
                "responseMimeType": "image/jpeg"
            }
        }
        
        url = f"{self.API_URL}?key={self.api_key}"
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            
            # Extract base64 image data
            if 'candidates' in result and len(result['candidates']) > 0:
                parts = result['candidates'][0].get('content', {}).get('parts', [])
                if parts and 'inlineData' in parts[0]:
                    b64_data = parts[0]['inlineData']['data']
                    return base64.b64decode(b64_data)
            
            raise RuntimeError("No image data in API response")
            
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Gemini API request failed: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to process API response: {e}")
    
    def get_available_styles(self) -> List[str]:
        """Get list of available style templates."""
        return list(self.STYLE_TEMPLATES.keys())


# CLI for testing
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate YouTube cover images')
    parser.add_argument('title', help='Video title')
    parser.add_argument('--description', '-d', help='Video description')
    parser.add_argument('--count', '-c', type=int, default=4, help='Number of covers (1-4)')
    parser.add_argument('--styles', '-s', nargs='+', help='Styles to use')
    parser.add_argument('--output', '-o', type=Path, help='Output directory')
    parser.add_argument('--list-styles', action='store_true', help='List available styles')
    
    args = parser.parse_args()
    
    # Initialize generator
    try:
        generator = CoverGenerator()
    except ValueError as e:
        print(f"Error: {e}")
        print("Set GOOGLE_GEMINI_API_KEY environment variable.")
        exit(1)
    
    # List styles if requested
    if args.list_styles:
        print("Available styles:")
        for style in generator.get_available_styles():
            print(f"  - {style}: {generator.STYLE_TEMPLATES[style]}")
        exit(0)
    
    # Progress callback
    def progress(current, total, message):
        print(f"[{current}/{total}] {message}")
    
    # Generate covers
    try:
        print(f"Generating {args.count} cover(s) for: {args.title}")
        paths = generator.generate_covers(
            title=args.title,
            description=args.description,
            count=args.count,
            styles=args.styles,
            output_dir=args.output,
            progress_callback=progress
        )
        
        print(f"\n✅ Successfully generated {len(paths)} cover(s):")
        for path in paths:
            print(f"  - {path}")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        exit(1)
