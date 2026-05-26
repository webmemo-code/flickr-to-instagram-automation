"""
Unit tests for Threads-related Config behavior.

Focuses on how Config handles empty / malformed / missing env vars for the
Threads cross-posting variables, since GitHub Actions plumbing exports
optional variables as empty strings ("") rather than leaving them unset.
"""
import os
from unittest.mock import patch

import pytest

from config import Config


REQUIRED_ENV = {
    'FLICKR_API_KEY': 'k',
    'FLICKR_USER_ID': 'u',
    'FLICKR_USERNAME': 'n',
    'ANTHROPIC_API_KEY': 'a',
    'GITHUB_TOKEN': 't',
    'FLICKR_ALBUM_ID': '123',
    'INSTAGRAM_ACCESS_TOKEN': 'tok',
    'INSTAGRAM_ACCOUNT_ID': 'acc',
}


def _build_config(extra_env):
    env = {**REQUIRED_ENV, **extra_env}
    with patch.dict(os.environ, env, clear=True):
        return Config()


class TestThreadsConfigDefaults:
    def test_unset_threads_api_version_uses_default(self):
        config = _build_config({})
        assert config.threads_api_version == 'v1.0'
        assert config.threads_endpoint_base == 'https://graph.threads.net/v1.0/'

    def test_empty_threads_api_version_uses_default(self):
        config = _build_config({'THREADS_API_VERSION': ''})
        assert config.threads_api_version == 'v1.0'
        assert config.threads_endpoint_base == 'https://graph.threads.net/v1.0/'

    def test_explicit_threads_api_version_used_verbatim(self):
        config = _build_config({'THREADS_API_VERSION': 'v2.0'})
        assert config.threads_api_version == 'v2.0'
        assert config.threads_endpoint_base == 'https://graph.threads.net/v2.0/'

    def test_unset_delay_defaults_to_8(self):
        config = _build_config({})
        assert config.threads_post_delay_hours == 8

    def test_empty_delay_defaults_to_8(self):
        config = _build_config({'THREADS_POST_DELAY_HOURS': ''})
        assert config.threads_post_delay_hours == 8

    def test_malformed_delay_defaults_to_8(self):
        config = _build_config({'THREADS_POST_DELAY_HOURS': 'not-a-number'})
        assert config.threads_post_delay_hours == 8

    def test_negative_delay_clamped_to_zero(self):
        config = _build_config({'THREADS_POST_DELAY_HOURS': '-3'})
        assert config.threads_post_delay_hours == 0

    def test_explicit_delay_used_verbatim(self):
        config = _build_config({'THREADS_POST_DELAY_HOURS': '24'})
        assert config.threads_post_delay_hours == 24


class TestThreadsPostingEnabled:
    def test_disabled_when_neither_set(self):
        config = _build_config({})
        assert config.threads_posting_enabled is False

    def test_disabled_when_only_user_id_set(self):
        config = _build_config({'THREADS_USER_ID': '1'})
        assert config.threads_posting_enabled is False

    def test_disabled_when_only_token_set(self):
        config = _build_config({'THREADS_ACCESS_TOKEN': 't'})
        assert config.threads_posting_enabled is False

    def test_enabled_when_both_set(self):
        config = _build_config({
            'THREADS_USER_ID': '1',
            'THREADS_ACCESS_TOKEN': 't',
        })
        assert config.threads_posting_enabled is True
