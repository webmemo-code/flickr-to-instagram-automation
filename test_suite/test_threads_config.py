"""
Unit tests for Threads-related Config behavior.

Focuses on how Config handles empty / malformed / missing env vars for the
Threads cross-posting variables, since GitHub Actions plumbing exports
optional variables as empty strings ("") rather than leaving them unset.
"""
from config import Config


class TestThreadsConfigDefaults:
    def test_unset_threads_api_version_uses_default(self, full_env):
        full_env()
        config = Config()
        assert config.threads_api_version == 'v1.0'
        assert config.threads_endpoint_base == 'https://graph.threads.net/v1.0/'

    def test_empty_threads_api_version_uses_default(self, full_env):
        full_env(THREADS_API_VERSION='')
        config = Config()
        assert config.threads_api_version == 'v1.0'
        assert config.threads_endpoint_base == 'https://graph.threads.net/v1.0/'

    def test_explicit_threads_api_version_used_verbatim(self, full_env):
        full_env(THREADS_API_VERSION='v2.0')
        config = Config()
        assert config.threads_api_version == 'v2.0'
        assert config.threads_endpoint_base == 'https://graph.threads.net/v2.0/'

    def test_unset_delay_defaults_to_8(self, full_env):
        full_env()
        assert Config().threads_post_delay_hours == 8

    def test_empty_delay_defaults_to_8(self, full_env):
        full_env(THREADS_POST_DELAY_HOURS='')
        assert Config().threads_post_delay_hours == 8

    def test_malformed_delay_defaults_to_8(self, full_env):
        full_env(THREADS_POST_DELAY_HOURS='not-a-number')
        assert Config().threads_post_delay_hours == 8

    def test_negative_delay_clamped_to_zero(self, full_env):
        full_env(THREADS_POST_DELAY_HOURS='-3')
        assert Config().threads_post_delay_hours == 0

    def test_explicit_delay_used_verbatim(self, full_env):
        full_env(THREADS_POST_DELAY_HOURS='24')
        assert Config().threads_post_delay_hours == 24


class TestThreadsPostingEnabled:
    def test_disabled_when_neither_set(self, full_env):
        full_env()
        assert Config().threads_posting_enabled is False

    def test_disabled_when_only_user_id_set(self, full_env):
        full_env(THREADS_USER_ID='1')
        assert Config().threads_posting_enabled is False

    def test_disabled_when_only_token_set(self, full_env):
        full_env(THREADS_ACCESS_TOKEN='t')
        assert Config().threads_posting_enabled is False

    def test_enabled_when_both_set(self, full_env):
        full_env(THREADS_USER_ID='1', THREADS_ACCESS_TOKEN='t')
        assert Config().threads_posting_enabled is True
