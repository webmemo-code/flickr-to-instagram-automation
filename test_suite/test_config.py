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

WP5 = pytest.mark.xfail(reason="WP5 not implemented", strict=False)


class TestAccountParity:
    @WP5
    def test_config_identical_for_primary_and_secondary_env(self):
        """REGRESSION then invariant: parametrize over
        account in ('primary', 'reisememo'); with an identical environment,
        the effective Config fields (album id, token, account id, endpoints)
        are identical for both. Passes before the collapse (branches are
        already identical) and after."""
        pytest.fail("scaffold: implement per docstring")


class TestDomainDetection:
    @WP5
    def test_igaa_token_routes_to_graph_instagram(self):
        """REGRESSION: with igaa_env, graph_endpoint_base starts with
        https://graph.instagram.com/ — the auto-detection that makes the
        EAA→IGAA migration a pure token swap."""
        pytest.fail("scaffold: implement per docstring")

    @WP5
    def test_eaa_token_routes_to_graph_facebook(self):
        """REGRESSION: with eaa_env, graph_endpoint_base starts with
        https://graph.facebook.com/."""
        pytest.fail("scaffold: implement per docstring")


class TestValidationSimplification:
    @WP5
    def test_validation_still_covers_required_vars(self):
        """After simplifying the pre-environment-scope special casing in
        _validate_config (config.py:117-158), a genuinely missing required
        credential still produces a validation failure with a clear message,
        and the workflows' validation step still passes with a complete env."""
        pytest.fail("scaffold: implement per docstring")
