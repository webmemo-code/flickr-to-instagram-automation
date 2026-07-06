"""Shared fixture contract for the test suite (scaffold).

SCAFFOLD STATUS: These fixtures are stubs defining the contract described in
docs/refactor/02-test-scaffold-map.md. They are implemented in WP2
("Test-suite hygiene"). Until then, any test requesting one of them is
skipped with an explanatory message.

Implementation rules for WP2:
- Implement each fixture per its docstring; remove the `_not_implemented` call.
- Existing test files must then migrate their copy-pasted fixture blocks
  (REQUIRED_ENV, _build_config, safe_print, config mocks) to these fixtures.
- No test file may redefine a fixture that this conftest provides.
"""

import pytest


def _not_implemented(name: str):
    pytest.skip(f"conftest fixture '{name}' not implemented yet (WP2 scaffold)")


@pytest.fixture
def full_env(monkeypatch):
    """Factory fixture: set a complete, valid environment.

    Contract:
    - Callable as ``full_env(**overrides)``; monkeypatch-sets every env var a
      default `Config()` needs (Flickr, Instagram, Anthropic, GitHub, SMTP),
      with realistic dummy values, then applies overrides.
    - Returns the effective env dict so tests can assert against it.
    """
    _not_implemented("full_env")


@pytest.fixture
def igaa_env(full_env):
    """`full_env` variant with INSTAGRAM_ACCESS_TOKEN prefixed 'IGAA...'.

    Config built under this env must route to https://graph.instagram.com/.
    """
    _not_implemented("igaa_env")


@pytest.fixture
def eaa_env(full_env):
    """`full_env` variant with INSTAGRAM_ACCESS_TOKEN prefixed 'EAA...'.

    Config built under this env must route to https://graph.facebook.com/.
    """
    _not_implemented("eaa_env")


@pytest.fixture
def fake_storage():
    """In-memory StateStorageAdapter double with a call log.

    Contract:
    - Subclasses/implements the storage adapter interface used by StateManager
      (read_posts, write_posts, read_failed_positions, metadata read/write, ...).
    - Records every call as (method, args) in ``.calls`` and every write in
      ``.writes`` so tests can assert zero-writes-on-read and per-cycle write
      counts.
    - Seedable: ``fake_storage.seed(posts=[...], metadata={...}, failed=[...])``.
    - Failure injection: ``fake_storage.fail_next(method, exc)`` to simulate
      network errors / 403 / 500 on a specific operation.
    """
    _not_implemented("fake_storage")


@pytest.fixture
def mock_github_contents():
    """`responses`-based fake of the GitHub Contents API + get_branch.

    Contract: canned scenarios for GitFileStorageAdapter-level tests —
    404-first-run (file/branch absent), 403 (denied), 500, connection error,
    and success with realistic content/sha payloads. Exposes a scenario
    selector, e.g. ``mock_github_contents.scenario('first_run')``.
    """
    _not_implemented("mock_github_contents")


@pytest.fixture
def graph_api():
    """`responses`-based canned Meta Graph API payloads.

    Contract: for BOTH graph.facebook.com and graph.instagram.com —
    media container create success, media_publish success, error 190
    (expired token), rate-limit error, and refresh_access_token
    success/failure payloads. Registered lazily so tests opt into the calls
    they expect; unexpected calls fail the test (assert_all_requests_are_fired
    semantics where practical).
    """
    _not_implemented("graph_api")


@pytest.fixture
def sample_photo():
    """Factory for photo_models.EnrichedPhoto with realistic defaults.

    Contract: ``sample_photo(position=1, **overrides)`` returns an
    EnrichedPhoto dataclass instance (NOT a dict — the dict drift is what
    broke test_integration.py). Includes EXIF/description fields used by the
    blog-context path.
    """
    _not_implemented("sample_photo")


@pytest.fixture
def sample_album(sample_photo):
    """Factory for a list of EnrichedPhoto covering a small album (e.g. 5)."""
    _not_implemented("sample_album")


@pytest.fixture
def sample_posts_json():
    """Realistic posts.json content copied in shape from production state.

    Contract: returns a list of post dicts, at least one of which contains
    legacy ``retry_history`` keys and legacy ``flickr_photo_id`` naming —
    used by the hard compatibility contract test
    ``test_existing_posts_json_parses_unchanged``.
    """
    _not_implemented("sample_posts_json")


@pytest.fixture
def captured_emails(monkeypatch):
    """Patch the single SMTP send point; yield the list of sent messages.

    Contract: after WP4 there is exactly ONE place that constructs
    smtplib.SMTP — patch it there. Each captured item exposes at least
    (recipient, subject, text_body, html_body).
    """
    _not_implemented("captured_emails")


@pytest.fixture
def account_env_reisememo(full_env):
    """SECONDARY_* env preset for reisememo.ch.

    Contract: applies the secondary-account variables (account id, German
    language, reisememo.ch blog domains, WP auth key, User-Agent) on top of
    ``full_env`` so Config(account='reisememo') resolves the reisememo
    content path introduced in WP6.
    """
    _not_implemented("account_env_reisememo")
