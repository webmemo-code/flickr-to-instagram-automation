"""
Unit tests for the orchestration modules.

These tests focus on the modular components extracted from the main automation workflow,
enabling isolated testing of each phase without requiring live API credentials.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from orchestration import (
    PhotoSelector,
    PhotoValidator,
    CaptionOrchestrator,
    CaptionPreprocessor,
    InstagramPoster,
    ProgressTracker,
    PostingOrchestrator,
    StateOrchestrator,
    ValidationStateHandler,
    PhotoSelectionResult,
    CaptionResult,
    PostingResult,
    StateResult
)


class TestPhotoSelection:
    """Test photo selection orchestration."""

    @pytest.fixture
    def mock_flickr_api(self):
        """Mock FlickrAPI instance."""
        return Mock()

    @pytest.fixture
    def mock_state_manager(self):
        """Mock StateManager instance."""
        return Mock()

    @pytest.fixture
    def photo_selector(self, mock_flickr_api, mock_state_manager):
        """Create PhotoSelector instance."""
        return PhotoSelector(mock_flickr_api, mock_state_manager)

    def test_get_next_photo_success(self, photo_selector, mock_flickr_api, mock_state_manager):
        """Test successful photo selection."""
        # Setup mocks
        mock_photos = [
            {'id': '123', 'title': 'Test Photo', 'album_position': 1, 'url': 'http://example.com/photo.jpg'}
        ]
        mock_flickr_api.get_unposted_photos.return_value = mock_photos
        mock_state_manager.is_album_complete.return_value = False
        mock_state_manager.get_next_photo_to_post.return_value = mock_photos[0]

        # Execute
        result = photo_selector.get_next_photo_to_post()

        # Verify
        assert result.success is True
        assert result.photo == mock_photos[0]
        assert result.photos_total == 1
        assert "Selected photo #1" in result.message

    def test_get_next_photo_no_photos(self, photo_selector, mock_flickr_api):
        """Test photo selection when no photos are available."""
        # Setup mocks
        mock_flickr_api.get_unposted_photos.return_value = []

        # Execute
        result = photo_selector.get_next_photo_to_post()

        # Verify
        assert result.success is False
        assert result.message == "No photos found in the album"

    def test_get_next_photo_album_complete(self, photo_selector, mock_flickr_api, mock_state_manager):
        """Test photo selection when album is complete."""
        # Setup mocks
        mock_photos = [{'id': '123', 'title': 'Test Photo'}]
        mock_flickr_api.get_unposted_photos.return_value = mock_photos
        mock_state_manager.is_album_complete.return_value = True

        # Execute
        result = photo_selector.get_next_photo_to_post()

        # Verify
        assert result.success is True
        assert result.is_album_complete is True
        assert "Album complete" in result.message

    def test_photo_validator_success(self):
        """Test successful photo validation."""
        # Setup
        mock_instagram_api = Mock()
        mock_instagram_api.validate_image_url.return_value = True
        validator = PhotoValidator(mock_instagram_api)

        photo_data = {'url': 'http://example.com/photo.jpg', 'album_position': 1}

        # Execute
        is_valid, error_message = validator.validate_photo_for_posting(photo_data)

        # Verify
        assert is_valid is True
        assert error_message == ""

    def test_photo_validator_failure(self):
        """Test photo validation failure."""
        # Setup
        mock_instagram_api = Mock()
        mock_instagram_api.validate_image_url.return_value = False
        validator = PhotoValidator(mock_instagram_api)

        photo_data = {'url': 'http://example.com/invalid.jpg', 'album_position': 1}

        # Execute
        is_valid, error_message = validator.validate_photo_for_posting(photo_data)

        # Verify
        assert is_valid is False
        assert "Invalid or inaccessible image URL" in error_message


class TestCaptionOrchestration:
    """Test caption generation orchestration."""

    @pytest.fixture
    def mock_caption_generator(self):
        """Mock CaptionGenerator instance."""
        return Mock()

    @pytest.fixture
    def caption_orchestrator(self, mock_caption_generator):
        """Create CaptionOrchestrator instance."""
        return CaptionOrchestrator(mock_caption_generator)

    def test_generate_full_caption_success(self, caption_orchestrator, mock_caption_generator):
        """Test successful caption generation."""
        # Setup mocks
        generated_text = "Beautiful sunset over the ocean"
        full_caption = "Title: Sunset\n\nBeautiful sunset over the ocean\n\n#travel #sunset"

        mock_caption_generator.generate_with_retry.return_value = generated_text
        mock_caption_generator.build_full_caption.return_value = full_caption

        photo_data = {'id': '123', 'title': 'Sunset', 'url': 'http://example.com/photo.jpg'}

        # Execute
        result = caption_orchestrator.generate_full_caption(photo_data)

        # Verify
        assert result.success is True
        assert result.caption == full_caption
        assert result.generated_text == generated_text
        assert result.used_fallback is False

    def test_generate_full_caption_with_fallback(self, caption_orchestrator, mock_caption_generator):
        """Test caption generation with fallback."""
        # Setup mocks
        fallback_text = "Beautiful moment captured during our travels."
        full_caption = "Title: Photo\n\nBeautiful moment captured during our travels.\n\n#travel"

        mock_caption_generator.generate_with_retry.return_value = None  # Failed generation
        mock_caption_generator.build_full_caption.return_value = full_caption

        photo_data = {'id': '123', 'title': 'Photo'}

        # Execute
        result = caption_orchestrator.generate_full_caption(photo_data)

        # Verify
        assert result.success is True
        assert result.caption == full_caption
        assert result.generated_text == fallback_text
        assert result.used_fallback is True

    def test_caption_validation_success(self, caption_orchestrator):
        """Test successful caption validation."""
        # Execute
        is_valid, message = caption_orchestrator.validate_caption("This is a valid caption for Instagram posting.")

        # Verify
        assert is_valid is True
        assert "validation passed" in message

    def test_caption_validation_too_long(self, caption_orchestrator):
        """Test caption validation failure for length."""
        # Execute
        long_caption = "x" * 2201  # Exceeds Instagram's 2200 character limit
        is_valid, message = caption_orchestrator.validate_caption(long_caption)

        # Verify
        assert is_valid is False
        assert "too long" in message

    def test_caption_preprocessing(self):
        """Test caption preprocessing."""
        preprocessor = CaptionPreprocessor()

        # Test data
        photo_data = {
            'id': '123',
            'description': '  This is a description with extra spaces  '
        }

        # Execute
        result = preprocessor.preprocess_photo_data(photo_data)

        # Verify
        assert result['title'] == "Photo 123"  # Auto-generated title
        assert result['description'] == "This is a description with extra spaces"  # Cleaned description
        assert 'url_validated' in result


class TestPostingOrchestration:
    """Test Instagram posting orchestration."""

    @pytest.fixture
    def mock_instagram_api(self):
        """Mock InstagramAPI instance."""
        return Mock()

    @pytest.fixture
    def instagram_poster(self, mock_instagram_api):
        """Create InstagramPoster instance."""
        return InstagramPoster(mock_instagram_api)

    def test_post_photo_success(self, instagram_poster, mock_instagram_api):
        """Test successful photo posting."""
        # Setup mocks
        mock_instagram_api.post_with_retry.return_value = "insta_post_123"

        photo_data = {'id': '123', 'url': 'http://example.com/photo.jpg', 'album_position': 1}
        caption = "Test caption"

        # Execute
        result = instagram_poster.post_photo(photo_data, caption)

        # Verify
        assert result.success is True
        assert result.instagram_post_id == "insta_post_123"
        assert result.is_dry_run is False

    def test_post_photo_dry_run(self, instagram_poster):
        """Test photo posting in dry run mode."""
        photo_data = {'id': '123', 'url': 'http://example.com/photo.jpg', 'album_position': 1}
        caption = "Test caption"

        # Execute
        result = instagram_poster.post_photo(photo_data, caption, dry_run=True)

        # Verify
        assert result.success is True
        assert result.instagram_post_id is None
        assert result.is_dry_run is True
        assert "Dry run completed" in result.message

    def test_post_photo_failure(self, instagram_poster, mock_instagram_api):
        """Test photo posting failure."""
        # Setup mocks
        mock_instagram_api.post_with_retry.return_value = None

        photo_data = {'id': '123', 'url': 'http://example.com/photo.jpg', 'album_position': 1}
        caption = "Test caption"

        # Execute
        result = instagram_poster.post_photo(photo_data, caption)

        # Verify
        assert result.success is False
        assert result.instagram_post_id is None

    def test_progress_tracker(self):
        """Test progress tracking."""
        tracker = ProgressTracker()

        photo_data = {'album_position': 5}
        total_photos = 10

        # Execute
        progress_info = tracker.log_progress(photo_data, total_photos, posted=True)

        # Verify
        assert progress_info['current_position'] == 5
        assert progress_info['total_photos'] == 10
        assert progress_info['posted'] is True
        assert progress_info['is_complete'] is False

    def test_posting_orchestrator_workflow(self, mock_instagram_api):
        """Test complete posting workflow."""
        # Setup
        mock_instagram_api.post_with_retry.return_value = "insta_post_456"
        orchestrator = PostingOrchestrator(mock_instagram_api)

        photo_data = {'id': '456', 'url': 'http://example.com/photo2.jpg', 'album_position': 2}
        caption = "Test workflow caption"
        total_photos = 5

        # Execute
        result = orchestrator.execute_posting_workflow(photo_data, caption, total_photos)

        # Verify
        assert result['workflow_success'] is True
        assert result['posting_success'] is True
        assert result['instagram_post_id'] == "insta_post_456"
        assert result['progress_info']['current_position'] == 2


class TestStateOrchestration:
    """Test state management orchestration."""

    @pytest.fixture
    def mock_state_manager(self):
        """Mock StateManager instance."""
        return Mock()

    @pytest.fixture
    def mock_email_notifier(self):
        """Mock EmailNotifier instance."""
        return Mock()

    @pytest.fixture
    def state_orchestrator(self, mock_state_manager, mock_email_notifier):
        """Create StateOrchestrator instance."""
        return StateOrchestrator(mock_state_manager, mock_email_notifier)

    def test_record_successful_post(self, state_orchestrator, mock_state_manager):
        """Test recording successful post."""
        # Setup
        photo_data = {'id': '789', 'album_position': 3}
        instagram_post_id = "insta_success_789"

        # Execute
        result = state_orchestrator.record_post_outcome(photo_data, instagram_post_id)

        # Verify
        assert result.success is True
        assert "Successfully recorded post" in result.message
        mock_state_manager.create_post_record.assert_called_once_with(
            photo_data, instagram_post_id, is_dry_run=False, create_audit_issue=False
        )

    def test_record_failed_post(self, state_orchestrator, mock_state_manager):
        """Test recording failed post."""
        # Setup
        mock_state_manager.create_post_record.return_value = True
        photo_data = {'id': '789', 'album_position': 3}

        # Execute
        result = state_orchestrator.record_post_outcome(photo_data, None)

        # Verify
        assert result.success is True
        assert "Recorded failed post" in result.message
        assert result.critical_failure is False

    def test_record_critical_failure(self, state_orchestrator, mock_state_manager):
        """Test recording critical state failure."""
        # Setup
        mock_state_manager.create_post_record.return_value = False
        photo_data = {'id': '789', 'album_position': 3}

        # Execute
        result = state_orchestrator.record_post_outcome(photo_data, None)

        # Verify
        assert result.success is False
        assert result.critical_failure is True
        assert "Critical error" in result.message

    def test_handle_album_completion(self, state_orchestrator, mock_email_notifier):
        """Test album completion handling."""
        # Execute
        result = state_orchestrator.handle_album_completion(50, "Test Album")

        # Verify
        assert result.success is True
        mock_email_notifier.send_completion_notification.assert_called_once_with(50, "Test Album")

    def test_validation_state_handler(self, mock_state_manager):
        """Test validation failure state handling."""
        # Setup
        handler = ValidationStateHandler(mock_state_manager)
        photo_data = {'id': '999', 'album_position': 5}
        error_message = "Invalid image URL"

        # Execute
        result = handler.handle_validation_failure(photo_data, error_message)

        # Verify
        assert result.success is True
        assert error_message in result.message
        mock_state_manager.create_post_record.assert_called_once_with(
            photo_data, None, is_dry_run=False
        )


class TestIntegrationWorkflow:
    """Integration tests for the complete orchestrated workflow."""

    @pytest.fixture
    def mock_components(self):
        """Mock all required components."""
        return {
            'flickr_api': Mock(),
            'instagram_api': Mock(),
            'caption_generator': Mock(),
            'state_manager': Mock(),
            'email_notifier': Mock()
        }

    def test_successful_posting_workflow(self, mock_components):
        """Test end-to-end successful posting workflow."""
        # Setup mocks
        mock_photo = {'id': '111', 'title': 'Test Photo', 'album_position': 1, 'url': 'http://example.com/photo.jpg'}

        mock_components['flickr_api'].get_unposted_photos.return_value = [mock_photo]
        mock_components['state_manager'].is_album_complete.return_value = False
        mock_components['state_manager'].get_next_photo_to_post.return_value = mock_photo
        mock_components['instagram_api'].validate_image_url.return_value = True
        mock_components['caption_generator'].generate_with_retry.return_value = "Generated caption"
        mock_components['caption_generator'].build_full_caption.return_value = "Full caption with hashtags"
        mock_components['instagram_api'].post_with_retry.return_value = "insta_post_111"

        # Create orchestrators
        from orchestration import (
            create_photo_selector,
            create_photo_validator,
            create_caption_orchestrator,
            create_posting_orchestrator,
            create_state_orchestrator
        )

        photo_selector = create_photo_selector(mock_components['flickr_api'], mock_components['state_manager'])
        photo_validator = create_photo_validator(mock_components['instagram_api'])
        caption_orchestrator = create_caption_orchestrator(mock_components['caption_generator'])
        posting_orchestrator = create_posting_orchestrator(mock_components['instagram_api'])
        state_orchestrator = create_state_orchestrator(mock_components['state_manager'], mock_components['email_notifier'])

        # Execute workflow phases
        selection_result = photo_selector.get_next_photo_to_post()
        assert selection_result.success is True

        is_valid, _ = photo_validator.validate_photo_for_posting(selection_result.photo)
        assert is_valid is True

        caption_result = caption_orchestrator.generate_full_caption(selection_result.photo)
        assert caption_result.success is True

        posting_result = posting_orchestrator.execute_posting_workflow(
            selection_result.photo, caption_result.caption, 1
        )
        assert posting_result['workflow_success'] is True

        state_result = state_orchestrator.record_post_outcome(
            selection_result.photo, posting_result['instagram_post_id']
        )
        assert state_result.success is True

    def test_dry_run_workflow(self, mock_components):
        """Test dry run workflow execution."""
        # Setup for dry run
        mock_photo = {'id': '222', 'title': 'Dry Run Photo', 'album_position': 1, 'url': 'http://example.com/photo2.jpg'}

        mock_components['flickr_api'].get_unposted_photos.return_value = [mock_photo]
        mock_components['state_manager'].get_next_photo_to_post.return_value = mock_photo
        mock_components['instagram_api'].validate_image_url.return_value = True
        mock_components['caption_generator'].generate_with_retry.return_value = "Dry run caption"
        mock_components['caption_generator'].build_full_caption.return_value = "Dry run full caption"

        # Create orchestrators
        from orchestration import create_posting_orchestrator, create_state_orchestrator

        posting_orchestrator = create_posting_orchestrator(mock_components['instagram_api'])
        state_orchestrator = create_state_orchestrator(mock_components['state_manager'], mock_components['email_notifier'])

        # Execute dry run workflow
        posting_result = posting_orchestrator.execute_posting_workflow(
            mock_photo, "Dry run full caption", 1, dry_run=True
        )

        # Verify dry run behavior
        assert posting_result['workflow_success'] is True
        assert posting_result['is_dry_run'] is True
        assert posting_result['instagram_post_id'] is None

        # Verify state recording for dry run
        state_result = state_orchestrator.record_post_outcome(
            mock_photo, None, is_dry_run=True
        )
        assert state_result.success is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])