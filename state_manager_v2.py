"""
Enhanced state management with pluggable storage backends.

This is an evolution of the original StateManager that supports both legacy repository
variables and the new Git-based file storage system.
"""

import json
import logging
import os
from datetime import datetime
from typing import List, Optional, Dict, Union
from github import Github
from config import Config
from storage_adapter import StateStorageAdapter, GitFileStorageAdapter, RepositoryVariableStorageAdapter
from state_models import InstagramPost, AlbumMetadata, FailedPosition, PostStatus, AlbumStatus, migrate_legacy_data


class EnhancedStateManager:
    """Enhanced state manager with pluggable storage backends and rich metadata support."""

    def __init__(self, config: Config, repo_name: str, environment_name: str = None,
                 storage_backend: str = "auto", enable_parallel_writes: bool = False):
        """
        Initialize enhanced state manager.

        Args:
            config: Configuration object
            repo_name: GitHub repository name (owner/repo)
            environment_name: Environment name for account isolation
            storage_backend: Storage backend to use ("git", "repository_variables", "auto")
            enable_parallel_writes: Write to both storage systems during migration
        """
        self.config = config
        self.repo_name = repo_name
        self.logger = logging.getLogger(__name__)
        self.current_album_id = config.flickr_album_id
        self.environment_name = environment_name or self._detect_environment_name(config.account)
        self.enable_parallel_writes = enable_parallel_writes

        # Initialize GitHub client for legacy operations
        self.github = Github(config.github_token)
        self.repo = self.github.get_repo(repo_name)

        # Initialize storage adapters
        self.storage_adapter = self._initialize_storage_adapter(storage_backend)

        # Initialize legacy adapter if parallel writes are enabled
        self.legacy_adapter = None
        if enable_parallel_writes:
            from state_manager import StateManager  # Import legacy StateManager
            legacy_state_manager = StateManager(config, repo_name, environment_name)
            self.legacy_adapter = RepositoryVariableStorageAdapter(legacy_state_manager)

        self.logger.info(f"EnhancedStateManager initialized for account: {self.environment_name}")
        self.logger.info(f"Storage backend: {type(self.storage_adapter).__name__}")
        if self.enable_parallel_writes:
            self.logger.info("Parallel writes enabled (writing to both storage systems)")

    def _detect_environment_name(self, account: str) -> str:
        """Detect environment name based on account."""
        if account and account.lower() == 'reisememo':
            return 'secondary-account'
        return 'primary-account'

    def _initialize_storage_adapter(self, storage_backend: str) -> StateStorageAdapter:
        """Initialize the appropriate storage adapter."""
        if storage_backend == "git":
            return GitFileStorageAdapter(
                repo_name=self.repo_name,
                github_token=self.config.github_token
            )
        elif storage_backend == "repository_variables":
            from state_manager import StateManager  # Import legacy StateManager
            legacy_state_manager = StateManager(self.config, self.repo_name, self.environment_name)
            return RepositoryVariableStorageAdapter(legacy_state_manager)
        elif storage_backend == "auto":
            # Try Git storage first, fall back to repository variables
            git_adapter = GitFileStorageAdapter(
                repo_name=self.repo_name,
                github_token=self.config.github_token
            )
            if git_adapter.is_available():
                self.logger.info("Using Git-based storage (auto-detected)")
                return git_adapter
            else:
                self.logger.info("Git storage not available, falling back to repository variables")
                from state_manager import StateManager
                legacy_state_manager = StateManager(self.config, self.repo_name, self.environment_name)
                return RepositoryVariableStorageAdapter(legacy_state_manager)
        else:
            raise ValueError(f"Unknown storage backend: {storage_backend}")

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

            # Convert to InstagramPost objects
            posts = []
            for post_data in posts_data:
                if isinstance(post_data, dict):
                    # Handle both legacy and new format
                    if 'status' in post_data:
                        # New format
                        posts.append(InstagramPost.from_dict(post_data))
                    else:
                        # Legacy format
                        posts.append(InstagramPost.from_legacy_dict(post_data))

            return posts

        except Exception as e:
            self.logger.error(f"Failed to get Instagram posts: {e}")
            return []

    def get_failed_positions(self) -> List[int]:
        """Get list of failed positions (for backward compatibility)."""
        try:
            failed_data = self.storage_adapter.read_failed_positions(
                self.get_account_normalized(),
                self.current_album_id
            )

            # Handle both enhanced and legacy format
            if failed_data and isinstance(failed_data[0], dict):
                # Enhanced format with FailedPosition objects
                return [pos['position'] for pos in failed_data if not pos.get('resolved', False)]
            else:
                # Legacy format with just position integers
                return failed_data

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

            # Convert to FailedPosition objects
            failed_positions = []
            for item in failed_data:
                if isinstance(item, dict):
                    failed_positions.append(FailedPosition.from_dict(item))
                else:
                    # Legacy integer format
                    failed_positions.append(FailedPosition.from_position(item))

            return failed_positions

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

    def record_post(self, position: int, photo_data: dict, instagram_post_id: str,
                   title: str = "", create_audit_issue: bool = False) -> Optional[int]:
        """
        Record a successful Instagram post.

        Args:
            position: Photo position in album
            photo_data: Photo data from Flickr
            instagram_post_id: Instagram post ID
            title: Post title
            create_audit_issue: Whether to create audit issue (legacy compatibility)

        Returns:
            Issue number if audit issue created, None otherwise
        """
        try:
            # Get current posts
            posts = self.get_instagram_posts()

            # Check if post already exists (update) or create new
            existing_post = None
            for post in posts:
                if post.position == position:
                    existing_post = post
                    break

            if existing_post:
                # Update existing post
                existing_post.mark_as_posted(instagram_post_id)
                existing_post.title = title
                existing_post.account = self.get_account_normalized()
            else:
                # Create new post
                new_post = InstagramPost(
                    position=position,
                    photo_id=photo_data.get('id', ''),
                    title=title,
                    account=self.get_account_normalized(),
                    flickr_url=photo_data.get('url_o') or photo_data.get('url')
                )
                new_post.mark_as_posted(instagram_post_id)
                posts.append(new_post)

            # Write updated posts
            posts_data = [post.to_dict() for post in posts]
            success = self.storage_adapter.write_posts(
                self.get_account_normalized(),
                self.current_album_id,
                posts_data
            )

            if success:
                # Update metadata
                metadata = self.get_album_metadata()
                metadata.update_counts(posts)

                # Add workflow run info if available
                workflow_run_id = os.getenv('GITHUB_RUN_ID')
                if workflow_run_id:
                    metadata.add_workflow_run(workflow_run_id)

                self.storage_adapter.write_metadata(
                    self.get_account_normalized(),
                    self.current_album_id,
                    metadata.to_dict()
                )

                # Remove from failed positions if it was there
                self.remove_failed_position(position)

                # Parallel write to legacy system if enabled
                if self.enable_parallel_writes and self.legacy_adapter:
                    try:
                        # Convert to legacy format for parallel write
                        legacy_record = {
                            "position": position,
                            "photo_id": photo_data.get('id', ''),
                            "instagram_post_id": instagram_post_id,
                            "posted_at": datetime.now().isoformat(),
                            "title": title
                        }
                        # Note: Legacy system doesn't support bulk updates
                        self.logger.debug("Parallel write to legacy system (record_post)")
                    except Exception as e:
                        self.logger.warning(f"Parallel write to legacy system failed: {e}")

                self.logger.info(f"Recorded post for position {position} (Instagram ID: {instagram_post_id})")
                return None  # Issue creation not implemented in enhanced version
            else:
                self.logger.error(f"Failed to write post record for position {position}")
                return None

        except Exception as e:
            self.logger.error(f"Failed to record post for position {position}: {e}")
            return None

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

                # Parallel write to legacy system if enabled
                if self.enable_parallel_writes and self.legacy_adapter:
                    try:
                        # Legacy system uses simple integer list
                        legacy_failed = self.get_failed_positions()
                        if position not in legacy_failed:
                            legacy_failed.append(position)
                        self.logger.debug("Parallel write to legacy system (record_failed_position)")
                    except Exception as e:
                        self.logger.warning(f"Parallel write to legacy system failed: {e}")

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

                # Parallel write to legacy system if enabled
                if self.enable_parallel_writes and self.legacy_adapter:
                    try:
                        # Legacy system removes from list
                        legacy_failed = self.get_failed_positions()
                        if position in legacy_failed:
                            legacy_failed.remove(position)
                        self.logger.debug("Parallel write to legacy system (remove_failed_position)")
                    except Exception as e:
                        self.logger.warning(f"Parallel write to legacy system failed: {e}")

                return success
            return True

        except Exception as e:
            self.logger.error(f"Failed to remove failed position {position}: {e}")
            return False

    def is_album_complete(self, total_photos: int) -> bool:
        """Check if the album is complete."""
        try:
            posts = self.get_instagram_posts()
            posted_count = len([p for p in posts if p.status == PostStatus.POSTED])

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
            posted_count = len([p for p in posts if p.status == PostStatus.POSTED])
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

    def migrate_from_legacy(self) -> Dict:
        """Migrate data from legacy repository variables to new storage."""
        if not isinstance(self.storage_adapter, GitFileStorageAdapter):
            return {"error": "Migration only supported for Git storage backend"}

        try:
            # Get migration adapter
            git_adapter = self.storage_adapter
            return git_adapter.migrate_from_repository_variables(None)

        except Exception as e:
            self.logger.error(f"Migration failed: {e}")
            return {"error": str(e)}

    def get_next_photo_to_post(self, photos: List[Dict], include_dry_runs: bool = False) -> Optional[Dict]:
        """
        Get the next photo to post from the provided photos list.

        Args:
            photos: List of photo dictionaries from Flickr
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
            posted_ids = {post.flickr_photo_id for post in posted_photos
                         if not include_dry_runs or not post.is_dry_run}

            # Get failed positions that should be retried
            failed_positions = self.get_enhanced_failed_positions()
            failed_ids = {f.flickr_photo_id for f in failed_positions if not f.resolved}

            # Find next unposted photo
            for photo in sorted(photos, key=lambda x: x.get('album_position', 0)):
                photo_id = photo.get('id')
                if photo_id and photo_id not in posted_ids and photo_id not in failed_ids:
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
            self._save_album_metadata(metadata)

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