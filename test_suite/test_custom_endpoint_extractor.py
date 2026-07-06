"""WP6 scaffold — de-hardcode travelmemo in the content path.

Spec: docs/refactor/01-work-packages.md (WP6). Fixtures: account_env_reisememo,
full_env, graph_api/responses for outbound request capture.

Background (verified hardcodings this WP removes):
- custom_endpoint_extractor.py:46,53 — endpoint namespace
  'travelmemo-content/v1' and auth_key 'tm-post-retrieval'
- User-Agent 'TravelMemo-ContentFetcher/1.0' in 5 places
- blog_content_extractor.py:462 fallback ['travelmemo.com'], :540 label
- caption_generator.py:231 hardcoded English travelmemo fallback signature
- _extract_url_slug duplicated in custom_endpoint_extractor.py:96 and
  blog_content_extractor.py
"""

import pytest

WP6 = pytest.mark.xfail(reason="WP6 not implemented", strict=False)


class TestConfigurableEndpoint:
    @WP6
    def test_endpoint_url_uses_configured_namespace(self):
        """With account_env_reisememo, the custom endpoint request goes to
        https://reisememo.ch/wp-json/<configured namespace>/extract/... —
        namespace comes from AccountConfig, not a literal."""
        pytest.fail("scaffold: implement per docstring")

    @WP6
    def test_auth_key_from_account_config(self):
        """The auth_key sent with the custom-endpoint request is the
        configured per-account value, not the hardcoded 'tm-post-retrieval'."""
        pytest.fail("scaffold: implement per docstring")


class TestUserAgent:
    @WP6
    def test_user_agent_from_account_config_everywhere(self):
        """EVERY outbound request in the content path (custom endpoint, WP
        REST, direct scraping) carries the account-configured User-Agent —
        assert on captured request headers across all three fallback layers."""
        pytest.fail("scaffold: implement per docstring")


class TestFallbacks:
    @WP6
    def test_fallback_domains_from_account_config(self):
        """When no blog URL can be resolved from EXIF/metadata, the fallback
        domain list comes from AccountConfig.blog_domains (reisememo →
        ['reisememo.ch']), not the hardcoded ['travelmemo.com']."""
        pytest.fail("scaffold: implement per docstring")


class TestPrimaryRegression:
    @WP6
    def test_primary_defaults_unchanged(self):
        """REGRESSION (must pass BEFORE the change): with no new env vars set,
        the primary account produces byte-identical behavior to today —
        endpoint URL https://.../wp-json/travelmemo-content/v1/extract/...,
        auth_key 'tm-post-retrieval', User-Agent
        'TravelMemo-ContentFetcher/1.0', fallback ['travelmemo.com'], and the
        current English fallback signature."""
        pytest.fail("scaffold: implement per docstring")


class TestDeduplication:
    @WP6
    def test_extract_url_slug_single_source_of_truth(self):
        """_extract_url_slug exists exactly once (suggested home:
        blog_url_resolver.py); both former call sites use it and produce the
        same results for representative URLs (trailing slash, query string,
        umlauts/encoded chars)."""
        pytest.fail("scaffold: implement per docstring")
