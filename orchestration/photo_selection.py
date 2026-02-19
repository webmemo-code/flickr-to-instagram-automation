"""
Photo selection orchestration module.

This module handles the logic for selecting the next photo to post from the Flickr album,
including validation and error handling.
"""

import logging
from typing import Dict, List, Optional, Tuple
from flickr_api import FlickrAPI
from state_manager import StateManager


class PhotoSelectionResult:
    """Result of photo selection operation."""

    def __init__(self, success: bool, photo: Optional[Dict] = None,
                 photos_total: int = 0, message: str = ""):
        self.success = success
        self.photo = photo
        self.photos_total = photos_total
        self.message = message
        self.is_album_complete = False


class PhotoSelector:
    """Handles photo selection logic and validation."""

    def __init__(self, flickr_api: FlickrAPI, state_manager: StateManager):
        self.flickr_api = flickr_api
        self.state_manager = state_manager
        self.logger = logging.getLogger(__name__)

    def get_next_photo_to_post(self, include_dry_runs: bool = True,
                             dry_run_mode: bool = False) -> PhotoSelectionResult:
        """
        Get the next photo to post from the album.

        Args:
            include_dry_runs: Whether to include dry run selections in photo selection
            dry_run_mode: Whether we're running in dry run mode

        Returns:
            PhotoSelectionResult with photo data and selection status
        """
        try:
            # Get lightweight photo list (single API call)
            photos = self.flickr_api.get_photo_list()
            if not photos:
                return PhotoSelectionResult(
                    success=False,
                    message="No photos found in the album"
                )

            self.logger.info(f"Retrieved {len(photos)} photos from album")

            # Check if album is complete (only count actual posts, not dry runs)
            if self.state_manager.is_album_complete(len(photos)):
                result = PhotoSelectionResult(
                    success=True,
                    photos_total=len(photos),
                    message="Album complete! All photos have been posted to Instagram."
                )
                result.is_album_complete = True
                return result

            # Get next photo to post (uses only id and album_position)
            next_photo = self.state_manager.get_next_photo_to_post(
                photos,
                include_dry_runs=include_dry_runs and dry_run_mode
            )

            if not next_photo:
                if dry_run_mode and include_dry_runs:
                    message = "All photos have been selected in dry runs! Use --reset-dry-runs to start over."
                else:
                    message = "Album complete! All photos have been posted to Instagram."

                result = PhotoSelectionResult(
                    success=True,
                    photos_total=len(photos),
                    message=message
                )
                result.is_album_complete = True
                return result

            # Fetch full metadata only for the selected photo (3 API calls instead of 3×N)
            self.flickr_api.enrich_photo(next_photo)

            position = next_photo.get('album_position', 'unknown')
            self.logger.info(f"📸 Selected photo #{position}: {next_photo['title']} (ID: {next_photo['id']})")

            return PhotoSelectionResult(
                success=True,
                photo=next_photo,
                photos_total=len(photos),
                message=f"Selected photo #{position}"
            )

        except Exception as e:
            self.logger.error(f"Error during photo selection: {e}")
            return PhotoSelectionResult(
                success=False,
                message=f"Photo selection failed: {e}"
            )


class PhotoValidator:
    """Handles photo validation logic."""

    def __init__(self, instagram_api):
        self.instagram_api = instagram_api
        self.logger = logging.getLogger(__name__)

    def validate_photo_for_posting(self, photo: Dict) -> Tuple[bool, str]:
        """
        Validate a photo for Instagram posting.

        Args:
            photo: Photo data dictionary

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Validate image URL (includes retry logic with 1-minute delay)
            self.logger.info(f"🔍 Validating image URL (includes retry if needed)...")

            if not self.instagram_api.validate_image_url(photo['url']):
                position = photo.get('album_position', 'unknown')
                error_msg = f"Invalid or inaccessible image URL after retries: {photo['url']}"
                self.logger.error(f"❌ {error_msg}")
                return False, error_msg

            self.logger.info("✅ Image URL validation passed")
            return True, ""

        except Exception as e:
            error_msg = f"Photo validation failed: {e}"
            self.logger.error(error_msg)
            return False, error_msg


def create_photo_selector(flickr_api: FlickrAPI, state_manager: StateManager) -> PhotoSelector:
    """Factory function to create PhotoSelector instance."""
    return PhotoSelector(flickr_api, state_manager)


def create_photo_validator(instagram_api) -> PhotoValidator:
    """Factory function to create PhotoValidator instance."""
    return PhotoValidator(instagram_api)