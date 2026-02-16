"""
Title Generator & Critique Module

Generates optimized YouTube video titles using Google Gemini API
and provides AI-powered critique and improvement suggestions.
"""

import os
import requests
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime


class TitleGenerator:
    """
    YouTube video title generator and optimizer using Gemini 2.5 Flash.
    
    Features:
    - Generate multiple title variations from video metadata
    - Critique existing titles with detailed feedback
    - Suggest improvements based on YouTube best practices
    - SEO and engagement optimization
    """
    
    # Gemini Text API endpoint
    API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
    
    # YouTube title best practices
    TITLE_GUIDELINES = {
        'max_length': 70,  # Optimal length before truncation
        'recommended_length': 60,  # Sweet spot for full visibility
        'min_length': 30,  # Minimum for meaningful content
        'avoid_clickbait': True,
        'use_numbers': True,  # Numbers increase CTR
        'use_power_words': True,  # Emotional triggers
        'front_load_keywords': True  # Important words first
    }
    
    # Power words for engagement
    POWER_WORDS = [
        'Ultimate', 'Complete', 'Essential', 'Proven', 'Advanced',
        'Secret', 'Hidden', 'Revealed', 'Mastering', 'Expert',
        'Quick', 'Easy', 'Simple', 'Best', 'Top', 'Must-Know'
    ]
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Title Generator.
        
        Args:
            api_key: Google Gemini API key (or loaded from env GOOGLE_GEMINI_API_KEY)
        """
        self.api_key = api_key or os.getenv('GOOGLE_GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError(
                "Google Gemini API key required. "
                "Set GOOGLE_GEMINI_API_KEY env variable or pass api_key parameter."
            )
    
    def generate_titles(
        self,
        transcript: Optional[str] = None,
        description: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        target_audience: Optional[str] = None,
        count: int = 5,
        style: str = 'engaging'
    ) -> List[str]:
        """
        Generate multiple title variations optimized for YouTube.
        
        Args:
            transcript: Video transcript or summary
            description: Video description
            keywords: Target SEO keywords
            target_audience: Target audience description (e.g., "developers", "beginners")
            count: Number of title variations (1-10)
            style: Title style ('engaging', 'professional', 'educational', 'viral')
        
        Returns:
            List of generated title variations
        
        Raises:
            ValueError: If insufficient input data
            RuntimeError: If API call fails
        """
        if not transcript and not description:
            raise ValueError("Either transcript or description is required")
        
        if not 1 <= count <= 10:
            raise ValueError("Count must be between 1 and 10")
        
        # Build prompt
        prompt = self._build_generation_prompt(
            transcript=transcript,
            description=description,
            keywords=keywords,
            target_audience=target_audience,
            count=count,
            style=style
        )
        
        # Call API
        response_text = self._call_gemini_api(prompt)
        
        # Parse titles from response
        titles = self._parse_titles(response_text, count)
        
        return titles
    
    def critique_title(
        self,
        title: str,
        transcript: Optional[str] = None,
        description: Optional[str] = None,
        keywords: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Critique a title and provide detailed feedback.
        
        Args:
            title: Title to critique
            transcript: Video transcript (for context)
            description: Video description (for context)
            keywords: Target keywords (for SEO check)
        
        Returns:
            Dictionary with critique results:
            {
                'score': int (0-100),
                'strengths': List[str],
                'weaknesses': List[str],
                'suggestions': List[str],
                'seo_score': int (0-100),
                'engagement_score': int (0-100),
                'length_check': bool
            }
        """
        # Build critique prompt
        prompt = self._build_critique_prompt(
            title=title,
            transcript=transcript,
            description=description,
            keywords=keywords
        )
        
        # Call API
        response_text = self._call_gemini_api(prompt)
        
        # Parse critique
        critique = self._parse_critique(response_text)
        
        # Add basic checks
        critique['length_check'] = len(title) <= self.TITLE_GUIDELINES['max_length']
        
        return critique
    
    def suggest_improvements(
        self,
        title: str,
        critique: Optional[Dict[str, Any]] = None,
        count: int = 3
    ) -> List[str]:
        """
        Suggest improved versions of a title.
        
        Args:
            title: Original title
            critique: Optional critique results (will generate if None)
            count: Number of improved versions (1-5)
        
        Returns:
            List of improved title suggestions
        """
        if critique is None:
            critique = self.critique_title(title)
        
        # Build improvement prompt
        prompt = f"""
Improve this YouTube video title based on the following critique:

ORIGINAL TITLE: "{title}"

CRITIQUE:
- Overall Score: {critique.get('score', 'N/A')}/100
- Weaknesses: {', '.join(critique.get('weaknesses', []))}
- Suggestions: {', '.join(critique.get('suggestions', []))}

Generate {count} improved versions that address the weaknesses and implement the suggestions.
Each title should:
- Be 50-60 characters long (optimal for YouTube)
- Front-load important keywords
- Use power words for engagement
- Be accurate and non-clickbait
- Maintain the core message

Return ONLY the {count} improved titles, one per line, numbered 1-{count}.
"""
        
        # Call API
        response_text = self._call_gemini_api(prompt)
        
        # Parse improved titles
        improved = self._parse_titles(response_text, count)
        
        return improved
    
    def _build_generation_prompt(
        self,
        transcript: Optional[str],
        description: Optional[str],
        keywords: Optional[List[str]],
        target_audience: Optional[str],
        count: int,
        style: str
    ) -> str:
        """Build prompt for title generation."""
        
        # Style-specific instructions
        style_instructions = {
            'engaging': 'Use power words, emotional triggers, and curiosity gaps. Make viewers WANT to click.',
            'professional': 'Use clear, direct language. Focus on value proposition and expertise.',
            'educational': 'Highlight learning outcomes. Use "How to", "Learn", "Guide" patterns.',
            'viral': 'Maximize curiosity and emotional appeal. Use numbers, questions, or bold claims (but stay accurate).'
        }
        
        instruction = style_instructions.get(style, style_instructions['engaging'])
        
        # Build prompt
        prompt_parts = [
            f"Generate {count} optimized YouTube video titles.",
            "",
            f"STYLE: {style.upper()}",
            f"INSTRUCTIONS: {instruction}",
            "",
            "REQUIREMENTS:",
            "- 50-60 characters (optimal length)",
            "- Front-load important keywords",
            "- Include numbers if relevant",
            "- Use power words (Ultimate, Complete, Essential, etc.)",
            "- Be accurate and non-clickbait",
            "- Optimize for SEO and CTR"
        ]
        
        if transcript:
            # Use first 1000 chars of transcript
            snippet = transcript[:1000] + ("..." if len(transcript) > 1000 else "")
            prompt_parts.extend([
                "",
                "VIDEO CONTENT (transcript):",
                snippet
            ])
        
        if description:
            prompt_parts.extend([
                "",
                "VIDEO DESCRIPTION:",
                description[:500]
            ])
        
        if keywords:
            prompt_parts.extend([
                "",
                f"TARGET KEYWORDS: {', '.join(keywords)}"
            ])
        
        if target_audience:
            prompt_parts.extend([
                "",
                f"TARGET AUDIENCE: {target_audience}"
            ])
        
        prompt_parts.extend([
            "",
            f"Return ONLY {count} titles, one per line, numbered 1-{count}.",
            "Do not include explanations or additional text."
        ])
        
        return "\n".join(prompt_parts)
    
    def _build_critique_prompt(
        self,
        title: str,
        transcript: Optional[str],
        description: Optional[str],
        keywords: Optional[List[str]]
    ) -> str:
        """Build prompt for title critique."""
        
        prompt_parts = [
            "Critique this YouTube video title and provide detailed feedback.",
            "",
            f'TITLE: "{title}"',
            "",
            "Analyze the title based on:",
            "1. SEO optimization (keyword placement, searchability)",
            "2. Engagement potential (clickability, curiosity, emotional appeal)",
            "3. Length (optimal is 50-60 characters)",
            "4. Clarity (clear value proposition)",
            "5. Accuracy (no misleading clickbait)",
            "",
            "Provide your critique in this format:",
            "",
            "SCORE: [0-100]",
            "SEO_SCORE: [0-100]",
            "ENGAGEMENT_SCORE: [0-100]",
            "",
            "STRENGTHS:",
            "- [strength 1]",
            "- [strength 2]",
            "...",
            "",
            "WEAKNESSES:",
            "- [weakness 1]",
            "- [weakness 2]",
            "...",
            "",
            "SUGGESTIONS:",
            "- [suggestion 1]",
            "- [suggestion 2]",
            "..."
        ]
        
        if transcript:
            snippet = transcript[:500] + ("..." if len(transcript) > 500 else "")
            prompt_parts.extend([
                "",
                "VIDEO CONTENT (for context):",
                snippet
            ])
        
        if description:
            prompt_parts.extend([
                "",
                "VIDEO DESCRIPTION:",
                description[:300]
            ])
        
        if keywords:
            prompt_parts.extend([
                "",
                f"TARGET KEYWORDS: {', '.join(keywords)}"
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
                "temperature": temperature,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 2048
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
    
    def _parse_titles(self, response_text: str, expected_count: int) -> List[str]:
        """Parse titles from API response."""
        lines = response_text.strip().split('\n')
        titles = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Remove numbering (1., 2., 1), etc.)
            import re
            cleaned = re.sub(r'^\d+[\.)]\s*', '', line)
            
            # Remove quotes
            cleaned = cleaned.strip('"').strip("'")
            
            if cleaned and len(cleaned) > 10:  # Sanity check
                titles.append(cleaned)
        
        # Return requested count (or all if fewer)
        return titles[:expected_count] if len(titles) >= expected_count else titles
    
    def _parse_critique(self, response_text: str) -> Dict[str, Any]:
        """Parse critique from API response."""
        import re
        
        critique = {
            'score': 0,
            'seo_score': 0,
            'engagement_score': 0,
            'strengths': [],
            'weaknesses': [],
            'suggestions': []
        }
        
        # Extract scores
        score_match = re.search(r'SCORE:\s*(\d+)', response_text, re.IGNORECASE)
        if score_match:
            critique['score'] = int(score_match.group(1))
        
        seo_match = re.search(r'SEO_SCORE:\s*(\d+)', response_text, re.IGNORECASE)
        if seo_match:
            critique['seo_score'] = int(seo_match.group(1))
        
        eng_match = re.search(r'ENGAGEMENT_SCORE:\s*(\d+)', response_text, re.IGNORECASE)
        if eng_match:
            critique['engagement_score'] = int(eng_match.group(1))
        
        # Extract lists
        def extract_list(section_name: str) -> List[str]:
            pattern = rf'{section_name}:\s*\n((?:[-•]\s*.+\n?)+)'
            match = re.search(pattern, response_text, re.IGNORECASE | re.MULTILINE)
            if match:
                items = match.group(1).strip().split('\n')
                return [re.sub(r'^[-•]\s*', '', item.strip()) for item in items if item.strip()]
            return []
        
        critique['strengths'] = extract_list('STRENGTHS')
        critique['weaknesses'] = extract_list('WEAKNESSES')
        critique['suggestions'] = extract_list('SUGGESTIONS')
        
        return critique


# CLI for testing
if __name__ == '__main__':
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description='YouTube Title Generator & Critic')
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Generate command
    gen_parser = subparsers.add_parser('generate', help='Generate titles')
    gen_parser.add_argument('--transcript', '-t', help='Video transcript file')
    gen_parser.add_argument('--description', '-d', help='Video description')
    gen_parser.add_argument('--keywords', '-k', nargs='+', help='Target keywords')
    gen_parser.add_argument('--audience', '-a', help='Target audience')
    gen_parser.add_argument('--count', '-c', type=int, default=5, help='Number of titles')
    gen_parser.add_argument('--style', '-s', default='engaging', 
                           choices=['engaging', 'professional', 'educational', 'viral'])
    
    # Critique command
    crit_parser = subparsers.add_parser('critique', help='Critique a title')
    crit_parser.add_argument('title', help='Title to critique')
    crit_parser.add_argument('--transcript', '-t', help='Video transcript file')
    crit_parser.add_argument('--description', '-d', help='Video description')
    crit_parser.add_argument('--keywords', '-k', nargs='+', help='Target keywords')
    crit_parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    # Improve command
    imp_parser = subparsers.add_parser('improve', help='Suggest improvements')
    imp_parser.add_argument('title', help='Title to improve')
    imp_parser.add_argument('--count', '-c', type=int, default=3, help='Number of suggestions')
    
    args = parser.parse_args()
    
    # Initialize generator
    try:
        generator = TitleGenerator()
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
    
    # Execute command
    try:
        if args.command == 'generate':
            print(f"Generating {args.count} title variations...")
            titles = generator.generate_titles(
                transcript=transcript,
                description=args.description,
                keywords=args.keywords,
                target_audience=args.audience,
                count=args.count,
                style=args.style
            )
            
            print(f"\n✅ Generated {len(titles)} titles:\n")
            for i, title in enumerate(titles, 1):
                print(f"{i}. {title}")
        
        elif args.command == 'critique':
            print(f"Critiquing title: \"{args.title}\"...")
            critique = generator.critique_title(
                title=args.title,
                transcript=transcript,
                description=args.description,
                keywords=args.keywords
            )
            
            if args.json:
                print(json.dumps(critique, indent=2))
            else:
                print(f"\n📊 CRITIQUE RESULTS\n")
                print(f"Overall Score: {critique['score']}/100")
                print(f"SEO Score: {critique['seo_score']}/100")
                print(f"Engagement Score: {critique['engagement_score']}/100")
                print(f"Length Check: {'✅ PASS' if critique['length_check'] else '❌ FAIL (too long)'}")
                
                if critique['strengths']:
                    print(f"\n✅ STRENGTHS:")
                    for s in critique['strengths']:
                        print(f"  • {s}")
                
                if critique['weaknesses']:
                    print(f"\n⚠️  WEAKNESSES:")
                    for w in critique['weaknesses']:
                        print(f"  • {w}")
                
                if critique['suggestions']:
                    print(f"\n💡 SUGGESTIONS:")
                    for s in critique['suggestions']:
                        print(f"  • {s}")
        
        elif args.command == 'improve':
            print(f"Generating improvements for: \"{args.title}\"...")
            improved = generator.suggest_improvements(
                title=args.title,
                count=args.count
            )
            
            print(f"\n✅ Improved versions:\n")
            for i, title in enumerate(improved, 1):
                print(f"{i}. {title}")
        
        else:
            parser.print_help()
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        exit(1)
