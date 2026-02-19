"""
Tests for CaptionGenerator using live Flickr gallery and Anthropic API.
Tests the enhanced caption generation with blog context integration.
"""
import os
from unittest.mock import MagicMock, patch

import pytest

from caption_generator import CaptionGenerator
from account_config import AccountConfig
from config import Config
from blog_content_extractor import BlogContextMatch
from photo_models import EnrichedPhoto


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
        config.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY') or 'test-key'
        config.anthropic_model = 'claude-sonnet-4-6'
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
        return EnrichedPhoto(
            id='31352051237',
            url='https://live.staticflickr.com/4885/31352051237_b494dd1d65_c.jpg',
            title='Le Morne Beach Mauritius',
            server='4885', secret='b494dd1d65', date_taken='2024-01-01 12:00:00',
            album_position=1,
            description='Crystal clear turquoise water at Le Morne beach with the iconic Le Morne Brabant mountain in the background. One of the most beautiful beaches in Mauritius.',
            location_data={
                'photo': {
                    'location': {
                        'locality': {'_content': 'Le Morne'},
                        'region': {'_content': 'Black River'},
                        'country': {'_content': 'Mauritius'}
                    }
                }
            },
            exif_data={
                'photo': {
                    'exif': [
                        {'tag': 'Make', 'raw': {'_content': 'Canon'}},
                        {'tag': 'Model', 'raw': {'_content': 'EOS R6'}}
                    ]
                }
            },
            exif_hints={
                'source_urls': ['https://travelmemo.com/mauritius/mauritius-what-to-do']
            },
            source_url='https://travelmemo.com/mauritius/mauritius-what-to-do',
            hashtags='#Mauritius #Beach #Travel #Paradise #LeMorne',
        )

    def test_build_context_from_photo_data(self, generator, sample_mauritius_photo_data):
        """Ensure the enhanced prompt includes all relevant context pieces."""
        photo_data = sample_mauritius_photo_data
        blog_match = BlogContextMatch(
            url=photo_data.source_url,
            context='Mauritius travel guide excerpt highlighting Le Morne beach.',
            score=42,
            matched_terms=('mauritius', 'beach')
        )

        with patch.object(generator, '_get_blog_content_context', return_value=blog_match),              patch.object(generator.client.messages, 'create') as mock_create:
            mock_response = MagicMock()
            mock_response.content = [MagicMock(text='Test caption')]
            mock_create.return_value = mock_response

            generator.generate_caption(photo_data)

            _, kwargs = mock_create.call_args
            messages = kwargs['messages']
            prompt_content = messages[0]['content'][1]['text']

            assert 'Le Morne Beach Mauritius' in prompt_content
            assert 'Crystal clear turquoise water' in prompt_content
            assert 'Le Morne, Black River, Mauritius' in prompt_content
            assert 'Canon EOS R6' in prompt_content
            assert 'travelmemo.com' in prompt_content
            assert 'Blog context:' in prompt_content

    @pytest.mark.skipif(not os.getenv('ANTHROPIC_API_KEY'), reason='Requires Anthropic API key')
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

        with patch.object(generator, '_load_blog_content', return_value={'paragraphs': ['stub']}), \
             patch.object(generator.blog_extractor, 'find_relevant_content', return_value=blog_match):
            match = generator._get_blog_content_context(sample_mauritius_photo_data)

        assert isinstance(match, BlogContextMatch)
        assert match.context.startswith('Detailed travel memo')
        selected = sample_mauritius_photo_data.selected_blog
        assert selected['url'] == config.blog_post_url
        assert selected['derived_from_exif']

    def test_enhanced_vs_basic_prompt_selection(self, generator):
        """Ensure contextual prompts differ from the basic fallback prompt."""
        rich_photo = EnrichedPhoto(
            id='test1', url='https://example.com/photo.jpg', title='Test Beach',
            server='1', secret='a', date_taken='2024-01-01', album_position=1,
            description='Beautiful beach scene',
            location_data={'photo': {'location': {'country': {'_content': 'Mauritius'}}}},
            exif_hints={'source_urls': ['https://example.com/exif-post']},
        )
        minimal_photo = EnrichedPhoto(
            id='test2', url='https://example.com/photo2.jpg', title='',
            server='1', secret='b', date_taken='2024-01-01', album_position=2,
        )

        blog_match = BlogContextMatch(
            url='https://example.com/exif-post',
            context='Short context sourced from EXIF metadata.',
            score=99,
            matched_terms=('exif',)
        )

        with patch.object(generator, '_get_blog_content_context', side_effect=[blog_match, None]),              patch.object(generator.client.messages, 'create') as mock_create:
            mock_response = MagicMock()
            mock_response.content = [MagicMock(text='Test caption')]
            mock_create.return_value = mock_response

            generator.generate_caption(rich_photo)
            rich_prompt = mock_create.call_args[1]['messages'][0]['content'][1]['text']

            generator.generate_caption(minimal_photo)
            minimal_prompt = mock_create.call_args[1]['messages'][0]['content'][1]['text']

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

        photo_data = EnrichedPhoto(
            id='with-exif', url='https://example.com/with-exif.jpg', title='Test',
            server='1', secret='a', date_taken='2024-01-01', album_position=1,
            source_url=short_exif_url,
            exif_hints={'source_urls': [short_exif_url, long_exif_url]},
        )

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

        with patch.object(generator, '_load_blog_content', side_effect=load_side_effect), \
             patch.object(generator.blog_extractor, 'find_relevant_content', side_effect=find_side_effect):
            match = generator._get_blog_content_context(photo_data)

        assert processed_urls[0] == long_exif_url
        assert short_exif_url not in processed_urls
        assert isinstance(match, BlogContextMatch)
        assert match.url == long_exif_url
        assert photo_data.selected_blog['url'] == long_exif_url
        assert photo_data.source_url == long_exif_url
        assert photo_data.selected_blog['derived_from_exif'] is True

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
        assert sample_mauritius_photo_data.title in full_caption
        assert sample_mauritius_photo_data.description in full_caption
        assert 'Travelmemo from a one-of-a-kind travel experience.' in full_caption
        assert sample_mauritius_photo_data.hashtags in full_caption

    @pytest.mark.skipif(not os.getenv('ANTHROPIC_API_KEY'), reason='Requires Anthropic API key')
    def test_retry_mechanism_success(self, generator, sample_mauritius_photo_data):
        """Smoke test for retry wrapper when APIs are reachable."""
        caption = generator.generate_with_retry(sample_mauritius_photo_data, max_retries=3)

        assert caption is not None
        assert isinstance(caption, str)
        assert len(caption) > 20

    def test_domain_preference_in_exif_url_selection(self, generator, config):
        """Domain preferences should be applied to EXIF URLs to fix issue #162."""
        # Set up account with specific domain preferences (German account prefers reisememo.ch)

        # URLs where German URL is longer but English URL should be preferred for English account
        german_url = 'https://reisememo.ch/italien/sardinien/sardinien-reisetipps-norden'  # Longer German URL
        english_url = 'https://travelmemo.com/italy/sardinia'  # Shorter English URL

        photo_data = EnrichedPhoto(
            id='domain-preference-test', url='https://example.com/test.jpg', title='Test',
            server='1', secret='a', date_taken='2024-01-01', album_position=1,
            exif_hints={'source_urls': [german_url, english_url]},
        )

        processed_urls = []

        def load_side_effect(url):
            processed_urls.append(url)
            return {'url': url}

        def find_side_effect(content, _photo):
            # Both URLs should work, but preference should determine which is chosen first
            return BlogContextMatch(url=content['url'], context=f'Context from {content["url"]}', score=10, matched_terms=('test',))

        # Test with English account (should prefer travelmemo.com)
        config.account = 'primary'  # English account

        with patch('account_config.get_account_config') as mock_get_config:
            mock_get_config.return_value = AccountConfig(
                account_id='primary',
                display_name='Primary',
                environment_name='primary-account',
                language='en',
                blog_domains=['travelmemo.com', 'reisememo.ch']  # Prefers travelmemo.com first
            )

            with patch.object(generator, '_load_blog_content', side_effect=load_side_effect), \
                 patch.object(generator.blog_extractor, 'find_relevant_content', side_effect=find_side_effect):

                match = generator._get_blog_content_context(photo_data)

        # The English URL should be processed first due to domain preference
        assert processed_urls[0] == english_url, f"Expected {english_url} to be processed first, but got {processed_urls[0]}"
        assert match.url == english_url
        assert photo_data.selected_blog['url'] == english_url

        # Reset for German account test
        photo_data = EnrichedPhoto(
            id='domain-preference-test-de', url='https://example.com/test.jpg', title='Test',
            server='1', secret='a', date_taken='2024-01-01', album_position=1,
            exif_hints={'source_urls': [german_url, english_url]},
        )
        processed_urls.clear()

        # Test with German account (should prefer reisememo.ch)
        config.account = 'reisememo'  # German account

        with patch('account_config.get_account_config') as mock_get_config:
            mock_get_config.return_value = AccountConfig(
                account_id='reisememo',
                display_name='Reisememo',
                environment_name='secondary-account',
                language='de',
                blog_domains=['reisememo.ch', 'travelmemo.com']  # Prefers reisememo.ch first
            )

            with patch.object(generator, '_load_blog_content', side_effect=load_side_effect), \
                 patch.object(generator.blog_extractor, 'find_relevant_content', side_effect=find_side_effect):

                match = generator._get_blog_content_context(photo_data)

        # The German URL should be processed first due to domain preference
        assert processed_urls[0] == german_url, f"Expected {german_url} to be processed first, but got {processed_urls[0]}"
        assert match.url == german_url
        assert photo_data.selected_blog['url'] == german_url

    def test_issue_162_german_url_interference_fix(self, generator, config):
        """Integration test for issue #162: German URLs interfering with English account URL selection."""
        # Simulate the exact scenario from issue #162:
        # - All photos in an album refer to the same destination
        # - German URLs are longer due to language, not completeness
        # - English account should prefer shorter but complete English URLs

        # URLs from the issue description - German URL is longer but should not be preferred for English account
        complete_english_url = 'https://travelmemo.com/italy/sardinia'  # Complete but shorter
        longer_german_url = 'https://reisememo.ch/italien/sardinien/sardinien-sehenswuerdigkeiten-reisetipps'  # Longer German
        truncated_english_url = 'https://travelmemo.com/italy/sar'  # Truncated English URL

        # Photo data with EXIF containing multiple URLs (simulating Flickr EXIF data)
        photo_data = EnrichedPhoto(
            id='issue-162-test', url='https://example.com/sardinia-photo.jpg',
            title='Beautiful Sardinia coastline',
            server='1', secret='a', date_taken='2024-01-01', album_position=1,
            exif_hints={
                'source_urls': [
                    truncated_english_url,    # Appears first, truncated
                    longer_german_url,        # Appears second, longer (would be selected by old logic)
                    complete_english_url      # Appears third, complete English URL
                ]
            },
        )

        processed_urls = []

        def load_side_effect(url):
            processed_urls.append(url)
            return {'url': url, 'title': f'Blog post for {url}'}

        def find_side_effect(content, _photo):
            url = content['url']
            if 'travelmemo.com' in url:
                return BlogContextMatch(url=url, context='Sardinia travel tips from English blog', score=8, matched_terms=('sardinia', 'travel'))
            elif 'reisememo.ch' in url:
                return BlogContextMatch(url=url, context='Sardinien Reisetipps vom deutschen Blog', score=7, matched_terms=('sardinien', 'reise'))
            return None

        # Test with English primary account configuration
        config.account = 'primary'

        with patch('account_config.get_account_config') as mock_get_config:
            # English account prefers travelmemo.com domains
            mock_get_config.return_value = AccountConfig(
                account_id='primary',
                display_name='Primary',
                environment_name='primary-account',
                language='en',
                blog_domains=['travelmemo.com', 'reisememo.ch']  # English domain preferred first
            )

            with patch.object(generator, '_load_blog_content', side_effect=load_side_effect), \
                 patch.object(generator.blog_extractor, 'find_relevant_content', side_effect=find_side_effect):

                match = generator._get_blog_content_context(photo_data)

        # ASSERTION: The fix should ensure that English URLs are prioritized over German URLs
        # even when German URLs are longer, fixing the interference described in issue #162

        # The complete English URL should be selected, not the longer German URL
        assert match is not None, "Should find a blog context match"
        assert 'travelmemo.com' in match.url, f"Expected English travelmemo.com URL, but got {match.url}"
        assert match.url == complete_english_url, f"Expected complete English URL {complete_english_url}, but got {match.url}"

        # Verify that English URLs were processed before German URLs
        english_urls_processed = [url for url in processed_urls if 'travelmemo.com' in url]
        german_urls_processed = [url for url in processed_urls if 'reisememo.ch' in url]

        if english_urls_processed and german_urls_processed:
            first_english_index = processed_urls.index(english_urls_processed[0])
            first_german_index = processed_urls.index(german_urls_processed[0])
            assert first_english_index < first_german_index, \
                f"English URLs should be processed before German URLs. Processing order: {processed_urls}"

        # Verify photo data is updated correctly
        assert photo_data.selected_blog['url'] == complete_english_url
        assert photo_data.source_url == complete_english_url  # Updated by _ensure_longest_source_url

    def test_caption_url_fallback_when_no_blog_context_found(self, generator, config):
        """When no BLOG_POST_URL is configured and no selected_blog, no URL appears in caption."""
        config.account = 'primary'
        config.blog_post_url = None
        config.blog_post_urls = []
        config.get_default_blog_post_url.return_value = None  # No default URL configured

        photo_data = EnrichedPhoto(
            id='no-blog-context', url='https://example.com/photo.jpg',
            title='Photo without blog context',
            server='1', secret='a', date_taken='2024-01-01', album_position=1,
            description='A photo that has no associated blog context',
            hashtags='#test #photo #reisememo',
            # Note: no selected_blog - simulates when _get_blog_content_context returns None
        )

        generated_caption = "This is a test caption."

        with patch('account_config.get_account_config') as mock_get_config:
            mock_get_config.return_value = AccountConfig(
                account_id='primary',
                display_name='Primary',
                environment_name='primary-account',
                language='en',
                blog_domains=['travelmemo.com', 'backup.com']
            )

            caption = generator.build_full_caption(photo_data, generated_caption)

        # No bare-domain fallback — better to omit URL than show a generic domain
        assert 'https://travelmemo.com' not in caption, f"Should not contain bare domain URL: {caption}"
        assert 'Read the travel tip at' not in caption, "Should not contain travel tip text without a URL"
        assert photo_data.hashtags in caption, "Expected hashtags in caption"

    def test_caption_uses_configured_url_over_selected_blog(self, generator, config):
        """BLOG_POST_URL(S) takes priority over auto-discovered selected_blog URL."""
        config.account = 'primary'
        config.blog_post_urls = ['https://travelmemo.com/mauritius-guide/']
        config.get_default_blog_post_url.return_value = 'https://travelmemo.com/mauritius-guide/'

        photo_data = EnrichedPhoto(
            id='url-priority', url='https://example.com/photo.jpg', title='Priority test',
            server='1', secret='a', date_taken='2024-01-01', album_position=1,
            selected_blog={'url': 'https://reisememo.ch/some-post/'},
            hashtags='#test',
        )

        generated_caption = "Test caption."

        with patch('account_config.get_account_config') as mock_get_config:
            mock_get_config.return_value = AccountConfig(
                account_id='primary',
                display_name='Primary',
                environment_name='primary-account',
                language='en',
                blog_domains=['travelmemo.com']
            )

            caption = generator.build_full_caption(photo_data, generated_caption)

        assert 'https://travelmemo.com/mauritius-guide/' in caption, f"Should use configured URL: {caption}"
        assert 'reisememo.ch' not in caption, f"Should not contain secondary domain URL: {caption}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
