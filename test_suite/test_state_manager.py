"""WP3 — state-layer safety (StateManager).

Fail-loud reads, read paths that never write, write batching, and the hard
posts.json compatibility contract. Uses the fake_storage / sample_posts_json
fixtures from conftest.py; no live GitHub calls.

Spec: docs/refactor/03-state-layer-spec.md.
"""

import logging
from unittest.mock import MagicMock

import pytest

from notification_system import CriticalStateFailure
from state_manager import StateManager
from state_models import InstagramPost, PostStatus
from storage_adapter import StateStorageError


def _make_state_manager(fake_storage, account='primary', album_id='1'):
    """Build a StateManager wired to fake_storage without touching GitHub."""
    sm = StateManager.__new__(StateManager)
    sm.config = MagicMock()
    sm.repo_name = 'owner/repo'
    sm.logger = logging.getLogger('test-sm')
    sm.current_album_id = album_id
    sm.environment_name = 'primary-account' if account == 'primary' else 'secondary-account'
    sm.storage_adapter = fake_storage
    return sm


def _posted(position, photo_id):
    return {
        'position': position,
        'photo_id': photo_id,
        'instagram_post_id': f'ig{position}',
        'status': 'posted',
        'posted_at': '2025-01-15T08:00:00',
        'account': 'primary',
    }


class TestFailLoudReads:
    def test_read_error_raises_critical_state_failure(self, fake_storage):
        """A network error / 500 / rate-limit while reading posts.json raises
        CriticalStateFailure — get_instagram_posts must never return []."""
        for exc in (ConnectionError('reset'),
                    StateStorageError('500 server error'),
                    StateStorageError('403 rate limit exceeded')):
            sm = _make_state_manager(fake_storage)
            fake_storage.fail_next('read_posts', exc)
            with pytest.raises(CriticalStateFailure):
                sm.get_instagram_posts()

    def test_read_403_raises_critical_state_failure(self, fake_storage, monkeypatch):
        """REGRESSION: the permission-denied path raises CriticalStateFailure
        AND fires the critical-failure alert."""
        alert = MagicMock()
        monkeypatch.setattr('state_manager.notifier.send_critical_failure_alert', alert)
        sm = _make_state_manager(fake_storage)
        fake_storage.fail_next('read_posts', StateStorageError('403 Forbidden'))

        with pytest.raises(CriticalStateFailure):
            sm.get_instagram_posts()
        alert.assert_called_once()

    def test_first_run_404_returns_empty_state(self, fake_storage):
        """A fresh album (no posts file) returns empty state WITHOUT raising —
        the only case that may return empty."""
        sm = _make_state_manager(fake_storage)
        # No seed => fake read_posts returns [] (absent)
        assert sm.get_instagram_posts() == []

    def test_get_next_photo_never_restarts_after_read_failure(self, fake_storage, sample_album):
        """With photos already posted and the posts read failing,
        get_next_photo_to_post raises rather than returning photo 1."""
        photos = sample_album(5)
        fake_storage.seed(posts=[_posted(i, photos[i - 1].id) for i in range(1, 6)])
        sm = _make_state_manager(fake_storage)

        # Sanity: with a healthy read it would return None (all posted)
        assert sm.get_next_photo_to_post(photos) is None

        # Now the read fails -> must raise, never return photos[0]
        fake_storage.fail_next('read_posts', StateStorageError('500'))
        with pytest.raises(CriticalStateFailure):
            sm.get_next_photo_to_post(photos)


class TestReadsDoNotWrite:
    def test_is_album_complete_performs_no_writes(self, fake_storage, sample_album):
        """is_album_complete performs zero storage writes."""
        photos = sample_album(3)
        fake_storage.seed(posts=[_posted(i, photos[i - 1].id) for i in range(1, 4)])
        sm = _make_state_manager(fake_storage)

        assert sm.is_album_complete(3) is True
        assert fake_storage.writes == []

    def test_stats_performs_no_writes(self, fake_storage, sample_album):
        """The --stats data path (get_statistics + getters) performs zero
        storage writes."""
        photos = sample_album(2)
        fake_storage.seed(posts=[_posted(i, photos[i - 1].id) for i in range(1, 3)])
        sm = _make_state_manager(fake_storage)

        sm.get_statistics()
        sm.get_album_metadata()
        sm.get_failed_positions()
        sm.get_instagram_posts()
        sm.is_album_complete(2)

        assert fake_storage.writes == []


class TestWriteBatching:
    def test_posting_cycle_max_two_writes(self, fake_storage, sample_photo, monkeypatch):
        """One successful posting cycle produces at most 2 storage writes
        (posts + metadata), posts written FIRST (the Threads-compat commit
        point). Failed-position handling is unchanged."""
        monkeypatch.setattr('state_manager.os.getenv', lambda *a, **k: None)
        photo = sample_photo(position=1)
        sm = _make_state_manager(fake_storage)

        sm.create_post_record(photo, instagram_post_id='ig1')

        write_methods = [w[0] for w in fake_storage.writes]
        # A never-previously-failed photo: exactly posts + metadata
        assert write_methods == ['write_posts', 'write_metadata']

    def test_posting_cycle_writes_posts_before_metadata(self, fake_storage, sample_photo, monkeypatch):
        """Write ORDER: posts file is committed before metadata so a concurrent
        Threads run never sees a post without its threads-due record."""
        monkeypatch.setattr('state_manager.os.getenv', lambda *a, **k: None)
        sm = _make_state_manager(fake_storage)
        sm.create_post_record(sample_photo(position=1), instagram_post_id='ig1')

        write_methods = [w[0] for w in fake_storage.writes]
        assert write_methods.index('write_posts') < write_methods.index('write_metadata')

    def test_write_failure_on_posts_returns_none(self, fake_storage, sample_photo, monkeypatch):
        """If persisting the posts file fails, create_post_record returns None
        (never a success id) and does not proceed to write metadata."""
        monkeypatch.setattr('state_manager.os.getenv', lambda *a, **k: None)
        sm = _make_state_manager(fake_storage)
        fake_storage.fail_next('write_posts', StateStorageError('stale sha'))

        result = sm.create_post_record(sample_photo(position=1), instagram_post_id='ig1')
        assert result is None
        assert 'write_metadata' not in [w[0] for w in fake_storage.writes]

    def test_metadata_write_failure_still_reports_success(self, fake_storage, sample_photo, monkeypatch):
        """The posts file is the source of truth and is written first. If only
        the derived metadata write fails, the post is already durable, so
        create_post_record returns success (not None) — returning None would
        trigger a spurious re-post of an already-recorded photo. The derived
        stats self-heal on the next run."""
        monkeypatch.setattr('state_manager.os.getenv', lambda *a, **k: None)
        sm = _make_state_manager(fake_storage)
        fake_storage.fail_next('write_metadata', StateStorageError('500 on metadata'))

        result = sm.create_post_record(sample_photo(position=1), instagram_post_id='ig1')

        # Posts write succeeded -> post is recorded -> success id returned
        assert result == sample_photo(position=1).id
        assert 'write_posts' in [w[0] for w in fake_storage.writes]


class TestCleanup:
    def test_state_manager_has_no_direct_github_client(self, fake_storage):
        """StateManager no longer holds its own Github client or repo."""
        sm = _make_state_manager(fake_storage)
        assert not hasattr(sm, 'github')
        assert not hasattr(sm, 'repo')

    def test_state_manager_source_constructs_no_github(self):
        """The StateManager __init__ source no longer constructs a Github client
        (storage access goes solely through the adapter)."""
        import inspect
        import state_manager
        src = inspect.getsource(state_manager.StateManager.__init__)
        assert 'Github(' not in src
        assert 'self.github' not in src
        assert 'self.repo ' not in src


class TestDataCompatibility:
    def test_existing_posts_json_parses_unchanged(self, sample_posts_json):
        """REGRESSION (hard contract): sample_posts_json — including a legacy
        entry with retry_history keys and flickr_photo_id naming — loads into
        InstagramPost records and round-trips without schema changes."""
        posts = [InstagramPost.from_dict(p) for p in sample_posts_json]

        # Legacy flickr_photo_id normalized to photo_id
        assert posts[1].photo_id == '5388309999'
        # Status enum round-trips
        assert posts[0].status == PostStatus.POSTED
        assert posts[1].status == PostStatus.FAILED

        # Round-trip back to dict preserves the canonical shape
        dumped = posts[0].to_dict()
        assert dumped['photo_id'] == '5388301001'
        assert dumped['status'] == 'posted'
        assert 'retry_history' in dumped

    def test_load_via_state_manager_skips_only_bad_records(self, fake_storage, sample_posts_json):
        """A single malformed record is skipped (logged), not treated as an
        access failure; valid records still load."""
        bad = {'position': 'not-an-int', 'status': 'bogus-status'}
        fake_storage.seed(posts=sample_posts_json + [bad])
        sm = _make_state_manager(fake_storage)

        posts = sm.get_instagram_posts()
        # 2 good records from the fixture; the bad one is dropped
        assert len(posts) == 2


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
