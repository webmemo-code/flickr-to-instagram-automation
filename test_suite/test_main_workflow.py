"""
Unit tests for the main posting workflow (post_next_photo).

These tests mock all external dependencies (APIs, state management) and verify
the correct behaviour of each workflow phase.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import main
from photo_models import PhotoListItem, EnrichedPhoto


@pytest.fixture(autouse=True)
def mock_env():
    """Provide required environment variables."""
    with patch.dict('os.environ', {'GITHUB_REPOSITORY': 'test/repo'}):
        yield


@pytest.fixture
def mock_deps():
    """Mock all external dependencies used by post_next_photo."""
    with patch('main.Config') as MockConfig, \
         patch('main.FlickrAPI') as MockFlickr, \
         patch('main.CaptionGenerator') as MockCaption, \
         patch('main.InstagramAPI') as MockInstagram, \
         patch('main.EmailNotifier') as MockEmail, \
         patch('main.StateManager') as MockState:

        config = MockConfig.return_value
        config.album_name = 'Test Album'
        config.album_url = 'https://flickr.com/test'
        config.create_audit_issues = False

        yield {
            'config': config,
            'flickr': MockFlickr.return_value,
            'caption': MockCaption.return_value,
            'instagram': MockInstagram.return_value,
            'email': MockEmail.return_value,
            'state': MockState.return_value,
        }


SAMPLE_PHOTO = PhotoListItem(
    id='123', title='Test Photo', album_position=1,
    url='http://example.com/photo.jpg',
    server='1234', secret='abc', date_taken='2024-01-01 12:00:00',
)

SAMPLE_ENRICHED = EnrichedPhoto(
    id='123', title='Test Photo', album_position=1,
    url='http://example.com/photo.jpg',
    server='1234', secret='abc', date_taken='2024-01-01 12:00:00',
    description='A test photo', hashtags='#test',
)


class TestPostNextPhoto:
    """Test the main post_next_photo workflow."""

    def test_successful_post(self, mock_deps):
        """Happy path: select, validate, caption, post, record."""
        mock_deps['flickr'].get_photo_list.return_value = [SAMPLE_PHOTO]
        mock_deps['flickr'].enrich_photo.return_value = SAMPLE_ENRICHED
        mock_deps['state'].is_album_complete.return_value = False
        mock_deps['state'].get_next_photo_to_post.return_value = SAMPLE_PHOTO
        mock_deps['instagram'].validate_image_url.return_value = True
        mock_deps['caption'].generate_with_retry.return_value = "Nice caption"
        mock_deps['caption'].build_full_caption.return_value = "Full caption"
        mock_deps['instagram'].post_with_retry.return_value = "insta_123"
        mock_deps['state'].create_post_record.return_value = "123"

        result = main.post_next_photo(dry_run=False, account='primary')

        assert result is True
        mock_deps['instagram'].post_with_retry.assert_called_once()
        mock_deps['state'].create_post_record.assert_called_once()

    def test_dry_run_skips_posting(self, mock_deps):
        """Dry run should NOT call post_with_retry but SHOULD record state."""
        mock_deps['flickr'].get_photo_list.return_value = [SAMPLE_PHOTO]
        mock_deps['flickr'].enrich_photo.return_value = SAMPLE_ENRICHED
        mock_deps['state'].is_album_complete.return_value = False
        mock_deps['state'].get_next_photo_to_post.return_value = SAMPLE_PHOTO
        mock_deps['instagram'].validate_image_url.return_value = True
        mock_deps['caption'].generate_with_retry.return_value = "Dry caption"
        mock_deps['caption'].build_full_caption.return_value = "Full dry caption"
        mock_deps['state'].create_post_record.return_value = "dry_run"

        result = main.post_next_photo(dry_run=True, account='primary')

        assert result is True
        mock_deps['instagram'].post_with_retry.assert_not_called()
        mock_deps['state'].create_post_record.assert_called_once()
        call_kwargs = mock_deps['state'].create_post_record.call_args
        assert call_kwargs[1]['is_dry_run'] is True

    def test_no_photos_returns_false(self, mock_deps):
        """Empty album should return False."""
        mock_deps['flickr'].get_photo_list.return_value = []

        result = main.post_next_photo(dry_run=False, account='primary')

        assert result is False

    def test_album_complete(self, mock_deps):
        """Album completion should return True and send notification."""
        mock_deps['flickr'].get_photo_list.return_value = [SAMPLE_PHOTO]
        mock_deps['state'].is_album_complete.return_value = True

        result = main.post_next_photo(dry_run=False, account='primary')

        assert result is True
        mock_deps['email'].send_completion_notification.assert_called_once()

    def test_validation_failure_continues(self, mock_deps):
        """Validation failure should record state and return True (non-fatal)."""
        mock_deps['flickr'].get_photo_list.return_value = [SAMPLE_PHOTO]
        mock_deps['flickr'].enrich_photo.return_value = SAMPLE_ENRICHED
        mock_deps['state'].is_album_complete.return_value = False
        mock_deps['state'].get_next_photo_to_post.return_value = SAMPLE_PHOTO
        mock_deps['instagram'].validate_image_url.return_value = False

        result = main.post_next_photo(dry_run=False, account='primary')

        assert result is True
        mock_deps['state'].create_post_record.assert_called_once()

    def test_posting_failure_returns_false(self, mock_deps):
        """Instagram posting failure should record state, track failed position, and return False."""
        mock_deps['flickr'].get_photo_list.return_value = [SAMPLE_PHOTO]
        mock_deps['flickr'].enrich_photo.return_value = SAMPLE_ENRICHED
        mock_deps['state'].is_album_complete.return_value = False
        mock_deps['state'].get_next_photo_to_post.return_value = SAMPLE_PHOTO
        mock_deps['instagram'].validate_image_url.return_value = True
        mock_deps['caption'].generate_with_retry.return_value = "Caption"
        mock_deps['caption'].build_full_caption.return_value = "Full caption"
        mock_deps['instagram'].post_with_retry.return_value = None  # Posting failed

        result = main.post_next_photo(dry_run=False, account='primary')

        assert result is False
        mock_deps['state'].create_post_record.assert_called_once()
        mock_deps['state'].record_failed_position.assert_called_once()

    def test_caption_fallback_on_failure(self, mock_deps):
        """Caption generation failure should use fallback text."""
        mock_deps['flickr'].get_photo_list.return_value = [SAMPLE_PHOTO]
        mock_deps['flickr'].enrich_photo.return_value = SAMPLE_ENRICHED
        mock_deps['state'].is_album_complete.return_value = False
        mock_deps['state'].get_next_photo_to_post.return_value = SAMPLE_PHOTO
        mock_deps['instagram'].validate_image_url.return_value = True
        mock_deps['caption'].generate_with_retry.return_value = None  # AI failed
        mock_deps['caption'].build_full_caption.return_value = "Fallback caption"
        mock_deps['instagram'].post_with_retry.return_value = "insta_456"
        mock_deps['state'].create_post_record.return_value = "123"

        result = main.post_next_photo(dry_run=False, account='primary')

        assert result is True
        # build_full_caption should have been called with fallback text
        call_args = mock_deps['caption'].build_full_caption.call_args[0]
        assert call_args[1] == "Beautiful moment captured during our travels."


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
