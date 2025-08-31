"""
Tests for BlogContentExtractor using live Mauritius blog URL.
Tests the blog content extraction and photo-blog matching functionality.
"""
import pytest
import os
from unittest.mock import patch, MagicMock
from blog_content_extractor import BlogContentExtractor
from config import Config


class TestBlogContentExtractor:
    """Test BlogContentExtractor with live Mauritius blog data."""
    
    @pytest.fixture
    def config(self):
        """Create test config with live blog URL."""
        config = MagicMock(spec=Config)
        config.blog_post_url = "https://travelmemo.com/mauritius/mauritius-what-to-do"
        return config
    
    @pytest.fixture
    def extractor(self, config):
        """Create BlogContentExtractor instance."""
        return BlogContentExtractor(config)
    
    def test_extract_blog_content_live_mauritius_url(self, extractor):
        """Test extracting content from live Mauritius blog URL."""
        blog_url = "https://travelmemo.com/mauritius/mauritius-what-to-do"
        
        content = extractor.extract_blog_content(blog_url)
        
        assert content is not None, "Should successfully extract blog content"
        assert content['url'] == blog_url
        assert 'title' in content
        assert 'paragraphs' in content
        assert 'images' in content
        assert 'headings' in content
        
        # Verify we got substantial content
        assert len(content['paragraphs']) > 0, "Should extract paragraphs from blog"
        assert any(len(p) > 100 for p in content['paragraphs']), "Should have substantial paragraph content"
        
        # Check for Mauritius-related content
        content_text = ' '.join(content['paragraphs']).lower()
        assert 'mauritius' in content_text, "Content should mention Mauritius"
        
        print(f"PASS: Extracted {len(content['paragraphs'])} paragraphs, {len(content['images'])} images")
        print(f"Title: {content['title']}")
    
    def test_extract_photo_keywords_mauritius_context(self, extractor):
        """Test keyword extraction from Mauritius photo context."""
        # Sample photo context that might come from Flickr
        photo_context = {
            'title': 'Le Morne Brabant Beach Mauritius',
            'description': 'Beautiful beach at Le Morne with crystal clear water and mountain views',
            'location_data': {
                'city': 'Le Morne',
                'region': 'Black River',
                'country': 'Mauritius'
            }
        }
        
        keywords = extractor._extract_photo_keywords(photo_context)
        
        assert len(keywords) > 0, "Should extract keywords from photo context"
        
        # Check for expected Mauritius-related keywords
        keywords_lower = [k.lower() for k in keywords]
        expected_keywords = ['morne', 'brabant', 'beach', 'mauritius', 'mountain', 'water']
        
        found_keywords = [k for k in expected_keywords if k in keywords_lower]
        assert len(found_keywords) >= 3, f"Should find relevant keywords. Found: {found_keywords}"
        
        print(f"PASS: Extracted keywords: {keywords}")
    
    def test_find_relevant_content_mauritius_beach_photo(self, extractor):
        """Test finding relevant blog content for a Mauritius beach photo."""
        # First extract the blog content
        blog_content = extractor.extract_blog_content("https://travelmemo.com/mauritius/mauritius-what-to-do")
        assert blog_content is not None, "Should extract blog content successfully"
        
        # Sample photo context for a Mauritius beach photo
        photo_context = {
            'title': 'Le Morne Beach Mauritius',
            'description': 'Beautiful beach with turquoise water and Le Morne mountain',
            'location_data': {
                'city': 'Le Morne',
                'region': 'Black River', 
                'country': 'Mauritius'
            }
        }
        
        relevant_content = extractor.find_relevant_content(blog_content, photo_context)
        
        assert relevant_content is not None, "Should find relevant content for Mauritius beach photo"
        assert len(relevant_content) > 50, "Should return substantial relevant content"
        
        # Check that the content contains beach/Le Morne related keywords
        content_lower = relevant_content.lower()
        beach_keywords = ['beach', 'le morne', 'water', 'mauritius', 'turquoise', 'crystal']
        found_beach_keywords = [k for k in beach_keywords if k in content_lower]
        
        assert len(found_beach_keywords) >= 2, f"Should contain beach-related content. Found: {found_beach_keywords}"
        
        print(f"PASS: Found relevant content ({len(relevant_content)} chars)")
        print(f"Content preview: {relevant_content[:200]}...")
    
    def test_score_text_relevance_mauritius_terms(self, extractor):
        """Test text relevance scoring with Mauritius-specific terms."""
        search_terms = ['mauritius', 'beach', 'morne', 'crystal', 'water']
        
        # High relevance text
        high_relevance = "The beautiful beaches of Mauritius offer crystal clear water, especially at Le Morne beach where you can see the mountain backdrop."
        high_score = extractor._score_text_relevance(high_relevance, search_terms)
        
        # Low relevance text  
        low_relevance = "This is some random text about something completely different and unrelated to the topic."
        low_score = extractor._score_text_relevance(low_relevance, search_terms)
        
        assert high_score > low_score, f"High relevance text should score higher ({high_score} vs {low_score})"
        assert high_score >= 6, f"Should get good score for relevant text: {high_score}"
        assert low_score == 0, f"Irrelevant text should score 0: {low_score}"
        
        print(f"PASS: Scoring works: relevant={high_score}, irrelevant={low_score}")
    
    def test_image_context_extraction_mauritius_blog(self, extractor):
        """Test extracting image context from Mauritius blog."""
        blog_content = extractor.extract_blog_content("https://travelmemo.com/mauritius/mauritius-what-to-do")
        assert blog_content is not None
        
        images = blog_content.get('images', [])
        
        if len(images) > 0:
            # Check that images have useful context
            images_with_context = [img for img in images if img.get('alt') or img.get('caption') or img.get('context')]
            assert len(images_with_context) > 0, "Should extract images with context"
            
            # Check for Mauritius-related image content
            for img in images_with_context[:3]:  # Check first 3 images
                img_text = ' '.join([
                    img.get('alt', ''),
                    img.get('caption', ''), 
                    img.get('context', '')
                ]).lower()
                
                if 'mauritius' in img_text or 'beach' in img_text or 'morne' in img_text:
                    print(f"PASS: Found relevant image context: {img_text[:100]}...")
                    break
            else:
                print("INFO: No obviously Mauritius-related image context found (this may be normal)")
        else:
            print("INFO: No images found in blog content")


if __name__ == "__main__":
    # Allow running tests directly for development
    pytest.main([__file__, "-v"])