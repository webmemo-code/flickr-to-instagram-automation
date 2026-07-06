"""WP3 scaffold — state-layer safety (StateManager).

Spec: docs/refactor/03-state-layer-spec.md. Fixtures: test_suite/conftest.py.

Each test docstring IS the behavior spec. Implement the test body per the
docstring, remove the xfail marker in the WP3 PR, then implement production
code until green. Tests tagged REGRESSION must pass BEFORE the production
change as well as after.
"""

import pytest

WP3 = pytest.mark.xfail(reason="WP3 not implemented", strict=False)


class TestFailLoudReads:
    @WP3
    def test_read_error_raises_critical_state_failure(self):
        """A network error or HTTP 500 while reading posts.json raises
        CriticalStateFailure — get_instagram_posts must never return [] on a
        failed read.

        Use fake_storage.fail_next('read_posts', ConnectionError(...)) and
        assert pytest.raises(CriticalStateFailure). Repeat for a 500-style
        GithubException and a rate-limit error.
        """
        pytest.fail("scaffold: implement per docstring")

    @WP3
    def test_read_403_raises_critical_state_failure(self):
        """REGRESSION: the existing 403/permission path still raises
        CriticalStateFailure and sends the critical-failure alert."""
        pytest.fail("scaffold: implement per docstring")

    @WP3
    def test_first_run_404_returns_empty_state(self):
        """A 404 'state file does not exist yet' (fresh album / first-ever
        run) returns empty state WITHOUT raising — the only case that may
        return empty. Branch auto-creation bootstrap keeps working."""
        pytest.fail("scaffold: implement per docstring")

    @WP3
    def test_get_next_photo_never_restarts_after_read_failure(self):
        """With 5 photos already posted and the posts read failing,
        get_next_photo_to_post raises rather than returning photo 1
        (the silent album-restart this refactor exists to prevent)."""
        pytest.fail("scaffold: implement per docstring")


class TestReadsDoNotWrite:
    @WP3
    def test_is_album_complete_performs_no_writes(self):
        """After calling is_album_complete against seeded fake_storage,
        the fake_storage write log is EMPTY (metadata must no longer be
        rewritten on read paths)."""
        pytest.fail("scaffold: implement per docstring")

    @WP3
    def test_stats_performs_no_writes(self):
        """The --stats path (show_stats / its StateManager calls) performs
        zero storage writes."""
        pytest.fail("scaffold: implement per docstring")


class TestWriteBatching:
    @WP3
    def test_posting_cycle_max_two_writes(self):
        """One successful posting cycle (record post + update metadata)
        produces at most 2 storage writes. Failed-position handling is
        unchanged. Write ORDER preserves the current commit point so a
        concurrent Threads run never sees a post without its threads-due
        record (see spec §Write batching)."""
        pytest.fail("scaffold: implement per docstring")


class TestCleanup:
    @WP3
    def test_state_manager_has_no_direct_github_client(self):
        """StateManager no longer constructs/holds its own Github client or
        repo — storage access goes only through the storage adapter."""
        pytest.fail("scaffold: implement per docstring")


class TestDataCompatibility:
    @WP3
    def test_existing_posts_json_parses_unchanged(self):
        """REGRESSION (hard contract): sample_posts_json — including a legacy
        entry with retry_history keys and flickr_photo_id naming — loads into
        InstagramPost records and round-trips back without schema changes.
        Must pass before AND after WP3/WP5."""
        pytest.fail("scaffold: implement per docstring")


class TestWP5Additions:
    """Scaffolded here because WP5 edits the same module family."""

    XFAIL_WP5 = pytest.mark.xfail(reason="WP5 not implemented", strict=False)

    @XFAIL_WP5
    def test_legacy_retry_history_ignored_on_load(self):
        """After WP5 removes RetryAttempt/retry_history/RETRYING, loading a
        stored post that still contains those keys succeeds (unknown keys
        ignored, never required)."""
        pytest.fail("scaffold: implement per docstring")

    @XFAIL_WP5
    def test_main_uses_instagram_api_validate_image_url(self):
        """main.instagram_api_url_ok is deleted; the posting path validates
        image URLs via InstagramAPI.validate_image_url (canonical semantics:
        retries, requires 200 + image/* content type)."""
        pytest.fail("scaffold: implement per docstring")
