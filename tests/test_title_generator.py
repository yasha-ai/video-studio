"""
Unit tests for Title Generator module.
"""

import pytest
import os
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from processors.title_generator import TitleGenerator


class TestTitleGenerator:
    """Test suite for TitleGenerator class."""
    
    @pytest.fixture
    def generator(self):
        """Create generator instance with API key from env."""
        api_key = os.getenv('GOOGLE_GEMINI_API_KEY')
        if not api_key:
            pytest.skip("GOOGLE_GEMINI_API_KEY not set")
        return TitleGenerator(api_key=api_key)
    
    def test_init_without_api_key(self):
        """Test initialization fails without API key."""
        # Temporarily remove env variable
        original_key = os.environ.pop('GOOGLE_GEMINI_API_KEY', None)
        
        try:
            with pytest.raises(ValueError, match="API key required"):
                TitleGenerator()
        finally:
            # Restore env variable
            if original_key:
                os.environ['GOOGLE_GEMINI_API_KEY'] = original_key
    
    def test_init_with_api_key(self):
        """Test initialization succeeds with API key."""
        generator = TitleGenerator(api_key='test_key_123')
        assert generator.api_key == 'test_key_123'
    
    def test_generate_titles_requires_input(self, generator):
        """Test generate_titles requires transcript or description."""
        with pytest.raises(ValueError, match="transcript or description"):
            generator.generate_titles()
    
    def test_generate_titles_count_validation(self, generator):
        """Test generate_titles validates count parameter."""
        with pytest.raises(ValueError, match="between 1 and 10"):
            generator.generate_titles(
                description="Test video",
                count=15
            )
    
    @pytest.mark.integration
    def test_generate_titles_basic(self, generator):
        """Test basic title generation (integration test)."""
        description = "Learn Python programming basics in this beginner-friendly tutorial"
        
        titles = generator.generate_titles(
            description=description,
            count=3,
            style='educational'
        )
        
        assert len(titles) > 0
        assert len(titles) <= 3
        
        # Check all titles are strings
        for title in titles:
            assert isinstance(title, str)
            assert len(title) > 10  # Reasonable minimum
    
    @pytest.mark.integration
    def test_generate_titles_with_keywords(self, generator):
        """Test title generation with keywords."""
        titles = generator.generate_titles(
            description="Advanced Next.js tutorial covering server components",
            keywords=['Next.js', 'React', 'Server Components'],
            count=2,
            style='professional'
        )
        
        assert len(titles) > 0
        
        # At least one title should mention keywords
        keywords_mentioned = any(
            'Next' in title or 'React' in title
            for title in titles
        )
        assert keywords_mentioned
    
    @pytest.mark.integration
    def test_critique_title(self, generator):
        """Test title critique functionality."""
        title = "How to Learn Python in 2024"
        
        critique = generator.critique_title(
            title=title,
            description="Python programming tutorial for beginners"
        )
        
        # Check critique structure
        assert 'score' in critique
        assert 'seo_score' in critique
        assert 'engagement_score' in critique
        assert 'strengths' in critique
        assert 'weaknesses' in critique
        assert 'suggestions' in critique
        assert 'length_check' in critique
        
        # Check scores are in valid range
        assert 0 <= critique['score'] <= 100
        assert 0 <= critique['seo_score'] <= 100
        assert 0 <= critique['engagement_score'] <= 100
        
        # Check lists are lists
        assert isinstance(critique['strengths'], list)
        assert isinstance(critique['weaknesses'], list)
        assert isinstance(critique['suggestions'], list)
        
        # Length check should pass (title is 27 chars)
        assert critique['length_check'] is True
    
    @pytest.mark.integration
    def test_critique_long_title(self, generator):
        """Test critique detects overly long titles."""
        long_title = "This is a very long YouTube title that definitely exceeds the recommended 70 character limit for optimal display"
        
        critique = generator.critique_title(title=long_title)
        
        # Should fail length check
        assert critique['length_check'] is False
    
    @pytest.mark.integration
    def test_suggest_improvements(self, generator):
        """Test improvement suggestions."""
        title = "Python Tutorial"
        
        improved = generator.suggest_improvements(
            title=title,
            count=2
        )
        
        assert len(improved) > 0
        assert len(improved) <= 2
        
        # Improved titles should be different from original
        for improved_title in improved:
            assert improved_title != title
            assert len(improved_title) > len(title)  # Should be more descriptive
    
    def test_parse_titles(self, generator):
        """Test title parsing from API response."""
        response = """
1. First Amazing Title
2. Second Great Title
3. Third Excellent Title
"""
        
        titles = generator._parse_titles(response, expected_count=3)
        
        assert len(titles) == 3
        assert titles[0] == "First Amazing Title"
        assert titles[1] == "Second Great Title"
        assert titles[2] == "Third Excellent Title"
    
    def test_parse_titles_with_quotes(self, generator):
        """Test parsing titles with quotes."""
        response = '''
1) "Title With Quotes"
2) 'Title With Single Quotes'
3. Title Without Quotes
'''
        
        titles = generator._parse_titles(response, expected_count=3)
        
        assert len(titles) == 3
        assert "Title With Quotes" in titles[0]
        assert "Title With Single Quotes" in titles[1]
        assert "Title Without Quotes" in titles[2]
    
    def test_parse_critique(self, generator):
        """Test critique parsing."""
        response = """
SCORE: 75
SEO_SCORE: 80
ENGAGEMENT_SCORE: 70

STRENGTHS:
- Clear and concise
- Good keyword placement

WEAKNESSES:
- Too generic
- Missing power words

SUGGESTIONS:
- Add specific numbers
- Include emotional triggers
"""
        
        critique = generator._parse_critique(response)
        
        assert critique['score'] == 75
        assert critique['seo_score'] == 80
        assert critique['engagement_score'] == 70
        assert len(critique['strengths']) == 2
        assert len(critique['weaknesses']) == 2
        assert len(critique['suggestions']) == 2
    
    def test_build_generation_prompt(self, generator):
        """Test generation prompt building."""
        prompt = generator._build_generation_prompt(
            transcript="This is a video about Python",
            description="Learn Python basics",
            keywords=['Python', 'Tutorial'],
            target_audience='beginners',
            count=3,
            style='educational'
        )
        
        # Check prompt contains key elements
        assert 'Python' in prompt
        assert 'educational' in prompt.lower()
        assert 'beginners' in prompt
        assert '3' in prompt
        assert 'Learn Python basics' in prompt
    
    def test_build_critique_prompt(self, generator):
        """Test critique prompt building."""
        prompt = generator._build_critique_prompt(
            title="Learn Python Fast",
            transcript="Video about Python programming",
            keywords=['Python', 'Programming']
        )
        
        # Check prompt structure
        assert 'Learn Python Fast' in prompt
        assert 'SCORE' in prompt
        assert 'SEO' in prompt
        assert 'ENGAGEMENT' in prompt
        assert 'Python' in prompt  # From transcript


# Integration test markers
pytestmark = pytest.mark.integration


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
