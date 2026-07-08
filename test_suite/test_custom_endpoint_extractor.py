"""WP6 — de-hardcode travelmemo in the content path.

Spec: docs/refactor/01-work-packages.md (WP6). Fixtures: account_env_reisememo,
full_env, sample_posts_json (unused here) live in conftest.py.

Covers: custom-endpoint namespace/auth_key/User-Agent sourced from
AccountConfig, byte-identical primary defaults, and the single shared
_extract_url_slug (now blog_url_resolver.extract_url_slug).
"""
from unittest.mock import MagicMock, patch

import pytest

from account_config import account_manager
from custom_endpoint_extractor import CustomEndpointExtractor
from blog_url_resolver import extract_url_slug


@pytest.fixture(autouse=True)
def _reload_account_manager(monkeypatch):
    """AccountConfigManager is built once at import time from os.environ.
    Rebuild it after env fixtures set SECONDARY_* vars so get_account_config
    reflects the test's environment."""
    def _reload():
        account_manager.accounts = account_manager._load_account_configs()
        return account_manager

    yield _reload
    account_manager.accounts = account_manager._load_account_configs()


def _config(account='primary'):
    config = MagicMock()
    config.account = account
    return config


class TestConfigurableEndpoint:
    def test_endpoint_url_uses_configured_namespace(self, account_env_reisememo, _reload_account_manager):
        """With account_env_reisememo, the custom endpoint request goes to
        https://reisememo.ch/wp-json/<configured namespace>/extract/... —
        namespace comes from AccountConfig, not a literal."""
        account_env_reisememo(SECONDARY_WP_ENDPOINT_NAMESPACE='reisememo-content/v1')
        _reload_account_manager()

        extractor = CustomEndpointExtractor(_config('reisememo'))
        with patch.object(extractor.session, 'get') as mock_get:
            mock_get.return_value = MagicMock(status_code=200, json=lambda: {'success': False})
            extractor.extract_via_custom_endpoint('https://reisememo.ch/blog/my-post')

        called_url = mock_get.call_args.args[0]
        assert called_url == 'https://reisememo.ch/wp-json/reisememo-content/v1/extract/my-post'

    def test_auth_key_from_account_config(self, account_env_reisememo, _reload_account_manager):
        """The auth_key sent with the custom-endpoint request is the
        configured per-account value, not the hardcoded 'tm-post-retrieval'."""
        account_env_reisememo(SECONDARY_WP_AUTH_KEY='reisememo-secret-key')
        _reload_account_manager()

        extractor = CustomEndpointExtractor(_config('reisememo'))
        with patch.object(extractor.session, 'get') as mock_get:
            mock_get.return_value = MagicMock(status_code=200, json=lambda: {'success': False})
            extractor.extract_via_custom_endpoint('https://reisememo.ch/blog/my-post')

        assert mock_get.call_args.kwargs['params'] == {'auth_key': 'reisememo-secret-key'}


class TestUserAgent:
    def test_user_agent_from_account_config(self, account_env_reisememo, _reload_account_manager):
        """The custom-endpoint session carries the account-configured
        User-Agent, not the hardcoded travelmemo literal."""
        account_env_reisememo()
        _reload_account_manager()

        extractor = CustomEndpointExtractor(_config('reisememo'))
        assert extractor.session.headers['User-Agent'] == 'Reisememo-ContentFetcher/1.0'

    def test_user_agent_derived_from_display_name_when_unset(self, full_env, _reload_account_manager):
        """With no SECONDARY_USER_AGENT override, the User-Agent is derived
        from the account's display_name."""
        full_env(SECONDARY_ACCOUNT_ID='reisememo', SECONDARY_ACCOUNT_NAME='My Custom Brand')
        _reload_account_manager()

        extractor = CustomEndpointExtractor(_config('reisememo'))
        assert extractor.session.headers['User-Agent'] == 'MyCustomBrand-ContentFetcher/1.0'


class TestPrimaryRegression:
    def test_primary_defaults_unchanged(self, full_env, _reload_account_manager):
        """REGRESSION: with no new env vars set, the primary account produces
        byte-identical behavior to today - endpoint URL
        https://.../wp-json/travelmemo-content/v1/extract/..., auth_key
        'tm-post-retrieval', User-Agent 'TravelMemo-ContentFetcher/1.0'."""
        full_env()
        _reload_account_manager()

        extractor = CustomEndpointExtractor(_config('primary'))
        assert extractor.session.headers['User-Agent'] == 'TravelMemo-ContentFetcher/1.0'
        assert extractor.wp_endpoint_namespace == 'travelmemo-content/v1'
        assert extractor.wp_auth_key == 'tm-post-retrieval'

        with patch.object(extractor.session, 'get') as mock_get:
            mock_get.return_value = MagicMock(status_code=200, json=lambda: {'success': False})
            extractor.extract_via_custom_endpoint('https://travelmemo.com/blog/my-post')

        called_url = mock_get.call_args.args[0]
        assert called_url == 'https://travelmemo.com/wp-json/travelmemo-content/v1/extract/my-post'
        assert mock_get.call_args.kwargs['params'] == {'auth_key': 'tm-post-retrieval'}


class TestDeduplication:
    def test_extract_url_slug_single_source_of_truth(self):
        """_extract_url_slug exists exactly once (blog_url_resolver.py);
        both former call sites (custom_endpoint_extractor.py,
        blog_content_extractor.py) now import and use it directly."""
        import custom_endpoint_extractor
        import blog_content_extractor

        assert not hasattr(custom_endpoint_extractor.CustomEndpointExtractor, '_extract_url_slug')
        assert not hasattr(blog_content_extractor.BlogContentExtractor, '_extract_url_slug')

        cases = [
            ('https://reisememo.ch/blog/my-post', 'my-post'),
            ('https://travelmemo.com/mauritius/what-to-do/', 'what-to-do'),
            ('https://travelmemo.com/search?q=hello', 'search'),
            ('https://reisememo.ch/reise/z%C3%BCrich', 'z%C3%BCrich'),
        ]
        for url, expected_slug in cases:
            assert extract_url_slug(url) == expected_slug
