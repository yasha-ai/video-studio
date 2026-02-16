# AI Title Generation & Critique

**Module:** `src/processors/title_generator.py`  
**Status:** ✅ Complete  
**Last Updated:** 2024-02-16

---

## Overview

The Title Generator module uses Google Gemini 2.5 Flash API to generate optimized YouTube video titles and provide AI-powered critique and improvement suggestions.

### Features

- **Multi-variant Generation:** Generate 1-10 title variations per video
- **AI-Powered Critique:** Detailed analysis with scores (0-100) for SEO, engagement, and overall quality
- **Smart Improvements:** Automatic suggestions based on critique feedback
- **Style Options:** Engaging, Professional, Educational, Viral
- **YouTube Best Practices:** Built-in guidelines (length, power words, keyword placement)

---

## Architecture

### Class: `TitleGenerator`

```python
from processors.title_generator import TitleGenerator

generator = TitleGenerator(api_key='your_gemini_api_key')
```

**Initialization:**
- `api_key`: Google Gemini API key (optional if `GOOGLE_GEMINI_API_KEY` env variable is set)

---

## Core Methods

### 1. Generate Titles

Generate multiple optimized title variations from video content.

```python
titles = generator.generate_titles(
    transcript="Video transcript text...",  # Optional
    description="Video description",        # Optional (one of transcript/description required)
    keywords=['Python', 'Tutorial'],        # Optional SEO keywords
    target_audience='beginners',            # Optional audience description
    count=5,                                # Number of variations (1-10)
    style='engaging'                        # Style preset
)

# Returns: ['Title 1', 'Title 2', 'Title 3', ...]
```

**Styles:**
- `engaging` — Power words, emotional triggers, curiosity gaps (default)
- `professional` — Clear, direct, value-focused
- `educational` — Learning outcomes, "How to" patterns
- `viral` — Maximum curiosity and emotional appeal

**Requirements:**
- At least one of `transcript` or `description` must be provided
- Count must be 1-10
- Titles optimized for 50-60 characters (YouTube sweet spot)

---

### 2. Critique Title

Analyze an existing title with detailed feedback.

```python
critique = generator.critique_title(
    title="How to Learn Python in 2024",
    transcript="Optional video transcript for context",
    description="Optional video description",
    keywords=['Python', 'Tutorial']  # Optional for SEO check
)

# Returns:
{
    'score': 75,              # Overall score (0-100)
    'seo_score': 80,          # SEO optimization (0-100)
    'engagement_score': 70,   # Clickability/appeal (0-100)
    'length_check': True,     # Passes 70-char limit
    'strengths': [
        'Clear topic indication',
        'Year included for freshness'
    ],
    'weaknesses': [
        'Generic phrasing',
        'Missing power words'
    ],
    'suggestions': [
        'Add specific outcome (e.g., "in 30 Days")',
        'Include difficulty level keyword'
    ]
}
```

**Critique Factors:**
1. **SEO:** Keyword placement, searchability
2. **Engagement:** Clickability, curiosity, emotional appeal
3. **Length:** Optimal 50-60 chars, max 70
4. **Clarity:** Clear value proposition
5. **Accuracy:** Non-misleading, honest

---

### 3. Suggest Improvements

Generate improved versions based on critique.

```python
improved = generator.suggest_improvements(
    title="Python Tutorial",
    critique=None,  # Optional (will generate if None)
    count=3         # Number of improved versions (1-5)
)

# Returns: ['Improved Title 1', 'Improved Title 2', 'Improved Title 3']
```

**Improvement Process:**
1. Auto-critique if not provided
2. Address identified weaknesses
3. Implement suggestions
4. Maintain core message
5. Optimize length (50-60 chars)

---

## YouTube Best Practices

### Built-in Guidelines

```python
TitleGenerator.TITLE_GUIDELINES = {
    'max_length': 70,           # Hard limit before truncation
    'recommended_length': 60,   # Sweet spot for full visibility
    'min_length': 30,           # Minimum for meaningful content
    'avoid_clickbait': True,
    'use_numbers': True,        # Numbers increase CTR
    'use_power_words': True,    # Emotional triggers
    'front_load_keywords': True # Important words first
}
```

### Power Words

The module includes 16 proven power words:

- **Authority:** Ultimate, Complete, Essential, Expert, Mastering
- **Discovery:** Secret, Hidden, Revealed
- **Value:** Proven, Advanced, Best, Top, Must-Know
- **Accessibility:** Quick, Easy, Simple

---

## CLI Usage

The module includes a command-line interface for standalone use.

### Generate Titles

```bash
# Basic generation
python src/processors/title_generator.py generate \
  --description "Learn Python basics for beginners" \
  --count 5 \
  --style educational

# With transcript file
python src/processors/title_generator.py generate \
  --transcript tmp/transcript.txt \
  --keywords Python Tutorial Beginner \
  --audience "developers new to Python" \
  --count 3 \
  --style engaging

# Output:
# Generating 3 title variations...
# 
# ✅ Generated 3 titles:
# 
# 1. Python Basics: Complete Guide for Beginners in 2024
# 2. Learn Python Fast: Essential Tutorial for New Developers
# 3. Master Python Fundamentals: Beginner-Friendly Course
```

### Critique Title

```bash
# Basic critique
python src/processors/title_generator.py critique \
  "How to Learn Python"

# With context and JSON output
python src/processors/title_generator.py critique \
  "Python Tutorial for Beginners" \
  --transcript tmp/transcript.txt \
  --keywords Python Tutorial \
  --json

# Output (non-JSON):
# Critiquing title: "How to Learn Python"...
# 
# 📊 CRITIQUE RESULTS
# 
# Overall Score: 65/100
# SEO Score: 70/100
# Engagement Score: 60/100
# Length Check: ✅ PASS
# 
# ✅ STRENGTHS:
#   • Clear intent (learning)
#   • Simple and approachable
# 
# ⚠️  WEAKNESSES:
#   • Too generic
#   • Missing timeline/scope
#   • No power words
# 
# 💡 SUGGESTIONS:
#   • Add specific outcome or timeframe
#   • Include difficulty level
#   • Use engaging adjectives
```

### Suggest Improvements

```bash
python src/processors/title_generator.py improve \
  "Python Tutorial" \
  --count 3

# Output:
# Generating improvements for: "Python Tutorial"...
# 
# ✅ Improved versions:
# 
# 1. Complete Python Tutorial: Master Basics in 30 Days
# 2. Python Mastery: Essential Tutorial for Beginners
# 3. Learn Python Fast: Ultimate Guide for New Developers
```

---

## API Integration

### Gemini 2.5 Flash

**Endpoint:**  
`https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent`

**Authentication:**  
API key passed as URL parameter: `?key={api_key}`

**Request Format:**

```json
{
  "contents": [{
    "parts": [{
      "text": "prompt text here"
    }]
  }],
  "generationConfig": {
    "temperature": 0.7,
    "topK": 40,
    "topP": 0.95,
    "maxOutputTokens": 2048
  }
}
```

**Response Format:**

```json
{
  "candidates": [{
    "content": {
      "parts": [{
        "text": "generated text response"
      }]
    }
  }]
}
```

**Error Handling:**
- Network errors → `RuntimeError` with descriptive message
- Missing API key → `ValueError` on initialization
- Invalid response → `RuntimeError`

---

## Testing

### Run Tests

```bash
# Install pytest if needed
pip install pytest

# Run all tests
pytest tests/test_title_generator.py -v

# Run specific test
pytest tests/test_title_generator.py::TestTitleGenerator::test_generate_titles_basic -v

# Run only unit tests (skip integration)
pytest tests/test_title_generator.py -v -m "not integration"
```

### Test Categories

1. **Unit Tests:** No API calls, test internal logic
   - Prompt building
   - Response parsing
   - Input validation

2. **Integration Tests:** Real API calls (require valid API key)
   - Title generation
   - Critique functionality
   - Improvement suggestions

**Note:** Set `GOOGLE_GEMINI_API_KEY` environment variable for integration tests.

---

## Usage Examples

### Example 1: Generate Titles from Transcript

```python
from processors.title_generator import TitleGenerator

generator = TitleGenerator()

# Load transcript
with open('tmp/transcript.txt') as f:
    transcript = f.read()

# Generate 5 engaging titles
titles = generator.generate_titles(
    transcript=transcript,
    keywords=['Python', 'FastAPI', 'REST API'],
    target_audience='intermediate developers',
    count=5,
    style='professional'
)

print("Generated titles:")
for i, title in enumerate(titles, 1):
    print(f"{i}. {title}")
```

### Example 2: Full Critique & Improvement Pipeline

```python
original_title = "Python API Tutorial"

# 1. Critique original
critique = generator.critique_title(
    title=original_title,
    keywords=['Python', 'API', 'REST']
)

print(f"Score: {critique['score']}/100")
print(f"Weaknesses: {', '.join(critique['weaknesses'])}")

# 2. Generate improvements
if critique['score'] < 80:
    improved = generator.suggest_improvements(
        title=original_title,
        critique=critique,
        count=3
    )
    
    print("\nImproved titles:")
    for title in improved:
        print(f"  • {title}")
```

### Example 3: Batch Processing

```python
# Process multiple videos
videos = [
    {'id': 1, 'transcript': '...', 'desc': 'Python tutorial'},
    {'id': 2, 'transcript': '...', 'desc': 'React guide'},
    # ...
]

results = {}

for video in videos:
    titles = generator.generate_titles(
        transcript=video['transcript'],
        description=video['desc'],
        count=3,
        style='engaging'
    )
    
    # Critique each generated title
    best_title = None
    best_score = 0
    
    for title in titles:
        critique = generator.critique_title(title)
        if critique['score'] > best_score:
            best_score = critique['score']
            best_title = title
    
    results[video['id']] = {
        'title': best_title,
        'score': best_score,
        'alternatives': titles
    }

print(f"Processed {len(results)} videos")
```

---

## Dependencies

```python
# Standard library
import os
import re
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

# Third-party
import requests  # HTTP client for Gemini API
```

**Install:**

```bash
pip install requests
```

---

## Environment Variables

```bash
# Required for API access
export GOOGLE_GEMINI_API_KEY="your_api_key_here"
```

**Obtain API Key:**

1. Visit [Google AI Studio](https://ai.google.dev/aistudio)
2. Create/select project
3. Generate API key
4. Copy key to `.env` or export directly

---

## Error Handling

### Common Errors

**1. Missing API Key**

```python
ValueError: Google Gemini API key required.
```

**Fix:** Set `GOOGLE_GEMINI_API_KEY` environment variable or pass `api_key` parameter.

**2. Insufficient Input**

```python
ValueError: Either transcript or description is required
```

**Fix:** Provide at least one of `transcript` or `description`.

**3. API Request Failed**

```python
RuntimeError: Gemini API request failed: 401 Client Error
```

**Fix:** Check API key validity. Verify quota limits.

**4. Invalid Count**

```python
ValueError: Count must be between 1 and 10
```

**Fix:** Use valid count range (1-10 for generation, 1-5 for improvements).

---

## Performance

**Typical Response Times:**

- Title generation (5 titles): ~3-5 seconds
- Critique: ~2-3 seconds
- Improvements (3 suggestions): ~3-4 seconds

**Rate Limits:**

- Gemini API: 60 requests/minute (free tier)
- Consider batch processing for large volumes

**Cost Optimization:**

- Use lower `count` values when possible
- Cache frequently used critiques
- Reuse critique results for improvements

---

## Future Enhancements

### Planned Features

- [ ] A/B testing mode (compare title variants)
- [ ] Historical performance analysis (if YouTube Analytics integrated)
- [ ] Multi-language support
- [ ] Custom style templates
- [ ] Thumbnail-title consistency checker
- [ ] Trending topic detection

### Integration Points

- **UI Panel:** `src/ui/title_panel.py` (to be created)
- **Artifacts System:** Store generated titles in artifacts
- **YouTube Upload:** Auto-select best title on upload
- **Workflow:** Title generation as workflow step

---

## Support & Resources

**Documentation:**
- [Google Gemini API Docs](https://ai.google.dev/docs)
- [YouTube Title Best Practices](https://support.google.com/youtube/answer/6328248)

**Internal Links:**
- [Artifacts System](artifacts-system.md)
- [Workflow Panel](workflow-panel.md)

**Contact:**
- Module Maintainer: Yasha
- Created: 2024-02-16
- Repository: video-studio
