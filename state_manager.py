"""
Modern state management using Git-based file storage.

Provides scalable, reliable state management using Git files with fail-safe error handling.
"""

import json
import logging
import os
from datetime import datetime
from typing import List, Optional, Dict, Union
from github import Github
from config import Config
from storage_adapter import GitFileStorageAdapter
from state_models import InstagramPost, AlbumMetadata, FailedPosition, PostStatus, AlbumStatus
from photo_models import PhotoListItem, EnrichedPhoto
from notification_system import notifier, CriticalStateFailure
from account_config import account_manager


class StateManager:
    """Modern state manager using Git-based file storage with rich metadata support and fail-safe error handling."""

    def __init__(self, config: Config, repo_name: str, environment_name: str = None):
        """
        Initialize Git-based state manager.

        Args:
            config: Configuration object
            repo_name: GitHub repository name (owner/repo)
            environment_name: Environment name for account isolation
        """
        self.config = config
        self.repo_name = repo_name
        self.logger = logging.getLogger(__name__)
        self.current_album_id = config.flickr_album_id
        self.environment_name = environment_name or self._detect_environment_name(config.account)

        # Initialize GitHub client for Git operations
        self.github = Github(config.github_token)
        self.repo = self.github.get_repo(repo_name)

        # Initialize Git-based storage adapter
        self.storage_adapter = GitFileStorageAdapter(
            repo_name=self.repo_name,
            github_token=self.config.github_token
        )

        self.logger.info(f"StateManager initialized for account: {self.environment_name}")
        self.logger.info("Using Git-based file storage")

    def _detect_environment_name(self, account: str) -> str:
        """Detect environment name based on account configuration."""
        return account_manager.get_environment_name(account)


    def get_account_normalized(self) -> str:
        """Get normalized account name for storage."""
        if self.environment_name == 'secondary-account':
            return 'secondary'
        return 'primary'

    def get_instagram_posts(self) -> List[InstagramPost]:
        """Get all Instagram post records for the current album."""
        try:
            posts_data = self.storage_adapter.read_posts(
                self.get_account_normalized(),
                self.current_album_id
            )

            posts: List[InstagramPost] = []
            for post_data in posts_data:
                try:
                    posts.append(InstagramPost.from_dict(post_data))
                except Exception as conversion_error:
                    self.logger.error(
                        f"Failed to load stored post record: {conversion_error} | data={post_data}"
                    )

            return posts

        except Exception as e:
            if "403" in str(e) or "permission" in str(e).lower() or "forbidden" in str(e).lower():
                error_msg = f"CRITICAL: Cannot access Instagram posts data - STOPPING to prevent wrong photo posting: {e}"
                self.logger.critical(error_msg)
                notifier.send_critical_failure_alert(
                    "STATE_ACCESS_DENIED",
                    error_msg,
                    {"method": "get_instagram_posts", "exception": str(e), "album_id": self.current_album_id}
                )
                raise CriticalStateFailure(error_msg) from e

            self.logger.error(f"Failed to get Instagram posts: {e}")
            return []

    def get_failed_positions(self) -> List[int]:
        """Get list of failed positions that still require attention."""
        try:
            failed_data = self.storage_adapter.read_failed_positions(
                self.get_account_normalized(),
                self.current_album_id
            )

            return [
                pos['position']
                for pos in failed_data
                if isinstance(pos, dict) and not pos.get('resolved', False)
            ]

        except Exception as e:
            self.logger.error(f"Failed to get failed positions: {e}")
            return []

    def get_enhanced_failed_positions(self) -> List[FailedPosition]:
        """Get enhanced failed position records."""
        try:
            failed_data = self.storage_adapter.read_failed_positions(
                self.get_account_normalized(),
                self.current_album_id
            )

            return [FailedPosition.from_dict(item) for item in failed_data]

        except Exception as e:
            self.logger.error(f"Failed to get enhanced failed positions: {e}")
            return []

    def get_album_metadata(self) -> AlbumMetadata:
        """Get album metadata."""
        try:
            metadata_data = self.storage_adapter.read_metadata(
                self.get_account_normalized(),
                self.current_album_id
            )

            if metadata_data and 'album_id' in metadata_data:
                return AlbumMetadata.from_dict(metadata_data)
            else:
                # Create new metadata
                return AlbumMetadata.create_new(
                    self.current_album_id,
                    self.get_account_normalized()
                )

        except Exception as e:
            self.logger.error(f"Failed to get album metadata: {e}")
            return AlbumMetadata.create_new(
                self.current_album_id,
                self.get_account_normalized()
            )

    def clear_dry_run_records(self) -> int:
        """Clear dry-run post records from Git-based storage."""
        try:
            posts = self.get_instagram_posts()
            if not posts:
                self.logger.info("No post records found; nothing to clear")
                return 0

            remaining_posts = [
                post for post in posts if not post.is_dry_run
            ]
            cleared_count = len(posts) - len(remaining_posts)

            if cleared_count == 0:
                self.logger.info("No dry run records to clear")
                return 0

            if not self.storage_adapter.write_posts(
                self.get_account_normalized(),
                self.current_album_id,
                [post.to_dict() for post in remaining_posts]
            ):
                self.logger.error("Failed to persist updated post records after clearing dry runs")
                return 0

            metadata = self.get_album_metadata()
            metadata.update_counts(remaining_posts)
            self.storage_adapter.write_metadata(
                self.get_account_normalized(),
                self.current_album_id,
                metadata.to_dict()
            )

            self.logger.info(f"Cleared {cleared_count} dry run records")
            return cleared_count

        except Exception as e:
            self.logger.error(f"Failed to clear dry run records: {e}")
            return 0


    def record_failed_position(self, position: int, photo_id: str = None,
                             error_message: str = None) -> bool:
        """Record a failed posting position."""
        try:
            # Get current failed positions
            failed_positions = self.get_enhanced_failed_positions()

            # Check if position already exists
            existing_failed = None
            for failed in failed_positions:
                if failed.position == position and not failed.resolved:
                    existing_failed = failed
                    break

            if existing_failed:
                # Update retry count
                existing_failed.retry_count += 1
                existing_failed.error_message = error_message
                existing_failed.workflow_run_id = os.getenv('GITHUB_RUN_ID')
            else:
                # Create new failed position record
                new_failed = FailedPosition.from_position(
                    position=position,
                    photo_id=photo_id,
                    error_message=error_message,
                    workflow_run_id=os.getenv('GITHUB_RUN_ID')
                )
                failed_positions.append(new_failed)

            # Write updated failed positions
            failed_data = [failed.to_dict() for failed in failed_positions]
            success = self.storage_adapter.write_failed_positions(
                self.get_account_normalized(),
                self.current_album_id,
                failed_data
            )

            if success:
                # Update metadata
                metadata = self.get_album_metadata()
                metadata.add_error(error_message or f"Failed to post position {position}")
                self.storage_adapter.write_metadata(
                    self.get_account_normalized(),
                    self.current_album_id,
                    metadata.to_dict()
                )


                self.logger.info(f"Recorded failed position {position}")
                return True
            else:
                self.logger.error(f"Failed to write failed position record for {position}")
                return False

        except Exception as e:
            self.logger.error(f"Failed to record failed position {position}: {e}")
            return False

    def remove_failed_position(self, position: int) -> bool:
        """Remove a position from failed positions list."""
        try:
            failed_positions = self.get_enhanced_failed_positions()

            # Mark as resolved instead of removing (for audit trail)
            updated = False
            for failed in failed_positions:
                if failed.position == position and not failed.resolved:
                    failed.mark_resolved()
                    updated = True

            if updated:
                # Write updated failed positions
                failed_data = [failed.to_dict() for failed in failed_positions]
                success = self.storage_adapter.write_failed_positions(
                    self.get_account_normalized(),
                    self.current_album_id,
                    failed_data
                )


                return success
            return True

        except Exception as e:
            self.logger.error(f"Failed to remove failed position {position}: {e}")
            return False

    def is_album_complete(self, total_photos: int) -> bool:
        """Check if the album is complete."""
        try:
            posts = self.get_instagram_posts()
            posted_count = InstagramPost.count_real_posted(posts)

            # Update metadata with current photo count
            metadata = self.get_album_metadata()
            metadata.total_photos = total_photos
            metadata.update_counts(posts)
            self.storage_adapter.write_metadata(
                self.get_account_normalized(),
                self.current_album_id,
                metadata.to_dict()
            )

            is_complete = posted_count >= total_photos
            self.logger.debug(f"Album completion check: {posted_count}/{total_photos} = {is_complete}")
            return is_complete

        except Exception as e:
            self.logger.error(f"Failed to check album completion: {e}")
            return False

    def get_statistics(self) -> Dict:
        """Get comprehensive statistics about the current album."""
        try:
            posts = self.get_instagram_posts()
            failed_positions = self.get_enhanced_failed_positions()
            metadata = self.get_album_metadata()

            # Calculate statistics
            total_posts = len(posts)
            posted_count = InstagramPost.count_real_posted(posts)
            failed_count = len([f for f in failed_positions if not f.resolved])
            pending_count = len([p for p in posts if p.status == PostStatus.PENDING])

            return {
                "album_id": self.current_album_id,
                "account": self.get_account_normalized(),
                "total_photos": metadata.total_photos,
                "total_posts": total_posts,
                "posted_count": posted_count,
                "failed_count": failed_count,
                "pending_count": pending_count,
                "completion_percentage": metadata.completion_percentage,
                "completion_status": metadata.completion_status.value,
                "last_posted_at": metadata.last_posted_at,
                "last_update": metadata.last_update,
                "workflow_runs_count": metadata.workflow_runs_count,
                "error_count": metadata.error_count,
                "storage_backend": type(self.storage_adapter).__name__
            }

        except Exception as e:
            self.logger.error(f"Failed to get statistics: {e}")
            return {
                "error": str(e),
                "storage_backend": type(self.storage_adapter).__name__
            }


    def get_next_photo_to_post(self, photos: List[PhotoListItem], include_dry_runs: bool = False) -> Optional[PhotoListItem]:
        """
        Get the next photo to post from the provided photos list.

        Args:
            photos: List of PhotoListItem objects from Flickr
            include_dry_runs: Whether to consider dry run photos as posted

        Returns:
            Next photo to post or None if all are posted
        """
        try:
            if not photos:
                self.logger.warning("No photos provided to get_next_photo_to_post")
                return None

            # Get posted photos
            posted_photos = self.get_instagram_posts()
            if include_dry_runs:
                real_posted = [p for p in posted_photos if p.status == PostStatus.POSTED]
            else:
                real_posted = InstagramPost.get_real_posted(posted_photos)
            posted_ids = {p.photo_id for p in real_posted if p.photo_id}

            # Get failed positions that should be retried
            failed_positions = self.get_enhanced_failed_positions()
            failed_ids = {f.photo_id for f in failed_positions if not f.resolved and f.photo_id}

            # Find next unposted photo
            for photo in sorted(photos, key=lambda x: x.album_position):
                if photo.id not in posted_ids and photo.id not in failed_ids:
                    return photo

            return None

        except Exception as e:
            self.logger.error(f"Error in get_next_photo_to_post: {e}")
            return None

    def log_automation_run(self, success: bool, details: str = "", account_name: str = "",
                          album_name: str = "", album_url: str = "") -> None:
        """
        Log an automation run result.

        Args:
            success: Whether the automation run was successful
            details: Additional details about the run
            account_name: Name of the account
            album_name: Name of the album
            album_url: URL of the album
        """
        try:
            # Update album metadata with run information
            metadata = self.get_album_metadata()
            metadata.workflow_runs_count += 1
            metadata.last_update = datetime.now().isoformat()

            if not success:
                metadata.error_count += 1

            # Save updated metadata
            # Save album metadata
            self.storage_adapter.write_metadata(
                self.get_account_normalized(),
                self.current_album_id,
                metadata.to_dict()
            )

            # Log the run
            status = "SUCCESS" if success else "FAILED"
            self.logger.info(f"Automation run {status}: {details}")
            if account_name:
                self.logger.info(f"Account: {account_name}")
            if album_name:
                self.logger.info(f"Album: {album_name}")
            if album_url:
                self.logger.info(f"Album URL: {album_url}")

        except Exception as e:
            self.logger.error(f"Failed to log automation run: {e}")

    def create_post_record(self, photo_data, instagram_post_id: Optional[str] = None,
                          is_dry_run: bool = False, create_audit_issue: bool = False) -> Optional[str]:
        """Record a post (successful, failed, or dry run).

        Args:
            photo_data: PhotoListItem or EnrichedPhoto from Flickr
            instagram_post_id: Instagram post ID if successful, None if failed
            is_dry_run: Whether this was a dry run
            create_audit_issue: Whether to create audit issues (unused, kept for API compat)

        Returns:
            Post record ID or None if failed
        """
        try:
            album_position = photo_data.album_position
            flickr_photo_id = photo_data.id
            title = photo_data.title
            flickr_url = photo_data.url

            if is_dry_run:
                self.logger.info(f"DRY RUN: Would post photo #{album_position} - {title}")

            # Build the post record
            if instagram_post_id:
                status = PostStatus.POSTED
                self.logger.info(f"Recording successful post for photo #{album_position}")
            elif is_dry_run:
                status = PostStatus.POSTED
            else:
                status = PostStatus.FAILED
                self.logger.warning(f"Recording failed post for photo #{album_position}")

            post = InstagramPost(
                position=album_position,
                photo_id=flickr_photo_id,
                title=title,
                status=status,
                account=self.get_account_normalized(),
                flickr_url=flickr_url,
                is_dry_run=is_dry_run,
                workflow_run_id=os.getenv('GITHUB_RUN_ID'),
                instagram_url=f"https://www.instagram.com/p/{instagram_post_id}/" if instagram_post_id else None,
            )
            if instagram_post_id:
                post.mark_as_posted(instagram_post_id)

            # Upsert into posts list
            posts = self.get_instagram_posts()
            existing_idx = next(
                (i for i, p in enumerate(posts) if p.position == album_position), None
            )
            if existing_idx is not None:
                posts[existing_idx] = post
            else:
                posts.append(post)

            # Persist
            if not self.storage_adapter.write_posts(
                self.get_account_normalized(), self.current_album_id,
                [p.to_dict() for p in posts]
            ):
                self.logger.error(f"Failed to write post record for photo #{album_position}")
                return None

            # Update metadata
            metadata = self.get_album_metadata()
            metadata.update_counts(posts)
            metadata.last_update = datetime.now().isoformat()
            if instagram_post_id:
                metadata.last_posted_at = datetime.now().isoformat()
            workflow_run_id = os.getenv('GITHUB_RUN_ID')
            if workflow_run_id:
                metadata.add_workflow_run(workflow_run_id)
            self.storage_adapter.write_metadata(
                self.get_account_normalized(), self.current_album_id, metadata.to_dict()
            )

            # Clear from failed positions on success
            if instagram_post_id:
                self.remove_failed_position(album_position)

            return "dry_run" if is_dry_run else flickr_photo_id

        except Exception as e:
            self.logger.error(f"Failed to create post record: {e}")
            return None
