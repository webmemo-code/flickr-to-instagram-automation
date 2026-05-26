"""
Unit tests for Threads-related state handling.

Covers InstagramPost serialization with the new threads_* fields plus the
StateManager.get_posts_due_for_threads filter logic. State manager tests
inject posts via a stub so we don't touch the GitHub Contents API.
"""
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from state_models import InstagramPost, PostStatus, RetryAttempt


def _post(position=1, posted_at=None, status=PostStatus.POSTED,
          instagram_post_id='ig-1', threads_post_id=None,
          threads_retry_count=0, is_dry_run=False, generated_body=None):
    return InstagramPost(
        position=position,
        photo_id=f'photo-{position}',
        instagram_post_id=instagram_post_id,
        threads_post_id=threads_post_id,
        threads_retry_count=threads_retry_count,
        generated_body=generated_body,
        posted_at=posted_at,
        status=status,
        is_dry_run=is_dry_run,
    )


class TestInstagramPostSerialization:
    def test_round_trip_with_threads_fields(self):
        original = _post(
            position=3,
            posted_at='2026-05-20T10:00:00',
            threads_post_id='th-9',
            threads_retry_count=2,
            generated_body='AI body',
        )
        original.threads_posted_at = '2026-05-20T18:00:00'
        original.threads_caption = 'Short caption for Threads.'

        d = original.to_dict()
        assert d['threads_post_id'] == 'th-9'
        assert d['threads_retry_count'] == 2
        assert d['generated_body'] == 'AI body'
        assert d['threads_posted_at'] == '2026-05-20T18:00:00'
        assert d['threads_caption'] == 'Short caption for Threads.'

        round_tripped = InstagramPost.from_dict(d)
        assert round_tripped.threads_post_id == 'th-9'
        assert round_tripped.threads_retry_count == 2
        assert round_tripped.generated_body == 'AI body'
        assert round_tripped.threads_posted_at == '2026-05-20T18:00:00'
        assert round_tripped.threads_caption == 'Short caption for Threads.'

    def test_legacy_record_without_threads_fields_loads_with_defaults(self):
        legacy = {
            'position': 1, 'photo_id': 'p1',
            'instagram_post_id': 'ig-1', 'posted_at': '2026-05-01T00:00:00',
            'title': 'Old', 'status': 'posted', 'retry_count': 0,
            'retry_history': [], 'is_dry_run': False,
        }
        post = InstagramPost.from_dict(legacy)
        assert post.threads_post_id is None
        assert post.threads_retry_count == 0
        assert post.generated_body is None

    def test_mark_threads_posted_sets_fields(self):
        post = _post(posted_at='2026-05-20T10:00:00')
        post.mark_threads_posted('th-1', 'caption')
        assert post.threads_post_id == 'th-1'
        assert post.threads_caption == 'caption'
        assert post.threads_posted_at is not None

    def test_add_threads_retry_increments(self):
        post = _post()
        post.add_threads_retry()
        post.add_threads_retry()
        assert post.threads_retry_count == 2


@pytest.fixture
def state_manager():
    """A StateManager whose dependencies are stubbed enough to exercise the filter."""
    from state_manager import StateManager
    with patch('state_manager.Github'), \
         patch('state_manager.GitFileStorageAdapter'):
        config = MagicMock()
        config.flickr_album_id = 'album-1'
        config.account = 'primary'
        config.github_token = 'token'
        manager = StateManager.__new__(StateManager)
        manager.config = config
        manager.repo_name = 'test/repo'
        manager.current_album_id = 'album-1'
        manager.environment_name = 'primary-account'
        manager.storage_adapter = MagicMock()
        manager.github = MagicMock()
        manager.repo = MagicMock()
        import logging
        manager.logger = logging.getLogger('test')
        yield manager


def _hours_ago(hours):
    return (datetime.now() - timedelta(hours=hours)).isoformat()


class TestGetPostsDueForThreads:
    def test_returns_only_posts_older_than_delay(self, state_manager):
        posts = [
            _post(position=1, posted_at=_hours_ago(10)),  # eligible
            _post(position=2, posted_at=_hours_ago(2)),   # too recent
            _post(position=3, posted_at=_hours_ago(20)),  # eligible
        ]
        with patch.object(state_manager, 'get_instagram_posts', return_value=posts):
            due = state_manager.get_posts_due_for_threads(delay_hours=8)
        assert [p.position for p in due] == [3, 1]  # oldest first

    def test_excludes_already_mirrored(self, state_manager):
        posts = [
            _post(position=1, posted_at=_hours_ago(10), threads_post_id='th-1'),
            _post(position=2, posted_at=_hours_ago(10)),
        ]
        with patch.object(state_manager, 'get_instagram_posts', return_value=posts):
            due = state_manager.get_posts_due_for_threads(delay_hours=8)
        assert [p.position for p in due] == [2]

    def test_excludes_dry_runs(self, state_manager):
        posts = [
            _post(position=1, posted_at=_hours_ago(10), is_dry_run=True),
            _post(position=2, posted_at=_hours_ago(10)),
        ]
        with patch.object(state_manager, 'get_instagram_posts', return_value=posts):
            due = state_manager.get_posts_due_for_threads(delay_hours=8)
        assert [p.position for p in due] == [2]

    def test_excludes_failed_posts(self, state_manager):
        posts = [
            _post(position=1, posted_at=_hours_ago(10), status=PostStatus.FAILED,
                  instagram_post_id=None),
            _post(position=2, posted_at=_hours_ago(10)),
        ]
        with patch.object(state_manager, 'get_instagram_posts', return_value=posts):
            due = state_manager.get_posts_due_for_threads(delay_hours=8)
        assert [p.position for p in due] == [2]

    def test_excludes_posts_exceeding_retry_budget(self, state_manager):
        posts = [
            _post(position=1, posted_at=_hours_ago(10), threads_retry_count=5),
            _post(position=2, posted_at=_hours_ago(10), threads_retry_count=2),
        ]
        with patch.object(state_manager, 'get_instagram_posts', return_value=posts):
            due = state_manager.get_posts_due_for_threads(delay_hours=8, max_retries=5)
        assert [p.position for p in due] == [2]

    def test_unparseable_posted_at_is_skipped(self, state_manager):
        posts = [
            _post(position=1, posted_at='not-a-date'),
            _post(position=2, posted_at=_hours_ago(10)),
        ]
        with patch.object(state_manager, 'get_instagram_posts', return_value=posts):
            due = state_manager.get_posts_due_for_threads(delay_hours=8)
        assert [p.position for p in due] == [2]


class TestUpdateThreadsPostId:
    def test_updates_existing_position(self, state_manager):
        posts = [_post(position=1, posted_at=_hours_ago(10))]
        with patch.object(state_manager, 'get_instagram_posts', return_value=posts), \
             patch.object(state_manager, '_persist_posts', return_value=True) as mock_persist:
            ok = state_manager.update_threads_post_id(1, 'th-99', 'caption')
        assert ok is True
        mock_persist.assert_called_once()
        persisted = mock_persist.call_args[0][0]
        assert persisted[0].threads_post_id == 'th-99'
        assert persisted[0].threads_caption == 'caption'

    def test_missing_position_returns_false(self, state_manager):
        posts = [_post(position=1, posted_at=_hours_ago(10))]
        with patch.object(state_manager, 'get_instagram_posts', return_value=posts), \
             patch.object(state_manager, '_persist_posts') as mock_persist:
            ok = state_manager.update_threads_post_id(99, 'th-99', 'caption')
        assert ok is False
        mock_persist.assert_not_called()


class TestIncrementThreadsRetry:
    def test_increments_counter_and_persists(self, state_manager):
        posts = [_post(position=1, posted_at=_hours_ago(10))]
        with patch.object(state_manager, 'get_instagram_posts', return_value=posts), \
             patch.object(state_manager, '_persist_posts', return_value=True) as mock_persist:
            ok = state_manager.increment_threads_retry(1)
        assert ok is True
        persisted = mock_persist.call_args[0][0]
        assert persisted[0].threads_retry_count == 1
