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

    def test_truncate_respects_zero_max_chars(self, generator):
        # _truncate_for_threads must never return more graphemes than the budget.
        result = generator._truncate_for_threads(
            'some long candidate', 'http://example.com/post', max_chars=0
        )
        assert result == ''

    def test_truncate_respects_negative_max_chars(self, generator):
        result = generator._truncate_for_threads(
            'some long candidate', 'http://example.com/post', max_chars=-5
        )
        assert result == ''

    def test_truncate_smaller_than_ellipsis_returns_hard_cut(self, generator):
        # max_chars=1 can't fit the ellipsis or the URL; result must still
        # be within budget rather than overflowing with a stray ellipsis.
        result = generator._truncate_for_threads(
            'abcdefghij', 'http://example.com/post', max_chars=1
        )
        assert len(result) <= 1

    def test_truncate_preserves_url_when_head_budget_is_zero(self, generator):
        # The suffix "…\n\n{url}" exactly fills max_chars - the prior code
        # dropped the URL because the budget check was `> 0`. With `>= 0`
        # the URL is preserved with an empty head.
        url = 'http://x.test/p'
        candidate = f'long head text here\n\n{url}'
        ellipsis_suffix_len = 1 + 2 + len(url)  # '…' + '\n\n' + url
        result = generator._truncate_for_threads(
            candidate, url, max_chars=ellipsis_suffix_len
        )
        assert url in result
        assert result.startswith('…')
        assert len(result) <= ellipsis_suffix_len

    def test_truncation_does_not_split_multi_codepoint_emoji(self, generator):
        # Family ZWJ sequence: 👨‍👩‍👧‍👦 is one grapheme but 7 codepoints.
        # We assemble a body whose plain-codepoint slice would fall mid-cluster.
        body = 'A ' + ('\U0001F468‍\U0001F469‍\U0001F467‍\U0001F466 ' * 20)
        photo = _photo(source_url=None)
        with patch.object(generator.client.messages, 'create',
                          side_effect=RuntimeError('skip claude')), \
             patch('caption_generator.resolve_blog_url', return_value=None):
            caption = generator.build_threads_caption(
                photo, generated_body=body, max_chars=60
            )

        # If we split mid-cluster we'd see a dangling ZWJ (U+200D) or a stray
        # combining sequence at the end. After grapheme-safe truncate, the
        # trailing character before the ellipsis should not be a ZWJ.
        ellipsis_idx = caption.rfind('…')
        if ellipsis_idx > 0:
            assert caption[ellipsis_idx - 1] != '‍', (
                f"Truncation split a ZWJ-joined emoji cluster: {caption!r}"
            )
