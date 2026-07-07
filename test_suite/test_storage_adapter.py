"""WP3 — GitFileStorageAdapter behavior (error taxonomy, availability caching,
bootstrap, write safety).

These are offline unit tests: the adapter's PyGithub `repo` is replaced with a
MagicMock so no live GitHub calls are made. The taxonomy under test lives in
_read_json_file / _write_json_file / is_available.

Spec: docs/refactor/03-state-layer-spec.md.
"""

import base64
import json
from unittest.mock import MagicMock

import pytest
from github.GithubException import GithubException

from storage_adapter import (
    GitFileStorageAdapter,
    StateFileNotFound,
    StateStorageError,
)


def _adapter():
    """Build an adapter without running its GitHub-touching __init__."""
    adapter = GitFileStorageAdapter.__new__(GitFileStorageAdapter)
    adapter.repo_name = 'owner/repo'
    adapter.github_token = 'token'
    adapter.branch = 'automation-state'
    adapter._available = True  # skip the live get_branch check by default
    import logging
    adapter.logger = logging.getLogger('test')
    adapter.github = MagicMock()
    adapter.repo = MagicMock()
    return adapter


def _contents(payload):
    """Build a fake Contents API response object like PyGithub returns."""
    obj = MagicMock()
    obj.content = base64.b64encode(json.dumps(payload).encode()).decode()
    obj.sha = 'deadbeef'
    return obj


def _github_error(status):
    return GithubException(status, data={'message': f'status {status}'}, headers={})


class TestErrorTaxonomy:
    def test_missing_file_reported_as_absent_not_error(self):
        """Contents API 404 for a state file surfaces as the typed 'absent'
        outcome (StateFileNotFound) — distinguishable from failures WITHOUT
        string-matching '404'. read_posts translates that to an empty list."""
        adapter = _adapter()
        adapter.repo.get_contents.side_effect = _github_error(404)

        with pytest.raises(StateFileNotFound):
            adapter._read_json_file('state-data/primary/album-1/posts.json')

        # The public read method translates absent -> empty (first-run bootstrap)
        assert adapter.read_posts('primary', '1') == []

    def test_denied_and_server_errors_raise(self):
        """401/403, 5xx, rate-limit, connection errors, and JSON parse errors
        raise StateStorageError — never converted into an empty-state result."""
        for status in (401, 403, 429, 500, 502, 503):
            adapter = _adapter()
            adapter.repo.get_contents.side_effect = _github_error(status)
            with pytest.raises(StateStorageError):
                adapter.read_posts('primary', '1')

        # Connection error (non-GithubException) also raises
        adapter = _adapter()
        adapter.repo.get_contents.side_effect = ConnectionError('reset by peer')
        with pytest.raises(StateStorageError):
            adapter.read_posts('primary', '1')

        # Malformed JSON raises rather than returning empty
        adapter = _adapter()
        bad = MagicMock()
        bad.content = base64.b64encode(b'{not valid json').decode()
        adapter.repo.get_contents.return_value = bad
        with pytest.raises(StateStorageError):
            adapter.read_posts('primary', '1')

    def test_successful_read_returns_parsed_data(self):
        """A successful read returns the parsed JSON payload."""
        adapter = _adapter()
        payload = [{'position': 1, 'photo_id': 'abc'}]
        adapter.repo.get_contents.return_value = _contents(payload)
        assert adapter.read_posts('primary', '1') == payload

    def test_unavailable_backend_raises_not_empty(self):
        """When the branch can't be reached at all, reads raise StateStorageError
        rather than silently returning empty (an unreachable branch is a
        Denied/Failed outcome, not Absent)."""
        adapter = _adapter()
        adapter._available = False
        with pytest.raises(StateStorageError):
            adapter.read_posts('primary', '1')


class TestAvailabilityCaching:
    def test_is_available_cached_per_process(self):
        """N consecutive reads/writes trigger exactly ONE get_branch call —
        the availability check is cached for the adapter instance lifetime."""
        adapter = _adapter()
        adapter._available = None  # force a real (mocked) check
        adapter.repo.get_branch.return_value = MagicMock()
        adapter.repo.get_contents.side_effect = _github_error(404)

        # 5 reads + interleaved availability checks
        for _ in range(5):
            adapter.read_posts('primary', '1')
            adapter.read_failed_positions('primary', '1')

        assert adapter.repo.get_branch.call_count == 1


class TestBootstrap:
    def test_branch_autocreation_on_first_run(self):
        """REGRESSION: when the automation-state branch does not exist, the
        adapter creates it from the default branch (current behavior)."""
        adapter = _adapter()
        # get_branch raises 404 -> triggers creation path
        adapter.repo.get_branch.side_effect = _github_error(404)
        adapter.repo.default_branch = 'main'
        ref = MagicMock()
        ref.object.sha = 'basesha'
        adapter.repo.get_git_ref.return_value = ref

        created = adapter._ensure_branch_exists()

        assert created is True
        adapter.repo.create_git_ref.assert_called_once_with(
            'refs/heads/automation-state', 'basesha'
        )

    def test_absent_file_after_bootstrap_returns_empty_not_raise(self):
        """After the branch exists, a missing state file reports absent
        (empty) rather than raising."""
        adapter = _adapter()
        adapter.repo.get_contents.side_effect = _github_error(404)
        assert adapter.read_metadata('primary', '1')['album_id'] == '1'


class TestWrites:
    def test_write_failure_is_never_swallowed(self):
        """A failed write (stale sha / 5xx) raises StateStorageError — it can
        never be reported to StateManager as success."""
        adapter = _adapter()
        # get_contents succeeds (file exists), update_file fails with 5xx
        adapter.repo.get_contents.return_value = _contents([])
        adapter.repo.update_file.side_effect = _github_error(500)

        with pytest.raises(StateStorageError):
            adapter.write_posts('primary', '1', [{'position': 1}])

    def test_successful_write_returns_true(self):
        """A successful write returns True."""
        adapter = _adapter()
        adapter.repo.get_contents.return_value = _contents([])
        adapter.repo.update_file.return_value = MagicMock()
        assert adapter.write_posts('primary', '1', [{'position': 1}]) is True

    def test_create_file_on_absent_target(self):
        """Writing to an absent file path creates it (create_file), not update."""
        adapter = _adapter()
        adapter.repo.get_contents.side_effect = _github_error(404)
        adapter.repo.create_file.return_value = MagicMock()
        assert adapter.write_posts('primary', '1', [{'position': 1}]) is True
        adapter.repo.create_file.assert_called_once()
