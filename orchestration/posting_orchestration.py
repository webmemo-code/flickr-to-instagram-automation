"""
Instagram posting orchestration module.

This module handles the Instagram posting workflow, including dry run mode,
posting with retries, and progress tracking.
"""

import logging
from typing import Dict, Optional
from instagram_api import InstagramAPI


class PostingResult:
    """Result of Instagram posting operation."""

    def __init__(self, success: bool, instagram_post_id: Optional[str] = None,
                 is_dry_run: bool = False, message: str = ""):
        self.success = success
        self.instagram_post_id = instagram_post_id
        self.is_dry_run = is_dry_run
        self.message = message


class InstagramPoster:
    """Handles Instagram posting logic."""

    def __init__(self, instagram_api: InstagramAPI):
        self.instagram_api = instagram_api
        self.logger = logging.getLogger(__name__)

    def post_photo(self, photo_data: Dict, caption: str, dry_run: bool = False) -> PostingResult:
        """
        Post a photo to Instagram with the given caption.

        Args:
            photo_data: Photo data dictionary
            caption: Caption text for the post
            dry_run: Whether to run in dry run mode

        Returns:
            PostingResult with posting status and Instagram post ID
        """
        try:
            position = photo_data.get('album_position', 'unknown')

            if dry_run:
                self.logger.info("🧪 DRY RUN: Would post to Instagram")
                self.logger.info(f"Image URL: {photo_data['url']}")
                self.logger.info(f"Caption: {caption}")
                self.logger.info(f"✅ Dry run completed for photo #{position}")

                return PostingResult(
                    success=True,
                    is_dry_run=True,
                    message=f"Dry run completed for photo #{position}"
                )

            # Post to Instagram
            self.logger.info("📱 Posting to Instagram...")
            instagram_post_id = self.instagram_api.post_with_retry(photo_data['url'], caption)

            if instagram_post_id:
                self.logger.info(f"✅ Successfully posted to Instagram: {instagram_post_id}")
                return PostingResult(
                    success=True,
                    instagram_post_id=instagram_post_id,
                    message=f"Successfully posted photo #{position}"
                )
            else:
                self.logger.error("❌ Failed to post to Instagram")
                return PostingResult(
                    success=False,
                    message=f"Failed to post photo #{position} to Instagram"
                )

        except Exception as e:
            error_msg = f"Instagram posting failed: {e}"
            self.logger.error(error_msg)
            return PostingResult(
                success=False,
                message=error_msg
            )


class ProgressTracker:
    """Tracks posting progress and completion status."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def log_progress(self, photo_data: Dict, total_photos: int, posted: bool = True) -> Dict:
        """
        Log progress information for a photo.

        Args:
            photo_data: Photo data dictionary
            total_photos: Total number of photos in album
            posted: Whether the photo was successfully posted

        Returns:
            Dictionary with progress information
        """
        try:
            position = photo_data.get('album_position', 'unknown')

            progress_info = {
                'current_position': position,
                'total_photos': total_photos,
                'posted': posted,
                'is_complete': False
            }

            if posted:
                self.logger.info(f"📊 Progress: Posted {position}/{total_photos} photos (just posted #{position})")

                # Check if album is complete
                if isinstance(position, int) and position >= total_photos:
                    self.logger.info("🎉 Album complete! All photos have been posted.")
                    progress_info['is_complete'] = True

            return progress_info

        except Exception as e:
            self.logger.error(f"Progress tracking failed: {e}")
            return {
                'current_position': 'unknown',
                'total_photos': total_photos,
                'posted': posted,
                'is_complete': False,
                'error': str(e)
            }

    def is_album_complete(self, current_position: int, total_photos: int) -> bool:
        """
        Check if the album posting is complete.

        Args:
            current_position: Current photo position
            total_photos: Total number of photos

        Returns:
            True if album is complete
        """
        try:
            return current_position >= total_photos
        except Exception:
            return False


class PostingOrchestrator:
    """Orchestrates the complete posting workflow."""

    def __init__(self, instagram_api: InstagramAPI):
        self.poster = InstagramPoster(instagram_api)
        self.progress_tracker = ProgressTracker()
        self.logger = logging.getLogger(__name__)

    def execute_posting_workflow(self, photo_data: Dict, caption: str,
                                total_photos: int, dry_run: bool = False) -> Dict:
        """
        Execute the complete posting workflow.

        Args:
            photo_data: Photo data dictionary
            caption: Caption for the post
            total_photos: Total number of photos in album
            dry_run: Whether to run in dry run mode

        Returns:
            Dictionary with workflow results
        """
        try:
            # Post the photo
            posting_result = self.poster.post_photo(photo_data, caption, dry_run)

            # Track progress
            progress_info = self.progress_tracker.log_progress(
                photo_data,
                total_photos,
                posted=posting_result.success
            )

            # Combine results
            workflow_result = {
                'posting_success': posting_result.success,
                'instagram_post_id': posting_result.instagram_post_id,
                'is_dry_run': posting_result.is_dry_run,
                'posting_message': posting_result.message,
                'progress_info': progress_info,
                'workflow_success': posting_result.success  # Overall success
            }

            return workflow_result

        except Exception as e:
            error_msg = f"Posting workflow failed: {e}"
            self.logger.error(error_msg)
            return {
                'posting_success': False,
                'instagram_post_id': None,
                'is_dry_run': dry_run,
                'posting_message': error_msg,
                'progress_info': {'error': error_msg},
                'workflow_success': False
            }


def create_instagram_poster(instagram_api: InstagramAPI) -> InstagramPoster:
    """Factory function to create InstagramPoster instance."""
    return InstagramPoster(instagram_api)


def create_progress_tracker() -> ProgressTracker:
    """Factory function to create ProgressTracker instance."""
    return ProgressTracker()


def create_posting_orchestrator(instagram_api: InstagramAPI) -> PostingOrchestrator:
    """Factory function to create PostingOrchestrator instance."""
    return PostingOrchestrator(instagram_api)