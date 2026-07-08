"""WP5 scaffold — Config cleanup.

Spec: docs/refactor/01-work-packages.md (WP5). Uses full_env / igaa_env /
eaa_env fixtures.

Background (verified): config.py:40-50 has an if/else on
is_secondary_account(account) whose two branches read the SAME unsuffixed env
vars — account separation actually happens via GitHub Environments. WP5
collapses the branch; behavior must be provably identical for both account
types before and after.
"""

import pytest

from config import Config


class TestAccountParity:
    @pytest.mark.parametrize("account", ["primary", "reisememo"])
    def test_config_identical_for_primary_and_secondary_env(self, full_env, account):
        """REGRESSION then invariant: with an identical environment, the
        effective Config fields (album id, token, account id, endpoints) are
        identical for both account types. Passes before the collapse
        (branches were already identical) and after."""
        full_env()
        config = Config(account=account)

        assert config.flickr_album_id == '123'
        assert config.instagram_access_token == 'tok'
        assert config.instagram_account_id == 'acc'
        assert config.graph_endpoint_base == 'https://graph.facebook.com/v23.0/'


class TestDomainDetection:
    def test_igaa_token_routes_to_graph_instagram(self, igaa_env):
        """REGRESSION: with igaa_env, graph_endpoint_base starts with
        https://graph.instagram.com/ — the auto-detection that makes the
        EAA→IGAA migration a pure token swap."""
        igaa_env()
        config = Config()
        assert config.graph_endpoint_base.startswith('https://graph.instagram.com/')

    def test_eaa_token_routes_to_graph_facebook(self, eaa_env):
        """REGRESSION: with eaa_env, graph_endpoint_base starts with
        https://graph.facebook.com/."""
        eaa_env()
        config = Config()
        assert config.graph_endpoint_base.startswith('https://graph.facebook.com/')


class TestValidationSimplification:
    def test_validation_still_covers_required_vars(self, full_env):
        """After simplifying the pre-environment-scope special casing in
        _validate_config, a genuinely missing required credential still
        produces a validation failure with a clear message, and a complete
        env (as the workflows always provide, since Config() only ever runs
        inside GitHub Environment scope) still validates cleanly."""
        full_env()
        Config()  # complete env: must not raise

        full_env(FLICKR_ALBUM_ID='')
        with pytest.raises(ValueError, match='FLICKR_ALBUM_ID'):
            Config()
