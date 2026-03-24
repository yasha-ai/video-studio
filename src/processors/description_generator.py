"""
Description Generator Module

Generates optimized YouTube video descriptions using Google Gemini API
with multiple variants and customizable templates.
"""

import os
import re
import requests
from typing import Optional, List, Dict, Any


class DescriptionGenerator:
    """
    YouTube video description generator using Gemini 2.5 Flash.

    Features:
    - Generate multiple description variants (short, medium, full)
    - Include timestamps/chapters structure
    - Customizable footer template with links, social media, hashtags
    - Auto-generate relevant hashtags from content
    """

    # Gemini Text API endpoint
    API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

    # Default footer template
    DEFAULT_TEMPLATE = """{description_text}

Таймкоды:
{timestamps}

🔗 Полезные ссылки:
(заполните свои ссылки)

📱 Соцсети:
(заполните свои соцсети)

#youtube #видео {hashtags}"""

    # Description guidelines
    DESCRIPTION_GUIDELINES = {
        'max_length': 5000,  # YouTube limit
        'recommended_length': 1500,  # Optimal for SEO
        'min_length': 100,  # Minimum for meaningful content
        'first_lines_visible': 150,  # Characters visible before "Show more"
        'max_hashtags': 15,  # YouTube limit per description
        'recommended_hashtags': 5  # Optimal count
    }

    # Description variant types
    VARIANT_TYPES = {
        'short': 'Короткое описание (2-3 строки). Максимально ёмко передай суть видео.',
        'medium': 'Описание средней длины (абзац + таймкоды). Раскрой тему и добавь структуру.',
        'full': 'Подробное описание с главами. Полное описание содержания, ключевые моменты, для кого видео.'
    }

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Description Generator.

        Args:
            api_key: Google Gemini API key (or loaded from env GOOGLE_GEMINI_API_KEY)
        """
        self.api_key = api_key or os.getenv('GOOGLE_GEMINI_API_KEY') or os.getenv('GEMINI_API_KEY')
        # Note: API key is optional at init time, can be set later via set_api_key()
        # Methods will check for key before making API calls

    def set_api_key(self, api_key: str):
        """Set or update the Gemini API key."""
        self.api_key = api_key

    def generate_descriptions(
        self,
        transcript: Optional[str] = None,
        title: Optional[str] = None,
        count: int = 3,
        template: Optional[str] = None
    ) -> List[str]:
        """
        Generate multiple description variants optimized for YouTube.

        Generates 3 variants by default:
        1. Short (2-3 lines) — concise summary
        2. Medium (paragraph + timestamps) — balanced detail
        3. Full (detailed + chapters) — comprehensive description

        Args:
            transcript: Video transcript or summary
            title: Video title (for context)
            count: Number of description variants (1-3)
            template: Custom footer template (uses DEFAULT_TEMPLATE if None)

        Returns:
            List of generated description variants with applied template

        Raises:
            ValueError: If insufficient input data
            RuntimeError: If API call fails
        """
        if not transcript and not title:
            raise ValueError("Either transcript or title is required")

        if not 1 <= count <= 3:
            raise ValueError("Count must be between 1 and 3")

        used_template = template or self.DEFAULT_TEMPLATE

        # Determine which variants to generate
        variant_keys = list(self.VARIANT_TYPES.keys())[:count]

        # Build prompt
        prompt = self._build_generation_prompt(
            transcript=transcript,
            title=title,
            variant_keys=variant_keys
        )

        # Call API
        response_text = self._call_gemini_api(prompt)

        # Parse descriptions from response
        descriptions = self._parse_descriptions(response_text, variant_keys)

        # Apply template to each description
        result = []
        for desc_data in descriptions:
            formatted = self._apply_template(
                used_template,
                description_text=desc_data['text'],
                timestamps=desc_data['timestamps'],
                hashtags=desc_data['hashtags']
            )
            result.append(formatted)

        return result

    def _build_generation_prompt(
        self,
        transcript: Optional[str],
        title: Optional[str],
        variant_keys: List[str]
    ) -> str:
        """Build prompt for description generation."""

        prompt_parts = [
            "Сгенерируй описания для YouTube-видео на русском языке.",
            ""
        ]

        if title:
            prompt_parts.extend([
                f"НАЗВАНИЕ ВИДЕО: {title}",
                ""
            ])

        if transcript:
            # Use first 2000 chars of transcript for more context
            snippet = transcript[:2000] + ("..." if len(transcript) > 2000 else "")
            prompt_parts.extend([
                "ТРАНСКРИПТ ВИДЕО:",
                snippet,
                ""
            ])

        prompt_parts.extend([
            f"Сгенерируй {len(variant_keys)} вариантов описания:",
            ""
        ])

        for i, key in enumerate(variant_keys, 1):
            instruction = self.VARIANT_TYPES[key]
            prompt_parts.append(f"ВАРИАНТ {i} ({key.upper()}): {instruction}")

        prompt_parts.extend([
            "",
            "ТРЕБОВАНИЯ ДЛЯ КАЖДОГО ВАРИАНТА:",
            "- Первые 150 символов — самые важные (видны до 'Ещё')",
            "- Включи ключевые слова для SEO",
            "- Текст должен быть естественным и полезным",
            "- Для medium и full вариантов добавь таймкоды (если есть транскрипт, извлеки реальные темы)",
            "- Сгенерируй 3-5 релевантных хештегов на основе содержания",
            "",
            "ФОРМАТ ОТВЕТА (строго соблюдай):",
            ""
        ])

        for i, key in enumerate(variant_keys, 1):
            prompt_parts.extend([
                f"---VARIANT_{i}_START---",
                f"DESCRIPTION:",
                f"(текст описания для варианта {key})",
                f"TIMESTAMPS:",
                f"(таймкоды, по одному на строку, формат: 00:00 — Тема)",
                f"HASHTAGS:",
                f"(хештеги через пробел, начиная с #)",
                f"---VARIANT_{i}_END---",
                ""
            ])

        return "\n".join(prompt_parts)

    def _call_gemini_api(self, prompt: str, temperature: float = 0.7) -> str:
        """
        Call Gemini Text API.

        Args:
            prompt: Text prompt
            temperature: Creativity level (0.0-1.0)

        Returns:
            Response text

        Raises:
            RuntimeError: If API call fails or API key not set
        """
        if not self.api_key:
            raise RuntimeError(
                "Google Gemini API key not set. "
                "Please configure it in Settings or set GOOGLE_GEMINI_API_KEY environment variable."
            )

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
                "temperature": temperature,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 4096
            }
        }

        url = f"{self.API_URL}?key={self.api_key}"

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()

            result = response.json()

            # Extract text response
            if 'candidates' in result and len(result['candidates']) > 0:
                parts = result['candidates'][0].get('content', {}).get('parts', [])
                if parts and 'text' in parts[0]:
                    return parts[0]['text']

            raise RuntimeError("No text in API response")

        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Gemini API request failed: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to process API response: {e}")

    def _parse_descriptions(
        self,
        response_text: str,
        variant_keys: List[str]
    ) -> List[Dict[str, str]]:
        """Parse description variants from API response."""

        descriptions = []

        for i in range(1, len(variant_keys) + 1):
            # Extract variant block
            start_marker = f"---VARIANT_{i}_START---"
            end_marker = f"---VARIANT_{i}_END---"

            start_idx = response_text.find(start_marker)
            end_idx = response_text.find(end_marker)

            if start_idx != -1 and end_idx != -1:
                block = response_text[start_idx + len(start_marker):end_idx].strip()

                # Extract description text
                desc_text = self._extract_section(block, 'DESCRIPTION', 'TIMESTAMPS')
                timestamps = self._extract_section(block, 'TIMESTAMPS', 'HASHTAGS')
                hashtags = self._extract_section(block, 'HASHTAGS', None)

                descriptions.append({
                    'text': desc_text.strip() if desc_text else '',
                    'timestamps': timestamps.strip() if timestamps else '00:00 — Начало',
                    'hashtags': hashtags.strip() if hashtags else ''
                })
            else:
                # Fallback: try to parse without markers
                descriptions.append(self._fallback_parse(response_text, i, len(variant_keys)))

        # Ensure we have at least one result
        if not descriptions:
            descriptions.append({
                'text': response_text.strip(),
                'timestamps': '00:00 — Начало',
                'hashtags': '#youtube #видео'
            })

        return descriptions

    def _extract_section(
        self,
        block: str,
        section_name: str,
        next_section: Optional[str]
    ) -> str:
        """Extract a section from a parsed block."""

        pattern = rf'{section_name}:\s*\n?'
        match = re.search(pattern, block, re.IGNORECASE)

        if not match:
            return ''

        start = match.end()

        if next_section:
            next_pattern = rf'{next_section}:\s*'
            next_match = re.search(next_pattern, block[start:], re.IGNORECASE)
            if next_match:
                return block[start:start + next_match.start()].strip()

        return block[start:].strip()

    def _fallback_parse(
        self,
        response_text: str,
        variant_index: int,
        total_variants: int
    ) -> Dict[str, str]:
        """Fallback parsing when structured markers are not found."""

        # Try to split by variant labels
        lines = response_text.strip().split('\n')
        text_lines = [line for line in lines if line.strip()]

        if total_variants == 1:
            chunk = text_lines
        else:
            chunk_size = max(1, len(text_lines) // total_variants)
            start = (variant_index - 1) * chunk_size
            end = start + chunk_size if variant_index < total_variants else len(text_lines)
            chunk = text_lines[start:end]

        # Extract hashtags from chunk
        hashtags = []
        desc_lines = []
        for line in chunk:
            if re.match(r'^#\w+', line.strip()):
                hashtags.append(line.strip())
            else:
                desc_lines.append(line)

        return {
            'text': '\n'.join(desc_lines).strip(),
            'timestamps': '00:00 — Начало',
            'hashtags': ' '.join(hashtags) if hashtags else '#youtube #видео'
        }

    def _apply_template(
        self,
        template: str,
        description_text: str,
        timestamps: str,
        hashtags: str
    ) -> str:
        """Apply template to description data."""

        # Ensure hashtags always include base tags
        if '#youtube' not in hashtags:
            hashtags = hashtags.strip()

        result = template.replace('{description_text}', description_text)
        result = result.replace('{description text}', description_text)
        result = result.replace('{timestamps}', timestamps)
        result = result.replace('{timestamps or "00:00 — Начало"}', timestamps)
        result = result.replace('{generated hashtags based on content}', hashtags)
        result = result.replace('{hashtags}', hashtags)

        return result


# CLI for testing
if __name__ == '__main__':
    import argparse
    import json

    parser = argparse.ArgumentParser(description='YouTube Description Generator')
    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Generate command
    gen_parser = subparsers.add_parser('generate', help='Generate descriptions')
    gen_parser.add_argument('--transcript', '-t', help='Video transcript file')
    gen_parser.add_argument('--title', help='Video title')
    gen_parser.add_argument('--count', '-c', type=int, default=3,
                            help='Number of variants (1-3)')
    gen_parser.add_argument('--template', help='Custom template file')
    gen_parser.add_argument('--json', action='store_true', help='Output as JSON')

    args = parser.parse_args()

    # Initialize generator
    try:
        generator = DescriptionGenerator()
    except ValueError as e:
        print(f"Error: {e}")
        print("Set GOOGLE_GEMINI_API_KEY environment variable.")
        exit(1)

    # Load transcript if provided
    transcript = None
    if hasattr(args, 'transcript') and args.transcript:
        try:
            with open(args.transcript, 'r') as f:
                transcript = f.read()
        except Exception as e:
            print(f"Warning: Could not read transcript file: {e}")

    # Load custom template if provided
    template = None
    if hasattr(args, 'template') and args.template:
        try:
            with open(args.template, 'r') as f:
                template = f.read()
        except Exception as e:
            print(f"Warning: Could not read template file: {e}")

    # Execute command
    try:
        if args.command == 'generate':
            print(f"Generating {args.count} description variants...")
            descriptions = generator.generate_descriptions(
                transcript=transcript,
                title=args.title,
                count=args.count,
                template=template
            )

            if args.json:
                print(json.dumps(descriptions, indent=2, ensure_ascii=False))
            else:
                variant_names = ['SHORT', 'MEDIUM', 'FULL']
                print(f"\n--- Generated {len(descriptions)} description variants ---\n")
                for i, desc in enumerate(descriptions):
                    name = variant_names[i] if i < len(variant_names) else f'VARIANT {i + 1}'
                    print(f"{'=' * 60}")
                    print(f"  VARIANT {i + 1}: {name}")
                    print(f"{'=' * 60}")
                    print(desc)
                    print()

        else:
            parser.print_help()

    except Exception as e:
        print(f"\nError: {e}")
        exit(1)
