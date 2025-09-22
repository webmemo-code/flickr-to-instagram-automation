"""
Tests for CaptionGenerator using live Flickr gallery and OpenAI API.
Tests the enhanced caption generation with blog context integration.
"""
import os
from unittest.mock import MagicMock, patch

import pytest

from caption_generator import CaptionGenerator
from config import Config
from blog_content_extractor import BlogContextMatch


def safe_print(text):
    """Print text with Unicode characters safely on Windows."""
    try:
        print(text)
    except UnicodeEncodeError:
        safe_text = text.encode('ascii', 'ignore').decode('ascii')
        print(safe_text)


class TestCaptionGenerator:
    """Test CaptionGenerator with live data and mocked dependencies."""

    @pytest.fixture
    def config(self):
        """Create a config mock with sensible defaults for testing."""
        config = MagicMock(spec=Config)
        config.openai_api_key = os.getenv('OPENAI_API_KEY') or 'test-key'
        config.openai_model = 'gpt-4o-mini'
        config.blog_post_url = "https://travelmemo.com/mauritius/mauritius-what-to-do"
        config.blog_post_urls = [config.blog_post_url]
        config.account = 'primary'
        config.get_default_blog_post_url.return_value = config.blog_post_url
        return config

    @pytest.fixture
    def generator(self, config):
        """Create a CaptionGenerator instance for testing."""
        return CaptionGenerator(config)

    @pytest.fixture
    def sample_mauritius_photo_data(self):
        """Sample photo data representative of Flickr API output."""
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
            'exif_hints': {
                'source_urls': ['https://travelmemo.com/mauritius/mauritius-what-to-do']
            },
            'source_url': 'https://travelmemo.com/mauritius/mauritius-what-to-do',
            'hashtags': '#Mauritius #Beach #Travel #Paradise #LeMorne'
        }

    def test_build_context_from_photo_data(self, generator, sample_mauritius_photo_data):
        """Ensure the enhanced prompt includes all relevant context pieces."""
        photo_data = sample_mauritius_photo_data
        blog_match = BlogContextMatch(
            url=photo_data['source_url'],
            context='Mauritius travel guide excerpt highlighting Le Morne beach.',
            score=42,
            matched_terms=('mauritius', 'beach')
        )

        with patch.object(generator, '_get_blog_content_context', return_value=blog_match),              patch.object(generator.client.chat.completions, 'create') as mock_create:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock(message=MagicMock(content='Test caption'))]
            mock_create.return_value = mock_response

            generator.generate_caption(photo_data)

            _, kwargs = mock_create.call_args
            messages = kwargs['messages']
            prompt_content = messages[0]['content'][0]['text']

            assert 'Le Morne Beach Mauritius' in prompt_content
            assert 'Crystal clear turquoise water' in prompt_content
            assert 'Le Morne, Black River, Mauritius' in prompt_content
            assert 'Canon EOS R6' in prompt_content
            assert 'travelmemo.com' in prompt_content
            assert 'Blog context:' in prompt_content

    @pytest.mark.skipif(not os.getenv('OPENAI_API_KEY'), reason='Requires OpenAI API key')
    def test_generate_caption_with_blog_context_live(self, generator, sample_mauritius_photo_data):
        """Integration smoke test that exercises the live dependencies."""
        caption = generator.generate_caption(sample_mauritius_photo_data)

        assert caption is not None
        assert isinstance(caption, str)
        assert len(caption) > 20

        terms = ['mauritius', 'beach', 'morne', 'turquoise']
        found_terms = [term for term in terms if term in caption.lower()]
        assert len(found_terms) >= 2
        safe_print(f"PASS: Generated caption preview: {caption[:100]}...")

    def test_blog_content_context_integration(self, generator, sample_mauritius_photo_data, config):
        """Verify that blog context selection stores metadata on the photo."""
        blog_match = BlogContextMatch(
            url=config.blog_post_url,
            context='Detailed travel memo about Mauritius beaches and activities.',
            score=55,
            matched_terms=('mauritius', 'beach')
        )

        with patch.object(generator, '_load_blog_content', return_value={'paragraphs': ['stub']}),              patch.object(generator.blog_extractor, 'find_relevant_content', return_value=blog_match):
            match = generator._get_blog_content_context(sample_mauritius_photo_data)

        assert isinstance(match, BlogContextMatch)
        assert match.context.startswith('Detailed travel memo')
        selected = sample_mauritius_photo_data['selected_blog']
        assert selected['url'] == config.blog_post_url
        assert selected['derived_from_exif']

    def test_enhanced_vs_basic_prompt_selection(self, generator):
        """Ensure contextual prompts differ from the basic fallback prompt."""
        rich_photo = {
            'id': 'test1',
            'url': 'https://example.com/photo.jpg',
            'title': 'Test Beach',
            'description': 'Beautiful beach scene',
            'location_data': {'photo': {'location': {'country': {'_content': 'Mauritius'}}}},
            'exif_hints': {'source_urls': ['https://example.com/exif-post']}
        }
        minimal_photo = {'id': 'test2', 'url': 'https://example.com/photo2.jpg'}

        blog_match = BlogContextMatch(
            url='https://example.com/exif-post',
            context='Short context sourced from EXIF metadata.',
            score=99,
            matched_terms=('exif',)
        )

        with patch.object(generator, '_get_blog_content_context', side_effect=[blog_match, None]),              patch.object(generator.client.chat.completions, 'create') as mock_create:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock(message=MagicMock(content='Test caption'))]
            mock_create.return_value = mock_response

            generator.generate_caption(rich_photo)
            rich_prompt = mock_create.call_args[1]['messages'][0]['content'][0]['text']

            generator.generate_caption(minimal_photo)
            minimal_prompt = mock_create.call_args[1]['messages'][0]['content'][0]['text']

        assert 'Use the provided blog post context' in rich_prompt
        assert 'Blog context:' in rich_prompt
        assert 'Describe this image in two very short paragraphs' in minimal_prompt
        assert len(rich_prompt) > len(minimal_prompt)

    def test_get_blog_content_context_prioritizes_exif_urls(self, generator, config):
        """EXIF-sourced URLs should be evaluated before configured fallbacks."""
        long_exif_url = 'https://travelmemo.com/italien/sardinien/sardinien-norden-reisetipps'
        short_exif_url = 'https://travelmemo.com/italien/sar'
        fallback_url = 'https://travelmemo.com/fallback-post'
        config.blog_post_url = fallback_url
        config.blog_post_urls = [fallback_url]
        config.get_default_blog_post_url.return_value = fallback_url

        photo_data = {
            'id': 'with-exif',
            'url': 'https://example.com/with-exif.jpg',
            'source_url': short_exif_url,
            'exif_hints': {'source_urls': [short_exif_url, long_exif_url]},
        }

        processed_urls = []

        def load_side_effect(url):
            processed_urls.append(url)
            return {'url': url}

        def find_side_effect(content, _photo):
            url = content['url']
            if url == long_exif_url:
                return BlogContextMatch(url=url, context='Context from EXIF URL', score=10, matched_terms=('exif',))
            if url == fallback_url:
                return BlogContextMatch(url=url, context='Fallback context', score=5, matched_terms=('fallback',))
            return None

        with patch.object(generator, '_load_blog_content', side_effect=load_side_effect),              patch.object(generator.blog_extractor, 'find_relevant_content', side_effect=find_side_effect):
            match = generator._get_blog_content_context(photo_data)

        assert processed_urls[0] == long_exif_url
        assert short_exif_url not in processed_urls
        assert isinstance(match, BlogContextMatch)
        assert match.url == long_exif_url
        assert photo_data['selected_blog']['url'] == long_exif_url
        assert photo_data['source_url'] == long_exif_url
        assert photo_data['selected_blog']['derived_from_exif'] is True

    def test_build_full_caption_structure(self, generator, sample_mauritius_photo_data):
        """Validate the final caption assembly adds branding and hashtags."""
        generated_caption = (
            'This stunning beach showcases the natural beauty of Mauritius. '
            'The crystal clear waters invite you to take a refreshing swim. '
            'Le Morne mountain provides a dramatic backdrop. '
            "It's truly a paradise on earth. "
            'Perfect for photography and relaxation.'
        )

        full_caption = generator.build_full_caption(sample_mauritius_photo_data, generated_caption)

        assert full_caption is not None
        assert generated_caption in full_caption
        assert sample_mauritius_photo_data['title'] in full_caption
        assert sample_mauritius_photo_data['description'] in full_caption
        assert 'Travelmemo from a one-of-a-kind travel experience.' in full_caption
        assert sample_mauritius_photo_data['hashtags'] in full_caption

    @pytest.mark.skipif(not os.getenv('OPENAI_API_KEY'), reason='Requires OpenAI API key')
    def test_retry_mechanism_success(self, generator, sample_mauritius_photo_data):
        """Smoke test for retry wrapper when APIs are reachable."""
        caption = generator.generate_with_retry(sample_mauritius_photo_data, max_retries=3)

        assert caption is not None
        assert isinstance(caption, str)
        assert len(caption) > 20


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
