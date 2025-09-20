"""
State management orchestration module.

This module handles state recording, logging, and notification workflows.
"""

import logging
from typing import Dict, Optional
from state_manager import StateManager
from email_notifier import EmailNotifier


class StateResult:
    """Result of state management operation."""

    def __init__(self, success: bool, message: str = "", critical_failure: bool = False):
        self.success = success
        self.message = message
        self.critical_failure = critical_failure


class StateOrchestrator:
    """Orchestrates state management operations."""

    def __init__(self, state_manager: StateManager, email_notifier: EmailNotifier):
        self.state_manager = state_manager
        self.email_notifier = email_notifier
        self.logger = logging.getLogger(__name__)

    def record_post_outcome(self, photo_data: Dict, instagram_post_id: Optional[str],
                           is_dry_run: bool = False, create_audit_issue: bool = False) -> StateResult:
        """
        Record the outcome of a posting attempt.

        Args:
            photo_data: Photo data dictionary
            instagram_post_id: Instagram post ID if successful, None if failed
            is_dry_run: Whether this was a dry run
            create_audit_issue: Whether to create audit issues

        Returns:
            StateResult with operation status
        """
        try:
            position = photo_data.get('album_position', 'unknown')

            if instagram_post_id:
                # Successful post
                self.state_manager.create_post_record(
                    photo_data,
                    instagram_post_id,
                    is_dry_run=is_dry_run,
                    create_audit_issue=create_audit_issue
                )
                message = f"Successfully recorded post for photo #{position}"
                self.logger.info(message)
                return StateResult(success=True, message=message)

            elif is_dry_run:
                # Dry run
                self.state_manager.create_post_record(
                    photo_data,
                    None,
                    is_dry_run=True
                )
                message = f"Recorded dry run for photo #{position}"
                self.logger.info(message)
                return StateResult(success=True, message=message)

            else:
                # Failed post
                success = self.state_manager.create_post_record(photo_data, None)

                if not success:
                    # Critical failure - can't even record the failure
                    error_msg = f"Critical error: Cannot record failed post for photo #{position}"
                    self.logger.error(f"💥 {error_msg}")
                    return StateResult(
                        success=False,
                        message=error_msg,
                        critical_failure=True
                    )

                # Photo failed but state management succeeded
                message = f"Recorded failed post for photo #{position}"
                self.logger.warning(f"⚠️ {message}")
                return StateResult(success=True, message=message)

        except Exception as e:
            error_msg = f"State recording failed: {e}"
            self.logger.error(error_msg)
            return StateResult(
                success=False,
                message=error_msg,
                critical_failure=True
            )

    def log_automation_run(self, success: bool, message: str, account_display: str,
                          album_name: str, album_url: str) -> StateResult:
        """
        Log the automation run outcome.

        Args:
            success: Whether the automation run was successful
            message: Descriptive message about the outcome
            account_display: Display name for the account
            album_name: Album name
            album_url: Album URL

        Returns:
            StateResult with logging status
        """
        try:
            self.state_manager.log_automation_run(
                success,
                message,
                account_display,
                album_name,
                album_url
            )

            log_message = f"Logged automation run: {message}"
            self.logger.info(log_message)
            return StateResult(success=True, message=log_message)

        except Exception as e:
            error_msg = f"Automation run logging failed: {e}"
            self.logger.error(error_msg)
            return StateResult(success=False, message=error_msg)

    def handle_album_completion(self, total_photos: int, album_name: str) -> StateResult:
        """
        Handle album completion notifications and logging.

        Args:
            total_photos: Total number of photos in the album
            album_name: Name of the completed album

        Returns:
            StateResult with completion handling status
        """
        try:
            self.logger.info("🎉 Album complete! All photos have been posted to Instagram.")

            # Send completion notification email
            try:
                self.email_notifier.send_completion_notification(total_photos, album_name)
                notification_message = "Completion notification email sent"
                self.logger.info(notification_message)
            except Exception as email_error:
                notification_message = f"Email notification failed: {email_error}"
                self.logger.warning(f"⚠️ {notification_message}")

            return StateResult(
                success=True,
                message=f"Album completion handled. {notification_message}"
            )

        except Exception as e:
            error_msg = f"Album completion handling failed: {e}"
            self.logger.error(error_msg)
            return StateResult(success=False, message=error_msg)


class ValidationStateHandler:
    """Handles state operations for photo validation failures."""

    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager
        self.logger = logging.getLogger(__name__)

    def handle_validation_failure(self, photo_data: Dict, error_message: str,
                                 is_dry_run: bool = False) -> StateResult:
        """
        Handle state recording for photo validation failures.

        Args:
            photo_data: Photo data dictionary
            error_message: Validation error message
            is_dry_run: Whether this was a dry run

        Returns:
            StateResult with handling status
        """
        try:
            position = photo_data.get('album_position', 'unknown')

            # Record the validation failure
            self.state_manager.create_post_record(photo_data, None, is_dry_run=is_dry_run)

            message = f"Recorded validation failure for photo #{position}: {error_message}"
            self.logger.info(f"⏭️ Skipping photo #{position} and marking as failed to continue with next photo")

            return StateResult(success=True, message=message)

        except Exception as e:
            error_msg = f"Validation failure handling failed: {e}"
            self.logger.error(error_msg)
            return StateResult(success=False, message=error_msg)


def create_state_orchestrator(state_manager: StateManager, email_notifier: EmailNotifier) -> StateOrchestrator:
    """Factory function to create StateOrchestrator instance."""
    return StateOrchestrator(state_manager, email_notifier)


def create_validation_state_handler(state_manager: StateManager) -> ValidationStateHandler:
    """Factory function to create ValidationStateHandler instance."""
    return ValidationStateHandler(state_manager)