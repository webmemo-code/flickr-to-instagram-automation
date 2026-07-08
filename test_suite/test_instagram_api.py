"""Unit tests for InstagramAPI.validate_image_url.

Added alongside WP5 (main.instagram_api_url_ok removal) to cover the
redirect-following behavior this method must have now that it is the
canonical URL validator for both the primary posting path and the delayed
Threads cross-post path.
"""
from unittest.mock import MagicMock, patch

from instagram_api import InstagramAPI


def _api():
    return InstagramAPI(config=MagicMock())


class TestValidateImageUrl:
    def test_follows_redirects(self):
        """REGRESSION: requests.head() defaults allow_redirects=False; Flickr
        and most CDN hosts respond with 301/302 for canonical image URLs, so
        the call must explicitly request redirects be followed."""
        with patch('requests.head') as mock_head:
            mock_head.return_value = MagicMock(
                status_code=200,
                headers={'content-type': 'image/jpeg'},
            )
            assert _api().validate_image_url('http://example.com/p.jpg') is True
            assert mock_head.call_args.kwargs.get('allow_redirects') is True

    def test_non_image_content_type_rejected(self):
        with patch('requests.head') as mock_head:
            mock_head.return_value = MagicMock(
                status_code=200,
                headers={'content-type': 'text/html'},
            )
            assert _api().validate_image_url('http://example.com/x') is False

    def test_non_200_rejected_after_retries(self):
        with patch('requests.head') as mock_head, patch('time.sleep'):
            mock_head.return_value = MagicMock(
                status_code=404,
                headers={'content-type': 'image/jpeg'},
            )
            assert _api().validate_image_url('http://example.com/x', max_retries=2, retry_delay=0) is False

    def test_request_exception_returns_false(self):
        import requests
        with patch('requests.head', side_effect=requests.exceptions.Timeout), patch('time.sleep'):
            assert _api().validate_image_url('http://example.com/x', max_retries=2, retry_delay=0) is False
