"""
Integration tests for the complete caption generation pipeline.
Tests the full flow from Flickr gallery to enhanced captions using live data.
"""
import os

import pytest

from config import Config
from flickr_api import FlickrAPI
from caption_generator import CaptionGenerator
from blog_content_extractor import BlogContextMatch
from conftest import safe_print

pytestmark = pytest.mark.live_api


class TestCaptionGenerationIntegration:
    """Integration tests using live Flickr gallery 72157674455663497 and Mauritius blog."""

    @pytest.fixture
    def config(self):
        """Create config with live API credentials and test URLs."""
        config = Config()
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
        if not config.anthropic_api_key:
            pytest.skip("Requires ANTHROPIC_API_KEY environment variable")
        return CaptionGenerator(config)

    def test_flickr_gallery_photo_retrieval(self, flickr_api, config):
        """Test retrieving photos from the live Flickr gallery."""
        gallery_id = config.flickr_album_id

        photos = flickr_api.get_photo_list()

        assert photos is not None, f"Should retrieve photos from gallery {gallery_id}"
        assert len(photos) > 0, f"Gallery {gallery_id} should contain photos"

        first_photo = photos[0]
        assert first_photo.id, "Photo should have an id"
        assert first_photo.url, "Photo should have a url"
        assert first_photo.title is not None, "Photo should have a title"

        print(f"PASS: Retrieved {len(photos)} photos from gallery {gallery_id}")
        print(f"First photo: {first_photo.title or 'No title'} (ID: {first_photo.id})")

    def test_enhanced_photo_metadata_collection(self, flickr_api, config):
        """Test collecting enhanced metadata for photos from the gallery."""
        photos = flickr_api.get_photo_list()
        assert len(photos) > 0

        first_photo = photos[0]
        enriched = flickr_api.enrich_photo(first_photo)

        assert enriched.id == first_photo.id
        assert enriched.url
        assert enriched.title is not None
        assert enriched.description is not None

        metadata_found = [
            field for field in ('location_data', 'exif_data')
            if getattr(enriched, field)
        ]

        print(f"PASS: Enhanced metadata collected for photo {enriched.id}")
        print(f"Additional metadata found: {metadata_found}")

    def test_blog_context_matching_with_flickr_photo(self, flickr_api, caption_generator, config):
        """Test matching blog content with actual Flickr photo from the gallery."""
        photos = flickr_api.get_photo_list()
        assert len(photos) > 0

        enriched_photo = flickr_api.enrich_photo(photos[0])
        enriched_photo.source_url = config.blog_post_url

        blog_match = caption_generator._get_blog_content_context(enriched_photo)

        if blog_match:
            assert isinstance(blog_match, BlogContextMatch)
            assert len(blog_match.context) > 20, "Blog context should be substantial"

            photo_keywords = []
            if enriched_photo.title:
                photo_keywords.extend(enriched_photo.title.lower().split())
            if enriched_photo.description:
                photo_keywords.extend(enriched_photo.description.lower().split())

            meaningful_keywords = [k for k in photo_keywords if len(k) > 3]
            context_lower = blog_match.context.lower()

            if meaningful_keywords:
                matches = [k for k in meaningful_keywords if k in context_lower]
                print(f"PASS: Blog context matching: found {len(matches)} keyword matches")
                print(f"Matches: {matches}")
            else:
                print("INFO: No meaningful keywords found in photo metadata for matching")

            print(f"Blog context preview: {blog_match.context[:200]}...")
        else:
            print("WARN: No blog context extracted - this may indicate an issue with blog content extraction")

    @pytest.mark.skipif(not os.getenv('ANTHROPIC_API_KEY'), reason="Requires Anthropic API key")
    def test_end_to_end_caption_generation(self, flickr_api, caption_generator, config):
        """Test complete end-to-end caption generation with live data."""
        photos = flickr_api.get_photo_list()
        assert len(photos) > 0

        enriched_photo = flickr_api.enrich_photo(photos[0])
        enriched_photo.source_url = config.blog_post_url
        enriched_photo.hashtags = '#Mauritius #Travel #Beach #Paradise'

        generated_caption = caption_generator.generate_caption(enriched_photo)

        assert generated_caption is not None, "Should generate a caption"
        assert len(generated_caption) > 30, "Generated caption should be substantial"

        full_caption = caption_generator.build_full_caption(enriched_photo, generated_caption)

        assert full_caption is not None, "Should build full caption"
        assert len(full_caption) > len(generated_caption), "Full caption should be longer"

        caption_lower = full_caption.lower()
        relevant_terms = ['mauritius', 'beach', 'water', 'beautiful', 'paradise', 'island', 'crystal', 'travel']
        found_terms = [term for term in relevant_terms if term in caption_lower]

        print("PASS: End-to-end caption generation successful!")
        print(f"Photo: {enriched_photo.title or 'No title'} (ID: {enriched_photo.id})")
        print(f"Generated caption length: {len(generated_caption)} chars")
        print(f"Full caption length: {len(full_caption)} chars")
        print(f"Relevant terms found: {found_terms}")
        print("\n--- FULL CAPTION ---")
        safe_print(full_caption)
        print("--- END CAPTION ---\n")

        assert len(found_terms) >= 2, f"Caption should contain relevant terms. Found: {found_terms}"

    def test_caption_quality_with_vs_without_blog_context(self, flickr_api, caption_generator, config):
        """Compare caption quality with and without blog context."""
        if not os.getenv('ANTHROPIC_API_KEY'):
            pytest.skip("Requires Anthropic API key")

        photos = flickr_api.get_photo_list()
        enriched_photo = flickr_api.enrich_photo(photos[0])

        enriched_photo.source_url = config.blog_post_url
        caption_with_blog = caption_generator.generate_caption(enriched_photo)

        photo_without_blog = flickr_api.enrich_photo(photos[0])
        photo_without_blog.source_url = None
        caption_generator_without_blog = CaptionGenerator(config)
        caption_without_blog = caption_generator_without_blog.generate_caption(photo_without_blog)

        assert caption_with_blog is not None and caption_without_blog is not None

        print("\n=== CAPTION COMPARISON ===")
        print(f"Photo: {enriched_photo.title or 'No title'}")
        print(f"\n--- WITH BLOG CONTEXT ({len(caption_with_blog)} chars) ---")
        safe_print(caption_with_blog)
        print(f"\n--- WITHOUT BLOG CONTEXT ({len(caption_without_blog)} chars) ---")
        safe_print(caption_without_blog)
        print("\n=== END COMPARISON ===\n")

        if caption_with_blog != caption_without_blog:
            print("PASS: Blog context produces different captions")
        else:
            print("WARN: Captions are identical - blog context may not be working")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
