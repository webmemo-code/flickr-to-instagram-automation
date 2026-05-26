"""
Unit tests for the ThreadsAPI client.

External HTTP and time.sleep are mocked so tests are fast and offline.
"""
from unittest.mock import MagicMock, patch

import pytest

from threads_api import ThreadsAPI


def _config(threads_user_id='123', threads_access_token='IGAA-test'):
    """Build a Config-like mock with the fields ThreadsAPI consumes."""
    cfg = MagicMock()
    cfg.threads_user_id = threads_user_id
    cfg.threads_access_token = threads_access_token
    cfg.threads_endpoint_base = 'https://graph.threads.net/v1.0/'
    return cfg


def _json_response(status_code, payload):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = payload
    response.text = str(payload)
    return response


@pytest.fixture(autouse=True)
def _no_sleep():
    """Avoid burning seconds in retry/backoff tests."""
    with patch('threads_api.time.sleep'):
        yield


class TestThreadsAPICredentials:
    def test_missing_user_id_blocks_request(self):
        api = ThreadsAPI(_config(threads_user_id=None))
        with patch('threads_api.requests.post') as mock_post:
            result = api.create_media_container('http://example.com/p.jpg', 'hi')
        assert result is None
        mock_post.assert_not_called()

    def test_missing_token_blocks_request(self):
        api = ThreadsAPI(_config(threads_access_token=None))
        with patch('threads_api.requests.post') as mock_post:
            result = api.create_media_container('http://example.com/p.jpg', 'hi')
        assert result is None
        mock_post.assert_not_called()


class TestThreadsAPIContainer:
    def test_create_media_container_success(self):
        api = ThreadsAPI(_config())
        with patch('threads_api.requests.post') as mock_post:
            mock_post.return_value = _json_response(200, {'id': 'container-1'})
            container_id = api.create_media_container(
                'http://example.com/p.jpg', 'hello threads'
            )

        assert container_id == 'container-1'
        endpoint, _ = mock_post.call_args[0], mock_post.call_args[1]
        assert endpoint[0] == 'https://graph.threads.net/v1.0/123/threads'
        params = mock_post.call_args.kwargs['data']
        assert params['media_type'] == 'IMAGE'
        assert params['image_url'] == 'http://example.com/p.jpg'
        assert params['text'] == 'hello threads'
        assert params['access_token'] == 'IGAA-test'

    def test_create_media_container_error_returns_none(self):
        api = ThreadsAPI(_config())
        with patch('threads_api.requests.post') as mock_post:
            mock_post.return_value = _json_response(
                400, {'error': {'message': 'bad', 'code': 100}}
            )
            assert api.create_media_container('http://example.com/p.jpg', 'hi') is None

    def test_create_media_container_oauth_error_logged(self, caplog):
        api = ThreadsAPI(_config())
        with patch('threads_api.requests.post') as mock_post:
            mock_post.return_value = _json_response(
                400, {'error': {'message': 'Invalid OAuth access token', 'code': 190}}
            )
            api.create_media_container('http://example.com/p.jpg', 'hi')
        assert any('THREADS_ACCESS_TOKEN' in r.message for r in caplog.records)


class TestThreadsAPIPublish:
    def test_publish_success(self):
        api = ThreadsAPI(_config())
        with patch('threads_api.requests.post') as mock_post:
            mock_post.return_value = _json_response(200, {'id': 'post-7'})
            post_id = api.publish_media_container('container-1')
        assert post_id == 'post-7'
        endpoint = mock_post.call_args[0][0]
        assert endpoint == 'https://graph.threads.net/v1.0/123/threads_publish'
        params = mock_post.call_args.kwargs['data']
        assert params['creation_id'] == 'container-1'

    def test_publish_error_returns_none(self):
        api = ThreadsAPI(_config())
        with patch('threads_api.requests.post') as mock_post:
            mock_post.return_value = _json_response(
                500, {'error': {'message': 'oops', 'code': 1}}
            )
            assert api.publish_media_container('container-1') is None


class TestThreadsAPIPostWithRetry:
    def test_success_on_first_attempt(self):
        api = ThreadsAPI(_config())
        with patch.object(api, 'create_media_container', return_value='c1'), \
             patch.object(api, 'publish_media_container', return_value='p1'):
            result = api.post_with_retry('http://example.com/p.jpg', 'hi',
                                         publish_delay_seconds=0)
        assert result == 'p1'

    def test_retries_publish_failure_then_succeeds(self):
        api = ThreadsAPI(_config())
        with patch.object(api, 'create_media_container', return_value='c1'), \
             patch.object(api, 'publish_media_container',
                          side_effect=[None, None, 'p1']) as mock_pub:
            result = api.post_with_retry('http://example.com/p.jpg', 'hi',
                                         publish_delay_seconds=0)
        assert result == 'p1'
        assert mock_pub.call_count == 3

    def test_returns_none_after_max_retries(self):
        api = ThreadsAPI(_config())
        with patch.object(api, 'create_media_container', return_value='c1'), \
             patch.object(api, 'publish_media_container', return_value=None) as mock_pub:
            result = api.post_with_retry('http://example.com/p.jpg', 'hi',
                                         max_retries=2, publish_delay_seconds=0)
        assert result is None
        assert mock_pub.call_count == 2

    def test_container_failure_aborts_without_publish(self):
        api = ThreadsAPI(_config())
        with patch.object(api, 'create_media_container', return_value=None), \
             patch.object(api, 'publish_media_container') as mock_pub:
            result = api.post_with_retry('http://example.com/p.jpg', 'hi',
                                         publish_delay_seconds=0)
        assert result is None
        mock_pub.assert_not_called()

    def test_invalid_credentials_short_circuits(self):
        api = ThreadsAPI(_config(threads_user_id=None))
        with patch.object(api, 'create_media_container') as mock_create:
            result = api.post_with_retry('http://example.com/p.jpg', 'hi',
                                         publish_delay_seconds=0)
        assert result is None
        mock_create.assert_not_called()
