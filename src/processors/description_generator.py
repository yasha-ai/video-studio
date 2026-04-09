"""
Description Generator Module

Generates optimized YouTube video descriptions using Google Gemini API
with multiple variants and customizable templates.
"""

import logging
import os
import re
import requests
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


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

    # Default social links
    DEFAULT_SOCIAL_LINKS = """📱 Соцсети:
Telegram: https://t.me/daonejuniorday
⚡️ Поддержать меня на Boosty: https://boosty.to/sovit"""

    # Default footer template
    DEFAULT_TEMPLATE = """{description_text}

Таймкоды:
{timestamps}

Полезные ссылки:
{useful_links}

{social_links}

#youtube #видео {hashtags}"""

    # Verified links for technologies (only real, official URLs)
    TECH_LINKS = {
        "node.js":      ("Node.js",       "https://nodejs.org/"),
        "nodejs":       ("Node.js",       "https://nodejs.org/"),
        "npm":          ("npm",           "https://www.npmjs.com/"),
        "typescript":   ("TypeScript",    "https://www.typescriptlang.org/"),
        "react":        ("React",         "https://react.dev/"),
        "next.js":      ("Next.js",       "https://nextjs.org/"),
        "nextjs":       ("Next.js",       "https://nextjs.org/"),
        "vue":          ("Vue.js",        "https://vuejs.org/"),
        "vue.js":       ("Vue.js",        "https://vuejs.org/"),
        "svelte":       ("Svelte",        "https://svelte.dev/"),
        "angular":      ("Angular",       "https://angular.dev/"),
        "python":       ("Python",        "https://www.python.org/"),
        "django":       ("Django",        "https://www.djangoproject.com/"),
        "fastapi":      ("FastAPI",       "https://fastapi.tiangolo.com/"),
        "flask":        ("Flask",         "https://flask.palletsprojects.com/"),
        "docker":       ("Docker",        "https://www.docker.com/"),
        "kubernetes":   ("Kubernetes",    "https://kubernetes.io/"),
        "git":          ("Git",           "https://git-scm.com/"),
        "github":       ("GitHub",        "https://github.com/"),
        "vscode":       ("VS Code",       "https://code.visualstudio.com/"),
        "vs code":      ("VS Code",       "https://code.visualstudio.com/"),
        "postgresql":   ("PostgreSQL",    "https://www.postgresql.org/"),
        "postgres":     ("PostgreSQL",    "https://www.postgresql.org/"),
        "mongodb":      ("MongoDB",       "https://www.mongodb.com/"),
        "redis":        ("Redis",         "https://redis.io/"),
        "tailwind":     ("Tailwind CSS",  "https://tailwindcss.com/"),
        "webpack":      ("Webpack",       "https://webpack.js.org/"),
        "vite":         ("Vite",          "https://vite.dev/"),
        "eslint":       ("ESLint",        "https://eslint.org/"),
        "prettier":     ("Prettier",      "https://prettier.io/"),
        "jest":         ("Jest",          "https://jestjs.io/"),
        "linux":        ("Linux",         "https://www.linux.org/"),
        "nginx":        ("Nginx",         "https://nginx.org/"),
        "rust":         ("Rust",          "https://www.rust-lang.org/"),
        "go":           ("Go",            "https://go.dev/"),
        "golang":       ("Go",            "https://go.dev/"),
        "java":         ("Java",          "https://dev.java/"),
        "kotlin":       ("Kotlin",        "https://kotlinlang.org/"),
        "swift":        ("Swift",         "https://www.swift.org/"),
        "flutter":      ("Flutter",       "https://flutter.dev/"),
        "dart":         ("Dart",          "https://dart.dev/"),
        "graphql":      ("GraphQL",       "https://graphql.org/"),
        "prisma":       ("Prisma",        "https://www.prisma.io/"),
        "sqlalchemy":   ("SQLAlchemy",    "https://www.sqlalchemy.org/"),
        "express":      ("Express.js",    "https://expressjs.com/"),
        "nestjs":       ("NestJS",        "https://nestjs.com/"),
        "aws":          ("AWS",           "https://aws.amazon.com/"),
        "firebase":     ("Firebase",      "https://firebase.google.com/"),
        "supabase":     ("Supabase",      "https://supabase.com/"),
        "vercel":       ("Vercel",        "https://vercel.com/"),
        "figma":        ("Figma",         "https://www.figma.com/"),
        "sass":         ("Sass",          "https://sass-lang.com/"),
        "scss":         ("Sass",          "https://sass-lang.com/"),
        "pnpm":         ("pnpm",          "https://pnpm.io/"),
        "yarn":         ("Yarn",          "https://yarnpkg.com/"),
        "bun":          ("Bun",           "https://bun.sh/"),
        "deno":         ("Deno",          "https://deno.com/"),
        "tsconfig":     ("tsconfig",      "https://www.typescriptlang.org/tsconfig/"),
    }

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
        'full': 'Подробное описание с главами. Полное описание содержания, ключевые моменты, для кого видео.',
        'seo': 'SEO-оптимизированное описание. Максимум ключевых слов естественно вплетены в текст, первые 2 строки — самые важные.',
        'storytelling': 'Описание в формате истории. Зацепи зрителя с первой строки, создай интригу, подведи к просмотру.',
        'tutorial': 'Описание для туториала. Чёткий список того, что зритель узнает, пререквизиты, уровень сложности.',
        'engagement': 'Описание с фокусом на вовлечение. Вопросы к аудитории, призывы к комментариям, CTA на подписку.',
        'minimal': 'Минималистичное описание (1-2 строки + таймкоды). Только суть, без воды.',
        'professional': 'Профессиональное описание. Экспертный тон, ссылки на документацию, для опытной аудитории.',
    }

    def __init__(self, api_key: Optional[str] = None, social_links: Optional[str] = None):
        """
        Initialize Description Generator.

        Args:
            api_key: Google Gemini API key (or loaded from env GOOGLE_GEMINI_API_KEY)
            social_links: Custom social links block for description footer
                          (defaults to DEFAULT_SOCIAL_LINKS)
        """
        self.api_key = api_key or os.getenv('GOOGLE_GEMINI_API_KEY') or os.getenv('GEMINI_API_KEY')
        self.social_links = social_links if social_links is not None else self.DEFAULT_SOCIAL_LINKS
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

        if not 1 <= count <= 9:
            raise ValueError("Count must be between 1 and 9")

        used_template = template or self.DEFAULT_TEMPLATE

        # Determine which variants to generate
        variant_keys = list(self.VARIANT_TYPES.keys())[:count]

        logger.info(f"Generating {len(variant_keys)} descriptions")

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

        # Extract useful links from transcript
        useful_links = self._extract_useful_links(transcript or "")

        # Apply template to each description
        result = []
        for desc_data in descriptions:
            formatted = self._apply_template(
                used_template,
                description_text=desc_data['text'],
                timestamps=desc_data['timestamps'],
                hashtags=desc_data['hashtags'],
                useful_links=useful_links,
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
            prompt_parts.extend([
                "ТРАНСКРИПТ ВИДЕО (с таймкодами в формате SRT):",
                transcript,
                "",
                "ВАЖНО: Используй ВСЕ таймкоды из транскрипта для генерации главной структуры видео.",
                "Таймкоды должны покрывать всё видео от начала до конца, а не только первую минуту!",
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
            "- ПЕРВЫЕ 2 СТРОКИ — самые важные! Они видны на YouTube без клика 'Ещё'. Должны цеплять и содержать ключевые слова.",
            "- Включи ключевые слова для SEO в первые предложения",
            "- Текст должен быть естественным и полезным",
            "- ОБЯЗАТЕЛЬНО включи таймкоды прямо в описание (YouTube делает их кликабельными)",
            "- Добавь призыв к подписке/лайку (CTA)",
            "- Сгенерируй 3-5 релевантных хештегов на основе содержания",
            "- НИКОГДА не используй треугольные скобки < > ! YouTube удаляет их как HTML.",
            "  Вместо Generic<T> пиши Generic(T), вместо Array<string> — Array string.",
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
            logger.error(f"API call failed: {e}")
            raise RuntimeError(f"Gemini API request failed: {e}")
        except Exception as e:
            logger.error(f"API call failed: {e}")
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

    def _extract_useful_links(self, transcript: str) -> str:
        """Extract verified useful links based on technologies mentioned in transcript."""
        if not transcript:
            return ""

        text_lower = transcript.lower()
        found = {}  # name -> url (dedup by name)

        for keyword, (name, url) in self.TECH_LINKS.items():
            if keyword in text_lower and name not in found:
                found[name] = url

        logger.info(f"Extracted {len(found)} useful links from transcript")
        logger.debug(f"Links: {list(found.keys())}")

        if not found:
            return ""

        lines = [f"  {name}: {url}" for name, url in found.items()]
        return "\n".join(lines)

    def _apply_template(
        self,
        template: str,
        description_text: str,
        timestamps: str,
        hashtags: str,
        useful_links: str = "",
    ) -> str:
        """Apply template to description data."""

        if '#youtube' not in hashtags:
            hashtags = hashtags.strip()

        result = template.replace('{description_text}', description_text)
        result = result.replace('{description text}', description_text)
        result = result.replace('{timestamps}', timestamps)
        result = result.replace('{timestamps or "00:00 — Начало"}', timestamps)
        result = result.replace('{social_links}', self.social_links)
        result = result.replace('{generated hashtags based on content}', hashtags)
        result = result.replace('{hashtags}', hashtags)
        result = result.replace('{useful_links}', useful_links)

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
