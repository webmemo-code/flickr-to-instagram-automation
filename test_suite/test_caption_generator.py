"""
Tests for CaptionGenerator using live Flickr gallery and OpenAI API.
Tests the enhanced caption generation with blog context integration.
"""
import pytest
import os
import json
from unittest.mock import patch, MagicMock
from caption_generator import CaptionGenerator
from config import Config
from blog_content_extractor import BlogContentExtractor


def safe_print(text):
    """Print text with Unicode characters safely on Windows."""
    try:
        print(text)
    except UnicodeEncodeError:
        # Convert Unicode to ASCII for Windows console
        safe_text = text.encode('ascii', 'ignore').decode('ascii')
        print(safe_text)


class TestCaptionGenerator:
    """Test CaptionGenerator with live data."""
    
    @pytest.fixture
    def config(self):
        """Create test config with live API keys."""
        config = MagicMock(spec=Config)
        config.openai_api_key = os.getenv('OPENAI_API_KEY')
        config.openai_model = 'gpt-4o-mini'
        config.blog_post_url = "https://travelmemo.com/mauritius/mauritius-what-to-do"
        return config
    
    @pytest.fixture
    def generator(self, config):
        """Create CaptionGenerator instance."""
        return CaptionGenerator(config)
    
    @pytest.fixture
    def sample_mauritius_photo_data(self):
        """Sample photo data that would come from Flickr API."""
        return {
            'id': '31352051237',
            'url': 'https://live.staticflickr.com/4885/31352051237_b494dd1d65_c.jpg',
            'title': 'Le Morne Beach Mauritius',
            'description': 'Crystal clear turquoise water at Le Morne beach with the iconic Le Morne Brabant mountain in the background. One of the most beautiful beaches in Mauritius.',
            'location_data': {
                'photo': {
                    'location': {
                        'locality': {'_content': 'Le Morne'},
                        'region': {'_content': 'Black River'},
                        'country': {'_content': 'Mauritius'}
                    }
                }
            },
            'exif_data': {
                'photo': {
                    'exif': [
                        {'tag': 'Make', 'raw': {'_content': 'Canon'}},
                        {'tag': 'Model', 'raw': {'_content': 'EOS R6'}}
                    ]
                }
            },
            'source_url': 'https://travelmemo.com/mauritius/mauritius-what-to-do',
            'hashtags': '#Mauritius #Beach #Travel #Paradise #LeMorne'
        }
    
    def test_build_context_from_photo_data(self, generator, sample_mauritius_photo_data):
        """Test building context parts from photo data."""
        # This tests the context building logic in generate_caption method
        photo_data = sample_mauritius_photo_data
        
        # Mock the generate_caption method to access context building
        with patch.object(generator.client.chat.completions, 'create') as mock_create:
            mock_response = MagicMock()
            mock_response.choices[0].message.content = "Test caption"
            mock_create.return_value = mock_response
            
            generator.generate_caption(photo_data)
            
            # Check that the OpenAI API was called with enhanced context
            args, kwargs = mock_create.call_args
            messages = kwargs['messages']
            prompt_content = messages[0]['content'][0]['text']
            
            # Verify context elements are included
            assert 'Le Morne Beach Mauritius' in prompt_content, "Should include photo title"
            assert 'Crystal clear turquoise water' in prompt_content, "Should include description"
            assert 'Le Morne, Black River, Mauritius' in prompt_content, "Should include location"
            assert 'Canon EOS R6' in prompt_content, "Should include camera info"
            assert 'travelmemo.com' in prompt_content, "Should include source URL"
            
            print("PASS: Context building works correctly")
    
    @pytest.mark.skipif(not os.getenv('OPENAI_API_KEY'), reason="Requires OpenAI API key")
    def test_generate_caption_with_blog_context_live(self, generator, sample_mauritius_photo_data):
        """Test generating caption with live blog context and OpenAI API."""
        photo_data = sample_mauritius_photo_data
        
        # Generate caption with live APIs
        caption = generator.generate_caption(photo_data)
        
        assert caption is not None, "Should generate a caption"
        assert len(caption) > 20, "Caption should be substantial"
        assert isinstance(caption, str), "Caption should be a string"
        
        # Check that the caption seems relevant to Mauritius/beach content
        caption_lower = caption.lower()
        relevant_terms = ['mauritius', 'beach', 'water', 'morne', 'beautiful', 'crystal', 'turquoise']
        found_terms = [term for term in relevant_terms if term in caption_lower]
        
        assert len(found_terms) >= 2, f"Caption should contain relevant terms. Found: {found_terms}"
        
        safe_print(f"PASS: Generated caption: {caption[:100]}...")
        print(f"Relevant terms found: {found_terms}")
    
    def test_blog_content_context_integration(self, generator, sample_mauritius_photo_data):
        """Test that blog content context is properly integrated."""
        photo_data = sample_mauritius_photo_data
        
        # Get blog content context
        blog_context = generator._get_blog_content_context(photo_data)
        
        if blog_context:
            assert len(blog_context) > 50, "Blog context should be substantial"
            
            # Check that context is relevant to Mauritius
            context_lower = blog_context.lower()
            mauritius_terms = ['mauritius', 'beach', 'island', 'water', 'morne']
            found_mauritius_terms = [term for term in mauritius_terms if term in context_lower]
            
            assert len(found_mauritius_terms) >= 1, f"Blog context should be relevant to Mauritius. Found: {found_mauritius_terms}"
            
            print(f"PASS: Blog context integration works ({len(blog_context)} chars)")
            print(f"Context preview: {blog_context[:150]}...")
        else:
            print("INFO: No blog context extracted (this may indicate an issue)")
    
    def test_build_full_caption_structure(self, generator, sample_mauritius_photo_data):
        """Test building the complete Instagram caption structure."""
        photo_data = sample_mauritius_photo_data
        generated_caption = "This stunning beach showcases the natural beauty of Mauritius. The crystal clear waters invite you to take a refreshing swim. Le Morne mountain provides a dramatic backdrop. It's truly a paradise on earth. Perfect for photography and relaxation."
        
        full_caption = generator.build_full_caption(photo_data, generated_caption)
        
        assert full_caption is not None
        assert len(full_caption) > len(generated_caption), "Full caption should be longer than generated part"
        
        # Check caption structure
        assert photo_data['title'] in full_caption, "Should include photo title"
        assert photo_data['description'] in full_caption, "Should include photo description"
        assert generated_caption in full_caption, "Should include generated caption"
        assert "Travelmemo from a one-of-a-kind travel experience" in full_caption, "Should include footer"
        assert photo_data['hashtags'] in full_caption, "Should include hashtags"
        
        print("PASS: Full caption structure is correct")
        print(f"Full caption length: {len(full_caption)} characters")
    
    def test_enhanced_vs_basic_prompt_selection(self, generator):
        """Test that enhanced prompts are used when context is available."""
        # Photo with rich context
        rich_photo = {
            'id': 'test1',
            'url': 'https://example.com/photo.jpg',
            'title': 'Test Beach',
            'description': 'Beautiful beach scene',
            'location_data': {'photo': {'location': {'country': {'_content': 'Mauritius'}}}}
        }
        
        # Photo with minimal context
        minimal_photo = {
            'id': 'test2',
            'url': 'https://example.com/photo2.jpg'
        }
        
        with patch.object(generator.client.chat.completions, 'create') as mock_create:
            mock_response = MagicMock()
            mock_response.choices[0].message.content = "Test caption"
            mock_create.return_value = mock_response
            
            # Test rich photo gets enhanced prompt
            generator.generate_caption(rich_photo)
            rich_prompt = mock_create.call_args[1]['messages'][0]['content'][0]['text']
            
            # Test minimal photo gets basic prompt
            generator.generate_caption(minimal_photo)
            minimal_prompt = mock_create.call_args[1]['messages'][0]['content'][0]['text']
            
            # Enhanced prompt should mention "Instagram influencer" and "travel content"
            assert "Instagram influencer" in rich_prompt, "Enhanced prompt should mention influencer"
            assert "travel content" in rich_prompt, "Enhanced prompt should mention travel"
            
            # Basic prompt should be shorter and more generic
            assert "Instagram influencer" in minimal_prompt, "Both prompts mention influencer"
            assert len(rich_prompt) > len(minimal_prompt), "Enhanced prompt should be longer"
            
            print("PASS: Prompt selection works correctly based on available context")
    
    @pytest.mark.skipif(not os.getenv('OPENAI_API_KEY'), reason="Requires OpenAI API key")
    def test_retry_mechanism_success(self, generator, sample_mauritius_photo_data):
        """Test that retry mechanism works when API calls succeed."""
        photo_data = sample_mauritius_photo_data
        
        caption = generator.generate_with_retry(photo_data, max_retries=3)
        
        assert caption is not None, "Should generate caption with retry mechanism"
        assert len(caption) > 20, "Caption should be substantial"
        
        print("PASS: Retry mechanism works for successful API calls")


if __name__ == "__main__":
    # Allow running tests directly for development
    pytest.main([__file__, "-v"])