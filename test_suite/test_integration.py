"""
Integration tests for the complete caption generation pipeline.
Tests the full flow from Flickr gallery to enhanced captions using live data.
"""
import pytest
import os
import logging
from unittest.mock import patch, MagicMock
from config import Config
from flickr_api import FlickrAPI
from caption_generator import CaptionGenerator
from blog_content_extractor import BlogContentExtractor


def safe_print(text):
    """Print text with Unicode characters safely on Windows."""
    try:
        print(text)
    except UnicodeEncodeError:
        # Convert Unicode to ASCII for Windows console
        safe_text = text.encode('ascii', 'ignore').decode('ascii')
        print(safe_text)


class TestCaptionGenerationIntegration:
    """Integration tests using live Flickr gallery 72157674455663497 and Mauritius blog."""
    
    @pytest.fixture
    def config(self):
        """Create config with live API credentials and test URLs."""
        # Use real Config object but override test-specific values
        config = Config()
        
        # Override test-specific configuration
        config.flickr_album_id = '72157674455663497'  # Test gallery ID  
        config.blog_post_url = 'https://travelmemo.com/mauritius/mauritius-what-to-do'
        
        return config
    
    @pytest.fixture
    def flickr_api(self, config):
        """Create FlickrAPI instance."""
        if not config.flickr_api_key:
            pytest.skip("Requires FLICKR_API_KEY environment variable")
        return FlickrAPI(config)
    
    @pytest.fixture 
    def caption_generator(self, config):
        """Create CaptionGenerator instance."""
        if not config.openai_api_key:
            pytest.skip("Requires OPENAI_API_KEY environment variable")
        return CaptionGenerator(config)
    
    def test_flickr_gallery_photo_retrieval(self, flickr_api, config):
        """Test retrieving photos from the live Flickr gallery."""
        gallery_id = config.flickr_album_id
        
        # Get photos from the gallery
        photos = flickr_api.get_unposted_photos()
        
        assert photos is not None, f"Should retrieve photos from gallery {gallery_id}"
        assert len(photos) > 0, f"Gallery {gallery_id} should contain photos"
        
        # Check first photo structure
        first_photo = photos[0]
        required_fields = ['id', 'url', 'title']
        for field in required_fields:
            assert field in first_photo, f"Photo should have {field} field"
        
        print(f"PASS: Retrieved {len(photos)} photos from gallery {gallery_id}")
        print(f"First photo: {first_photo.get('title', 'No title')} (ID: {first_photo.get('id')})")
    
    def test_enhanced_photo_metadata_collection(self, flickr_api, config):
        """Test collecting enhanced metadata for photos from the gallery."""
        # Get a photo from the gallery
        photos = flickr_api.get_unposted_photos()
        assert len(photos) > 0
        
        first_photo = photos[0]
        photo_id = first_photo['id']
        
        # Get enhanced metadata
        enhanced_photo = flickr_api.get_photo_with_metadata(photo_id)
        
        assert enhanced_photo is not None, "Should get enhanced photo metadata"
        
        # Check for enhanced fields
        expected_fields = ['id', 'url', 'title', 'description']
        for field in expected_fields:
            assert field in enhanced_photo, f"Enhanced photo should have {field}"
        
        # Check for additional metadata
        metadata_fields = ['location_data', 'exif_data']
        metadata_found = [field for field in metadata_fields if enhanced_photo.get(field)]
        
        print(f"PASS: Enhanced metadata collected for photo {photo_id}")
        print(f"Available metadata: {list(enhanced_photo.keys())}")
        print(f"Additional metadata found: {metadata_found}")
    
    def test_blog_context_matching_with_flickr_photo(self, flickr_api, caption_generator, config):
        """Test matching blog content with actual Flickr photo from the gallery."""
        # Get a photo from the gallery
        photos = flickr_api.get_unposted_photos()
        assert len(photos) > 0
        
        # Get enhanced metadata for the first photo
        first_photo = photos[0]
        enhanced_photo = first_photo  # Already has enhanced metadata from get_unposted_photos()
        
        # Add blog URL to photo data
        enhanced_photo['source_url'] = config.blog_post_url
        
        # Get blog context for this photo
        blog_context = caption_generator._get_blog_content_context(enhanced_photo)
        
        if blog_context:
            assert len(blog_context) > 20, "Blog context should be substantial"
            
            # Check if context seems relevant to the photo
            photo_title = enhanced_photo.get('title', '').lower()
            photo_desc = enhanced_photo.get('description', '').lower()
            context_lower = blog_context.lower()
            
            # Look for overlap in keywords
            photo_keywords = []
            if photo_title:
                photo_keywords.extend(photo_title.split())
            if photo_desc:
                photo_keywords.extend(photo_desc.split())
            
            # Filter out common words
            meaningful_keywords = [k for k in photo_keywords if len(k) > 3]
            
            if meaningful_keywords:
                matches = [k for k in meaningful_keywords if k in context_lower]
                print(f"PASS: Blog context matching: found {len(matches)} keyword matches")
                print(f"Matches: {matches}")
            else:
                print("INFO: No meaningful keywords found in photo metadata for matching")
                
            print(f"Blog context preview: {blog_context[:200]}...")
        else:
            print("WARN: No blog context extracted - this may indicate an issue with blog content extraction")
    
    @pytest.mark.skipif(not os.getenv('OPENAI_API_KEY'), reason="Requires OpenAI API key") 
    def test_end_to_end_caption_generation(self, flickr_api, caption_generator, config):
        """Test complete end-to-end caption generation with live data."""
        # Get photo from gallery
        photos = flickr_api.get_unposted_photos()
        assert len(photos) > 0
        
        # Get enhanced photo metadata
        first_photo = photos[0]
        enhanced_photo = first_photo  # Already has enhanced metadata from get_unposted_photos()
        
        # Add blog URL
        enhanced_photo['source_url'] = config.blog_post_url
        enhanced_photo['hashtags'] = '#Mauritius #Travel #Beach #Paradise'
        
        # Generate caption
        generated_caption = caption_generator.generate_caption(enhanced_photo)
        
        assert generated_caption is not None, "Should generate a caption"
        assert len(generated_caption) > 30, "Generated caption should be substantial"
        
        # Build full Instagram caption
        full_caption = caption_generator.build_full_caption(enhanced_photo, generated_caption)
        
        assert full_caption is not None, "Should build full caption"
        assert len(full_caption) > len(generated_caption), "Full caption should be longer"
        
        # Check caption quality
        caption_lower = full_caption.lower()
        
        # Should contain some relevant terms (either from photo or blog)
        relevant_terms = ['mauritius', 'beach', 'water', 'beautiful', 'paradise', 'island', 'crystal', 'travel']
        found_terms = [term for term in relevant_terms if term in caption_lower]
        
        print(f"PASS: End-to-end caption generation successful!")
        print(f"Photo: {enhanced_photo.get('title', 'No title')} (ID: {enhanced_photo.get('id')})")
        print(f"Generated caption length: {len(generated_caption)} chars")
        print(f"Full caption length: {len(full_caption)} chars")
        print(f"Relevant terms found: {found_terms}")
        print(f"\\n--- FULL CAPTION ---")
        safe_print(full_caption)
        print(f"--- END CAPTION ---\\n")
        
        # Basic quality checks
        assert len(found_terms) >= 2, f"Caption should contain relevant terms. Found: {found_terms}"
        
    def test_caption_quality_with_vs_without_blog_context(self, flickr_api, config):
        """Compare caption quality with and without blog context."""
        if not os.getenv('OPENAI_API_KEY'):
            pytest.skip("Requires OpenAI API key")
            
        # Get photo from gallery
        photos = flickr_api.get_unposted_photos()
        enhanced_photo = flickr_api.get_photo_with_metadata(photos[0]['id'])
        
        # Test with blog context
        config_with_blog = MagicMock(spec=Config)
        config_with_blog.openai_api_key = config.openai_api_key
        config_with_blog.openai_model = config.openai_model
        config_with_blog.blog_post_url = config.blog_post_url
        
        generator_with_blog = CaptionGenerator(config_with_blog)
        enhanced_photo['source_url'] = config.blog_post_url
        caption_with_blog = generator_with_blog.generate_caption(enhanced_photo)
        
        # Test without blog context
        config_without_blog = MagicMock(spec=Config)
        config_without_blog.openai_api_key = config.openai_api_key
        config_without_blog.openai_model = config.openai_model
        config_without_blog.blog_post_url = None
        
        generator_without_blog = CaptionGenerator(config_without_blog)
        enhanced_photo_no_blog = enhanced_photo.copy()
        enhanced_photo_no_blog.pop('source_url', None)
        caption_without_blog = generator_without_blog.generate_caption(enhanced_photo_no_blog)
        
        # Compare results
        assert caption_with_blog is not None and caption_without_blog is not None
        
        print(f"\\n=== CAPTION COMPARISON ===")
        print(f"Photo: {enhanced_photo.get('title', 'No title')}")
        print(f"\\n--- WITH BLOG CONTEXT ({len(caption_with_blog)} chars) ---")
        safe_print(caption_with_blog)
        print(f"\\n--- WITHOUT BLOG CONTEXT ({len(caption_without_blog)} chars) ---")
        safe_print(caption_without_blog)
        print(f"\\n=== END COMPARISON ===\\n")
        
        # Both should be different (unless blog context extraction failed)
        if caption_with_blog != caption_without_blog:
            print("PASS: Blog context produces different captions")
        else:
            print("WARN: Captions are identical - blog context may not be working")


if __name__ == "__main__":
    # Allow running tests directly for development
    pytest.main([__file__, "-v", "-s"])