"""
Unit tests for main.post_due_threads and helpers.

Exercises the orchestration path with all external dependencies mocked.
"""
from unittest.mock import MagicMock, patch

import pytest

import main
from photo_models import PhotoListItem
from state_models import InstagramPost, PostStatus


@pytest.fixture(autouse=True)
def _mock_env():
    with patch.dict('os.environ', {'GITHUB_REPOSITORY': 'test/repo'}):
        yield


def _post_record(position=1, photo_id='photo-1', generated_body='AI body'):
    p = InstagramPost(
        position=position,
        photo_id=photo_id,
        instagram_post_id='ig-1',
        posted_at='2026-05-20T10:00:00',
        status=PostStatus.POSTED,
        generated_body=generated_body,
    )
    return p


def _photo(position=1, photo_id='photo-1'):
    return PhotoListItem(
        id=photo_id, title='Test', album_position=position,
        url='http://example.com/p.jpg', server='1', secret='a',
        date_taken='2024-01-01 12:00:00',
    )


@pytest.fixture
def threads_mocks():
    with patch('main.Config') as MockConfig, \
         patch('main.FlickrAPI') as MockFlickr, \
         patch('main.CaptionGenerator') as MockCap, \
         patch('main.StateManager') as MockState, \
         patch('main.account_manager') as MockAcct, \
         patch('threads_api.ThreadsAPI') as MockThreads:

        config = MockConfig.return_value
        config.threads_posting_enabled = True
        config.threads_post_delay_hours = 8
        config.threads_max_chars = 500

        MockAcct.get_environment_name.return_value = 'primary-account'

        yield {
            'config': config,
            'flickr': MockFlickr.return_value,
            'caption': MockCap.return_value,
            'state': MockState.return_value,
            'threads': MockThreads.return_value,
        }


class TestPostDueThreadsDryRun:
    def test_missing_photo_in_dry_run_does_not_mutate_state(self, threads_mocks):
        m = threads_mocks
        m['state'].get_posts_due_for_threads.return_value = [_post_record()]
        # Album listing missing the post's photo.
        m['flickr'].get_photo_list.return_value = []

        ok = main.post_due_threads(dry_run=True, account='primary')

        assert ok is True
        m['state'].increment_threads_retry.assert_not_called()
        m['state'].update_threads_post_id.assert_not_called()

    def test_missing_photo_in_live_run_does_increment_retry(self, threads_mocks):
        m = threads_mocks
        m['state'].get_posts_due_for_threads.return_value = [_post_record()]
        m['flickr'].get_photo_list.return_value = []

        ok = main.post_due_threads(dry_run=False, account='primary')

        assert ok is False
        m['state'].increment_threads_retry.assert_called_once_with(1)

    def test_dry_run_does_not_call_threads_api(self, threads_mocks):
        m = threads_mocks
        m['state'].get_posts_due_for_threads.return_value = [_post_record()]
        m['flickr'].get_photo_list.return_value = [_photo()]
        m['flickr'].enrich_photo.return_value = MagicMock(url='http://x/p.jpg')
        m['caption'].build_threads_caption.return_value = 'short threads caption'

        with patch('threads_api.ThreadsAPI') as MockThreads:
            ok = main.post_due_threads(dry_run=True, account='primary')
            MockThreads.return_value.post_with_retry.assert_not_called()
        assert ok is True
        m['state'].update_threads_post_id.assert_not_called()


class TestPostDueThreadsDisabled:
    def test_returns_true_when_not_configured(self, threads_mocks):
        threads_mocks['config'].threads_posting_enabled = False
        ok = main.post_due_threads(account='primary')
        assert ok is True
        threads_mocks['state'].get_posts_due_for_threads.assert_not_called()


class TestInstagramApiUrlOk:
    def test_follows_redirects(self):
        with patch('main.requests' if False else 'requests.head') as mock_head:
            # head should be called with allow_redirects=True
            mock_head.return_value = MagicMock(
                status_code=200,
                headers={'content-type': 'image/jpeg'},
            )
            ok = main.instagram_api_url_ok('http://example.com/p.jpg')
            assert ok is True
            assert mock_head.call_args.kwargs.get('allow_redirects') is True

    def test_non_image_content_type_rejected(self):
        with patch('requests.head') as mock_head:
            mock_head.return_value = MagicMock(
                status_code=200,
                headers={'content-type': 'text/html'},
            )
            assert main.instagram_api_url_ok('http://example.com/x') is False

    def test_non_200_rejected(self):
        with patch('requests.head') as mock_head:
            mock_head.return_value = MagicMock(
                status_code=404,
                headers={'content-type': 'image/jpeg'},
            )
            assert main.instagram_api_url_ok('http://example.com/x') is False

    def test_request_exception_returns_false(self):
        import requests
        with patch('requests.head', side_effect=requests.exceptions.Timeout):
            assert main.instagram_api_url_ok('http://example.com/x') is False
