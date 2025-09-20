"""
Caption generation orchestration module.

This module handles the caption generation workflow, including AI generation,
fallback handling, and caption building.
"""

import logging
from typing import Dict, Optional, Tuple
from caption_generator import CaptionGenerator


class CaptionResult:
    """Result of caption generation operation."""

    def __init__(self, success: bool, caption: str = "", generated_text: str = "",
                 used_fallback: bool = False, message: str = ""):
        self.success = success
        self.caption = caption
        self.generated_text = generated_text
        self.used_fallback = used_fallback
        self.message = message


class CaptionOrchestrator:
    """Orchestrates the caption generation process."""

    def __init__(self, caption_generator: CaptionGenerator):
        self.caption_generator = caption_generator
        self.logger = logging.getLogger(__name__)

    def generate_full_caption(self, photo_data: Dict) -> CaptionResult:
        """
        Generate a complete Instagram caption for the given photo.

        Args:
            photo_data: Photo data dictionary from Flickr

        Returns:
            CaptionResult with the generated caption and metadata
        """
        try:
            # Generate caption with GPT-4 Vision
            self.logger.info("🤖 Generating enhanced caption with GPT-4 Vision...")
            generated_caption = self.caption_generator.generate_with_retry(photo_data)

            used_fallback = False
            if not generated_caption:
                self.logger.warning("⚠️ Failed to generate caption, using fallback")
                generated_caption = "Beautiful moment captured during our travels."
                used_fallback = True

            # Build full caption
            full_caption = self.caption_generator.build_full_caption(photo_data, generated_caption)

            self.logger.info(f"📝 Generated caption: {full_caption[:100]}...")

            return CaptionResult(
                success=True,
                caption=full_caption,
                generated_text=generated_caption,
                used_fallback=used_fallback,
                message="Caption generated successfully"
            )

        except Exception as e:
            error_msg = f"Caption generation failed: {e}"
            self.logger.error(error_msg)

            # Try to create a basic fallback caption
            try:
                fallback_caption = self.caption_generator.build_full_caption(
                    photo_data,
                    "Beautiful moment captured during our travels."
                )

                return CaptionResult(
                    success=True,
                    caption=fallback_caption,
                    generated_text="Beautiful moment captured during our travels.",
                    used_fallback=True,
                    message=f"Used fallback due to error: {error_msg}"
                )

            except Exception as fallback_error:
                self.logger.error(f"Even fallback caption generation failed: {fallback_error}")
                return CaptionResult(
                    success=False,
                    message=f"Complete caption generation failure: {e}, fallback also failed: {fallback_error}"
                )

    def validate_caption(self, caption: str) -> Tuple[bool, str]:
        """
        Validate a generated caption for Instagram posting.

        Args:
            caption: The caption text to validate

        Returns:
            Tuple of (is_valid, validation_message)
        """
        try:
            # Basic validation rules
            if not caption or not caption.strip():
                return False, "Caption is empty"

            # Instagram has a 2200 character limit
            if len(caption) > 2200:
                return False, f"Caption too long: {len(caption)} characters (max 2200)"

            # Check for basic structure
            if len(caption.strip()) < 10:
                return False, "Caption too short (less than 10 characters)"

            self.logger.debug(f"Caption validation passed: {len(caption)} characters")
            return True, "Caption validation passed"

        except Exception as e:
            error_msg = f"Caption validation error: {e}"
            self.logger.error(error_msg)
            return False, error_msg


class CaptionPreprocessor:
    """Handles caption preprocessing and enhancement."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def preprocess_photo_data(self, photo_data: Dict) -> Dict:
        """
        Preprocess photo data to enhance caption generation context.

        Args:
            photo_data: Raw photo data from Flickr

        Returns:
            Enhanced photo data dictionary
        """
        try:
            enhanced_data = photo_data.copy()

            # Ensure title is available
            if not enhanced_data.get('title'):
                enhanced_data['title'] = f"Photo {enhanced_data.get('id', 'unknown')}"

            # Clean and enhance description
            description = enhanced_data.get('description', '')
            if description:
                # Basic cleanup of description
                description = description.strip()
                if len(description) > 500:  # Truncate very long descriptions
                    description = description[:497] + "..."
                enhanced_data['description'] = description

            # Ensure position is available
            if 'album_position' not in enhanced_data:
                enhanced_data['album_position'] = 'unknown'

            # Add URL validation flag
            enhanced_data['url_validated'] = False

            self.logger.debug(f"Preprocessed photo data for {enhanced_data.get('id')}")
            return enhanced_data

        except Exception as e:
            self.logger.error(f"Photo data preprocessing failed: {e}")
            return photo_data  # Return original data if preprocessing fails


def create_caption_orchestrator(caption_generator: CaptionGenerator) -> CaptionOrchestrator:
    """Factory function to create CaptionOrchestrator instance."""
    return CaptionOrchestrator(caption_generator)


def create_caption_preprocessor() -> CaptionPreprocessor:
    """Factory function to create CaptionPreprocessor instance."""
    return CaptionPreprocessor()