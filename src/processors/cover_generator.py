"""
Cover Image Generator Module

Generates YouTube thumbnail images using Google Gemini Image API.
Supports multiple style variations and prompt templates.
"""

import logging
import os
import io
from pathlib import Path
from typing import Optional, List, Callable
from datetime import datetime

logger = logging.getLogger(__name__)

from google import genai
from google.genai import types
from PIL import Image


class CoverGenerator:
    """
    YouTube cover/thumbnail image generator using Gemini Image API.

    Features:
    - Generate 1-4 cover variations
    - Custom prompts or template-based generation
    - Multiple artistic styles
    - Saves high-quality PNG images
    - Reference image support (e.g. avatar)
    """

    DEFAULT_WIDTH = 1280
    DEFAULT_HEIGHT = 720

    STYLE_TEMPLATES = {
        'modern': 'современный минималистичный дизайн с крупной типографикой, чистые линии, высокий контраст',
        'cinematic': 'кинематографичный стиль постера, драматичное освещение, эпичная композиция',
        'vibrant': 'яркая красочная эстетика, энергичная атмосфера, привлекающие внимание элементы',
        'professional': 'профессиональный деловой стиль, чистая компоновка, корпоративные цвета',
        'creative': 'креативный художественный дизайн, уникальные визуальные элементы, выразительные цвета',
        'dark': 'тёмная атмосфера с неоновыми акцентами, код/терминал на фоне, загадочный tech-вайб',
        'bright': 'светлый жизнерадостный дизайн, тёплые цвета, приветливая атмосфера',
        'tech': 'футуристичный tech-стиль, неоновые акценты, цифровые элементы',
        'cozy': 'уютный lifestyle — автор за компьютером/ноутбуком в домашнем офисе или кофейне, тёплое освещение, чашка кофе, атмосфера обучения, код на экране если тема программирования',
    }

    # Preferred image models in order of priority
    IMAGE_MODELS = [
        "gemini-3-pro-image-preview",
        "gemini-3.1-flash-image-preview",
        "gemini-2.5-flash-image",
    ]

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('GOOGLE_GEMINI_API_KEY') or os.getenv('GEMINI_API_KEY')
        self.model = os.getenv('NANO_BANANA_MODEL') or os.getenv('GEMINI_MODEL') or ""
        self._client = None
        self._model_resolved = False

    def set_api_key(self, api_key: str):
        """Set or update the Gemini API key."""
        self.api_key = api_key
        self._client = None
        self._model_resolved = False

    def set_model(self, model: str):
        """Set model explicitly."""
        self.model = model
        self._model_resolved = True

    def _get_client(self) -> genai.Client:
        """Get or create Gemini client."""
        if self._client is None:
            if not self.api_key:
                raise RuntimeError(
                    "Google Gemini API key not set. "
                    "Please configure it in Settings or set GEMINI_API_KEY environment variable."
                )
            base_url = os.getenv('GOOGLE_GEMINI_BASE_URL')
            if base_url:
                self._client = genai.Client(api_key=self.api_key, http_options={"base_url": base_url})
            else:
                self._client = genai.Client(api_key=self.api_key)
        return self._client

    def _resolve_model(self):
        """Auto-detect best available image model if none set."""
        if self._model_resolved and self.model:
            return
        if self.model:
            self._model_resolved = True
            return

        # Try each model until one works
        client = self._get_client()
        for candidate in self.IMAGE_MODELS:
            try:
                client.models.generate_content(
                    model=candidate,
                    contents=["Test"],
                    config=types.GenerateContentConfig(
                        response_modalities=["TEXT"],
                    ),
                )
                self.model = candidate
                self._model_resolved = True
                logger.info(f"Auto-selected model: {candidate}")
                return
            except Exception as e:
                logger.error(f"Cover generation failed: {e}")
                continue

        # Fallback
        self.model = self.IMAGE_MODELS[0]
        self._model_resolved = True

    @classmethod
    def list_available_models(cls, api_key: Optional[str] = None) -> List[str]:
        """Query API for available image generation models."""
        key = api_key or os.getenv('GOOGLE_GEMINI_API_KEY') or os.getenv('GEMINI_API_KEY')
        if not key:
            return cls.IMAGE_MODELS
        try:
            import requests
            resp = requests.get(
                f"https://generativelanguage.googleapis.com/v1beta/models?key={key}",
                timeout=10,
            )
            if resp.status_code == 200:
                models = []
                for m in resp.json().get("models", []):
                    name = m["name"].replace("models/", "")
                    if "image" in name.lower() and "generateContent" in str(m.get("supportedGenerationMethods", [])):
                        models.append(name)
                logger.info(f"Available models: {models}")
                return models if models else cls.IMAGE_MODELS
        except Exception as e:
            logger.error(f"Cover generation failed: {e}")
        return cls.IMAGE_MODELS

    def generate_prompt(
        self,
        title: str,
        description: Optional[str] = None,
        style: str = 'modern',
        custom_elements: Optional[str] = None
    ) -> str:
        style_desc = self.STYLE_TEMPLATES.get(style, style)

        prompt_parts = [
            f"Создай обложку (thumbnail) для YouTube-видео с названием: \"{title}\"",
            f"Визуальный стиль: {style_desc}",
            "Требования:",
            "- 1280x720 пикселей (16:9)",
            "- Крупный, читаемый текст заголовка НА РУССКОМ ЯЗЫКЕ (IT-термины вроде TypeScript, React, Git можно на английском)",
            "- Привлекающая внимание композиция",
            "- Профессиональное качество",
            "- Без водяных знаков и логотипов",
        ]

        if description:
            prompt_parts.insert(1, f"Контекст видео: {description[:200]}")

        if custom_elements:
            prompt_parts.append(f"Дополнительные элементы: {custom_elements}")

        return "\n".join(prompt_parts)

    def generate_covers(
        self,
        title: str,
        description: Optional[str] = None,
        count: int = 9,
        styles: Optional[List[str]] = None,
        custom_prompts: Optional[List[str]] = None,
        output_dir: Optional[Path] = None,
        reference_image_path: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> List[Path]:
        """
        Generate multiple cover image variations.

        Args:
            title: Video title
            description: Video description (optional)
            count: Number of covers to generate (1-9)
            styles: List of styles to use (or auto-select if None)
            custom_prompts: Use custom prompts instead of generated ones
            output_dir: Directory to save images
            reference_image_path: Path to reference image (e.g. avatar) to include in generation
            progress_callback: Optional callback(current, total, status_msg)

        Returns:
            List of Paths to generated image files
        """
        logger.info(f"Generating {count} covers, model={self.model}")

        if not 1 <= count <= 9:
            raise ValueError("Cover count must be between 1 and 9")

        if output_dir is None:
            output_dir = Path('tmp/thumbnails')
        output_dir.mkdir(parents=True, exist_ok=True)

        # Prepare prompts
        if custom_prompts:
            prompts = custom_prompts[:count]
        else:
            if styles is None:
                default_styles = ['modern', 'cinematic', 'vibrant', 'professional', 'creative', 'dark', 'bright', 'tech', 'cozy']
                styles = default_styles[:count]
            else:
                styles = styles[:count]

            prompts = [
                self.generate_prompt(title, description, style)
                for style in styles
            ]

        # Load reference image if provided
        ref_image = None
        if reference_image_path and Path(reference_image_path).exists():
            ref_image = Image.open(reference_image_path)

        client = self._get_client()
        self._resolve_model()
        generated_paths = []
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        for i, prompt in enumerate(prompts, 1):
            if progress_callback:
                progress_callback(i, count, f"Generating cover {i}/{count}...")

            image_data = self._generate_image(client, prompt, ref_image)

            filename = f"cover_{timestamp}_{i:02d}.png"
            filepath = output_dir / filename

            image_data.save(filepath, "PNG")
            logger.info(f"Cover {i}/{count} saved: {filepath}")
            generated_paths.append(filepath)

            if progress_callback:
                progress_callback(i, count, f"Saved: {filename}")

        return generated_paths

    def _generate_image(self, client: genai.Client, prompt: str, ref_image: Optional[Image.Image] = None) -> Image.Image:
        """Generate a single image using Gemini API."""
        contents = [prompt]
        if ref_image is not None:
            contents.append(ref_image)

        response = client.models.generate_content(
            model=self.model,
            contents=contents,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(aspect_ratio="16:9"),
            ),
        )

        if not response.candidates or not response.candidates[0].content.parts:
            raise RuntimeError("No image generated in response")

        part = response.candidates[0].content.parts[0]
        if not hasattr(part, "inline_data") or not part.inline_data:
            raise RuntimeError("No image data in response")

        return Image.open(io.BytesIO(part.inline_data.data))

    def get_available_styles(self) -> List[str]:
        """Get list of available style templates."""
        return list(self.STYLE_TEMPLATES.keys())


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Generate YouTube cover images')
    parser.add_argument('title', help='Video title')
    parser.add_argument('--description', '-d', help='Video description')
    parser.add_argument('--count', '-c', type=int, default=9, help='Number of covers (1-9)')
    parser.add_argument('--styles', '-s', nargs='+', help='Styles to use')
    parser.add_argument('--output', '-o', type=Path, help='Output directory')
    parser.add_argument('--reference', '-r', help='Reference image path (e.g. avatar)')
    parser.add_argument('--list-styles', action='store_true', help='List available styles')

    args = parser.parse_args()

    generator = CoverGenerator()

    if args.list_styles:
        print("Available styles:")
        for style in generator.get_available_styles():
            print(f"  - {style}: {generator.STYLE_TEMPLATES[style]}")
        exit(0)

    def progress(current, total, message):
        print(f"[{current}/{total}] {message}")

    try:
        print(f"Generating {args.count} cover(s) for: {args.title}")
        paths = generator.generate_covers(
            title=args.title,
            description=args.description,
            count=args.count,
            styles=args.styles,
            output_dir=args.output,
            reference_image_path=args.reference,
            progress_callback=progress
        )

        print(f"\nSuccessfully generated {len(paths)} cover(s):")
        for path in paths:
            print(f"  - {path}")

    except Exception as e:
        print(f"\nError: {e}")
        exit(1)
