"""
Unit tests for CaptionGenerator.build_threads_caption.

The Claude call is always mocked. Tests cover:
  - candidate already fits (no Claude call)
  - candidate too long, Claude shortens successfully
  - candidate too long, Claude fails -> deterministic truncate fallback preserves URL
"""
import os
from unittest.mock import MagicMock, patch

import pytest

from caption_generator import CaptionGenerator
from config import Config
from photo_models import EnrichedPhoto


def _config():
    config = MagicMock(spec=Config)
    config.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY') or 'test-key'
    config.anthropic_model = 'claude-sonnet-4-6'
    config.blog_post_url = 'https://travelmemo.com/post'
    config.blog_post_urls = [config.blog_post_url]
    config.account = 'primary'
    config.get_default_blog_post_url.return_value = config.blog_post_url
    return config


@pytest.fixture
def generator():
    return CaptionGenerator(_config())


def _photo(title='Beach', source_url='https://travelmemo.com/post'):
    return EnrichedPhoto(
        id='1', url='http://example.com/p.jpg', title=title,
        server='1', secret='a', date_taken='2024-01-01', album_position=1,
        description='', hashtags='#unused', source_url=source_url,
    )


class TestBuildThreadsCaption:
    def test_short_candidate_returns_immediately_without_claude(self, generator):
        with patch.object(generator.client.messages, 'create') as mock_create:
            caption = generator.build_threads_caption(
                _photo(), generated_body='A pleasant stroll.', max_chars=500
            )
        assert 'Beach' in caption
        assert 'A pleasant stroll' in caption
        assert 'https://travelmemo.com/post' in caption
        assert len(caption) <= 500
        mock_create.assert_not_called()

    def test_strips_hashtags_via_assembly(self, generator):
        caption = generator.build_threads_caption(
            _photo(), generated_body='A pleasant stroll.', max_chars=500
        )
        assert '#unused' not in caption

    def test_long_candidate_uses_claude(self, generator):
        long_body = 'word ' * 200  # ~1000 chars
        with patch.object(generator.client.messages, 'create') as mock_create:
            mock_create.return_value = MagicMock(content=[MagicMock(text='Short rewrite.')])
            caption = generator.build_threads_caption(
                _photo(), generated_body=long_body, max_chars=500
            )
        assert mock_create.called
        assert len(caption) <= 500
        assert 'Short rewrite.' in caption

    def test_claude_failure_falls_back_to_truncate_preserves_url(self, generator):
        long_body = 'word ' * 200
        with patch.object(generator.client.messages, 'create',
                          side_effect=RuntimeError('rate limited')):
            caption = generator.build_threads_caption(
                _photo(), generated_body=long_body, max_chars=300
            )
        assert len(caption) <= 300
        assert caption.endswith('https://travelmemo.com/post')
        assert '…' in caption

    def test_claude_response_too_long_falls_back_to_truncate(self, generator):
        long_body = 'word ' * 200
        with patch.object(generator.client.messages, 'create') as mock_create:
            mock_create.return_value = MagicMock(
                content=[MagicMock(text='still way too long ' * 50)]
            )
            caption = generator.build_threads_caption(
                _photo(), generated_body=long_body, max_chars=200
            )
        assert len(caption) <= 200

    def test_no_blog_url_truncation_still_under_limit(self, generator):
        long_body = 'word ' * 200
        photo = _photo(source_url=None)
        with patch.object(generator.client.messages, 'create',
                          side_effect=RuntimeError('boom')), \
             patch('caption_generator.resolve_blog_url', return_value=None):
            caption = generator.build_threads_caption(
                photo, generated_body=long_body, max_chars=120
            )
        assert len(caption) <= 120

    def test_claude_drops_url_then_helper_appends_it_back(self, generator):
        long_body = 'word ' * 200
        with patch.object(generator.client.messages, 'create') as mock_create:
            mock_create.return_value = MagicMock(content=[MagicMock(text='Concise rewrite without url.')])
            caption = generator.build_threads_caption(
                _photo(), generated_body=long_body, max_chars=500
            )
        assert 'https://travelmemo.com/post' in caption

    def test_empty_generated_body_uses_title_only(self, generator):
        caption = generator.build_threads_caption(
            _photo(title='Solo Title'), generated_body=None, max_chars=500
        )
        assert 'Solo Title' in caption
