"""
Modern state management using Git-based file storage.

Provides scalable, reliable state management using Git files with fail-safe error handling.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Union
from config import Config
from storage_adapter import GitFileStorageAdapter, StateStorageError
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

        # Initialize Git-based storage adapter. All GitHub access goes through
        # this adapter — StateManager holds no GitHub client of its own.
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

    def _fail_loud(self, method: str, error: Exception) -> 'CriticalStateFailure':
        """Alert and build a CriticalStateFailure for a failed state read.

        Any storage read that fails for a non-absent reason must stop the run
        rather than return empty — an empty posted list would silently restart
        a half-posted album from photo 1. The storage adapter already
        distinguishes 'absent' (StateFileNotFound, handled as empty inside the
        adapter) from failures (StateStorageError), so anything reaching here
        is a genuine failure.
        """
        error_msg = (
            f"CRITICAL: Cannot access state data via {method} for album "
            f"{self.current_album_id} - STOPPING to prevent wrong photo posting: {error}"
        )
        self.logger.critical(error_msg)
        notifier.send_critical_failure_alert(
            "STATE_ACCESS_FAILURE",
            error_msg,
            {"method": method, "exception": str(error), "album_id": self.current_album_id},
        )
        return CriticalStateFailure(error_msg)

    def get_instagram_posts(self) -> List[InstagramPost]:
        """Get all Instagram post records for the current album.

        Raises CriticalStateFailure if the read fails — never returns [] on a
        failed read (which would silently restart the album from photo 1).
        An absent posts file (first run) returns [] normally.
        """
        try:
            posts_data = self.storage_adapter.read_posts(
                self.get_account_normalized(),
                self.current_album_id
            )
        except StateStorageError as e:
            raise self._fail_loud("get_instagram_posts", e) from e

        posts: List[InstagramPost] = []
        for post_data in posts_data:
            try:
                posts.append(InstagramPost.from_dict(post_data))
            except Exception as conversion_error:
                # A single malformed record is logged and skipped (kept
                # behavior); it is not an access failure.
                self.logger.error(
                    f"Failed to load stored post record: {conversion_error} | data={post_data}"
                )

        return posts

    def get_failed_positions(self) -> List[int]:
        """Get list of failed positions that still require attention.

        Raises CriticalStateFailure on a failed read; absent file returns [].
        """
        try:
            failed_data = self.storage_adapter.read_failed_positions(
                self.get_account_normalized(),
                self.current_album_id
            )
        except StateStorageError as e:
            raise self._fail_loud("get_failed_positions", e) from e

        return [
            pos['position']
            for pos in failed_data
            if isinstance(pos, dict) and not pos.get('resolved', False)
        ]

    def get_enhanced_failed_positions(self) -> List[FailedPosition]:
        """Get enhanced failed position records.

        Raises CriticalStateFailure on a failed read; absent file returns [].
        """
        try:
            failed_data = self.storage_adapter.read_failed_positions(
                self.get_account_normalized(),
                self.current_album_id
            )
        except StateStorageError as e:
            raise self._fail_loud("get_enhanced_failed_positions", e) from e

        return [FailedPosition.from_dict(item) for item in failed_data]

    def get_album_metadata(self) -> AlbumMetadata:
        """Get album metadata.

        Raises CriticalStateFailure on a failed read. An absent metadata file
        (first run) yields fresh metadata, not an error.
        """
        try:
            metadata_data = self.storage_adapter.read_metadata(
                self.get_account_normalized(),
                self.current_album_id
            )
        except StateStorageError as e:
            raise self._fail_loud("get_album_metadata", e) from e

        if metadata_data and 'album_id' in metadata_data:
            return AlbumMetadata.from_dict(metadata_data)
        # Absent file → adapter returned its default dict → create fresh
        return AlbumMetadata.create_new(
            self.current_album_id,
            self.get_account_normalized()
        )

    def clear_dry_run_records(self) -> int:
        """Clear dry-run post records from Git-based storage.

        Raises CriticalStateFailure if reading current state fails.
        """
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

            self.storage_adapter.write_posts(
                self.get_account_normalized(),
                self.current_album_id,
                [post.to_dict() for post in remaining_posts]
            )

            metadata = self.get_album_metadata()
            metadata.update_counts(remaining_posts)
            self.storage_adapter.write_metadata(
                self.get_account_normalized(),
                self.current_album_id,
                metadata.to_dict()
            )

            self.logger.info(f"Cleared {cleared_count} dry run records")
            return cleared_count

        except CriticalStateFailure:
            raise
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
            self.storage_adapter.write_failed_positions(
                self.get_account_normalized(),
                self.current_album_id,
                failed_data
            )

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

        except CriticalStateFailure:
            raise
        except Exception as e:
            self.logger.error(f"Failed to record failed position {position}: {e}")
            return False

    def remove_failed_position(self, position: int) -> bool:
        """Remove a position from failed positions list.

        Raises CriticalStateFailure if reading current state fails.
        """
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
                self.storage_adapter.write_failed_positions(
                    self.get_account_normalized(),
                    self.current_album_id,
                    failed_data
                )
            return True

        except CriticalStateFailure:
            raise
        except Exception as e:
            self.logger.error(f"Failed to remove failed position {position}: {e}")
            return False

    def is_album_complete(self, total_photos: int) -> bool:
        """Check if the album is complete.

        Read-only: performs NO storage writes (metadata is persisted only as
        part of a posting/failure/reset operation). A failed state read raises
        CriticalStateFailure via get_instagram_posts rather than returning a
        misleading False.
        """
        posts = self.get_instagram_posts()
        posted_count = InstagramPost.count_real_posted(posts)

        is_complete = posted_count >= total_photos
        self.logger.debug(f"Album completion check: {posted_count}/{total_photos} = {is_complete}")
        return is_complete

    def get_statistics(self) -> Dict:
        """Get comprehensive statistics about the current album.

        Read-only. A failed state read raises CriticalStateFailure (via the
        getters) rather than being masked as an error-dict result.
        """
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


    def get_next_photo_to_post(self, photos: List[PhotoListItem], include_dry_runs: bool = False) -> Optional[PhotoListItem]:
        """
        Get the next photo to post from the provided photos list.

        Args:
            photos: List of PhotoListItem objects from Flickr
            include_dry_runs: Whether to consider dry run photos as posted

        Returns:
            Next photo to post or None if all are posted

        Raises:
            CriticalStateFailure: if reading posted/failed state fails. This
            must propagate — swallowing it and returning photo 1 is exactly
            the silent album-restart this refactor exists to prevent.
        """
        if not photos:
            self.logger.warning("No photos provided to get_next_photo_to_post")
            return None

        # Get posted photos — a failed read raises CriticalStateFailure here
        # rather than yielding an empty list (which would select photo 1).
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

        except CriticalStateFailure:
            raise
        except Exception as e:
            self.logger.error(f"Failed to log automation run: {e}")

    def create_post_record(self, photo_data, instagram_post_id: Optional[str] = None,
                          is_dry_run: bool = False, create_audit_issue: bool = False,
                          facebook_post_id: Optional[str] = None,
                          generated_body: Optional[str] = None) -> Optional[str]:
        """Record a post (successful, failed, or dry run).

        Args:
            photo_data: PhotoListItem or EnrichedPhoto from Flickr
            instagram_post_id: Instagram post ID if successful, None if failed
            is_dry_run: Whether this was a dry run
            create_audit_issue: Whether to create audit issues (unused, kept for API compat)
            facebook_post_id: Facebook Page post ID if cross-posted, None otherwise
            generated_body: AI-generated caption body (without title/signature/hashtags),
                            persisted so a delayed Threads cross-post can reuse it.

        Returns:
            Post record ID, or None if the authoritative posts file could not
            be written. A metadata-only write failure still returns success
            (the post is durably recorded; derived stats self-heal next run).

        Raises:
            CriticalStateFailure: if reading current state fails (must halt the
                run rather than post without a durable record).
        """
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
            facebook_post_id=facebook_post_id,
            generated_body=generated_body,
        )
        if instagram_post_id:
            post.mark_as_posted(instagram_post_id)

        # Upsert into posts list (a failed read here raises CriticalStateFailure)
        posts = self.get_instagram_posts()
        existing_idx = next(
            (i for i, p in enumerate(posts) if p.position == album_position), None
        )
        if existing_idx is not None:
            posts[existing_idx] = post
        else:
            posts.append(post)

        # Persist. Write ORDER is a compatibility contract: the posts file is
        # written FIRST — this is the effective commit point a concurrently
        # scheduled delayed-Threads run keys off, so it never observes a post
        # without its threads-due record. Do not reorder posts vs failed writes.
        # A write failure now raises StateStorageError; catch it to preserve the
        # historical "return None on write failure" contract that main.py reads.
        try:
            self.storage_adapter.write_posts(
                self.get_account_normalized(), self.current_album_id,
                [p.to_dict() for p in posts]
            )
        except StateStorageError as e:
            self.logger.error(f"Failed to write post record for photo #{album_position}: {e}")
            return None

        # Update metadata (write #2). Batched into this posting cycle so a
        # successful post is at most 2 writes (posts + metadata).
        #
        # The posts file (written above) is the source of truth and is already
        # durable at this point. metadata.json holds only derived stats, which
        # self-heal on the next run's update_counts. So a metadata WRITE failure
        # must NOT return None — that would tell main.py the post failed and
        # trigger a spurious re-post / failed-position record for a photo that
        # was in fact posted and recorded. Log it and still report success.
        # (A metadata READ failure below is a different matter — it raises
        # CriticalStateFailure via get_album_metadata and halts the run, which
        # is correct: we could not even determine current state.)
        metadata = self.get_album_metadata()
        metadata.update_counts(posts)
        metadata.last_update = datetime.now().isoformat()
        if instagram_post_id:
            metadata.last_posted_at = datetime.now().isoformat()
        workflow_run_id = os.getenv('GITHUB_RUN_ID')
        if workflow_run_id:
            metadata.add_workflow_run(workflow_run_id)
        try:
            self.storage_adapter.write_metadata(
                self.get_account_normalized(), self.current_album_id, metadata.to_dict()
            )
        except StateStorageError as e:
            self.logger.error(
                f"Post #{album_position} recorded, but metadata write failed "
                f"(derived stats will self-heal next run): {e}"
            )

        # Clear from failed positions on success (only writes when the photo
        # was previously failed — unchanged behavior, outside the base 2 writes)
        if instagram_post_id:
            self.remove_failed_position(album_position)

        return "dry_run" if is_dry_run else flickr_photo_id

    def get_posts_due_for_threads(self, delay_hours: int = 8,
                                  max_retries: int = 5) -> List[InstagramPost]:
        """Return posts eligible for delayed Threads cross-posting.

        A post is eligible when:
          - it was actually posted to Instagram (status POSTED, not a dry run, has instagram_post_id),
          - it has not yet been mirrored to Threads (no threads_post_id),
          - it was posted to Instagram at least `delay_hours` ago,
          - it has not exhausted the Threads retry budget.

        Returned oldest-first so callers process the longest-waiting post first.
        """
        try:
            cutoff = datetime.now() - timedelta(hours=delay_hours)
            posts = self.get_instagram_posts()

            due: List[InstagramPost] = []
            for post in posts:
                if post.status != PostStatus.POSTED:
                    continue
                if post.is_dry_run:
                    continue
                if not post.instagram_post_id:
                    continue
                if post.threads_post_id:
                    continue
                if post.threads_retry_count >= max_retries:
                    continue
                if not post.posted_at:
                    continue
                try:
                    posted_dt = datetime.fromisoformat(post.posted_at)
                except (TypeError, ValueError):
                    self.logger.warning(
                        f"Skipping post #{post.position}: unparseable posted_at={post.posted_at!r}"
                    )
                    continue
                if posted_dt > cutoff:
                    continue
                due.append(post)

            due.sort(key=lambda p: p.posted_at)
            return due

        except CriticalStateFailure:
            raise
        except Exception as e:
            self.logger.error(f"Failed to find posts due for Threads cross-posting: {e}")
            return []

    def _persist_posts(self, posts: List[InstagramPost]) -> bool:
        """Persist the full posts list to storage.

        Returns False (rather than propagating) on a write failure so Threads
        callers can record a retry; the read that precedes it still fails loud.
        """
        try:
            return self.storage_adapter.write_posts(
                self.get_account_normalized(),
                self.current_album_id,
                [p.to_dict() for p in posts]
            )
        except StateStorageError as e:
            self.logger.error(f"Failed to persist posts: {e}")
            return False

    def update_threads_post_id(self, position: int, threads_post_id: str,
                               caption: str) -> bool:
        """Update an existing post record with a successful Threads cross-post ID.

        Raises CriticalStateFailure if reading current state fails.
        """
        posts = self.get_instagram_posts()
        idx = next((i for i, p in enumerate(posts) if p.position == position), None)
        if idx is None:
            self.logger.error(
                f"Cannot update Threads post: no record at position {position}"
            )
            return False
        posts[idx].mark_threads_posted(threads_post_id, caption)
        return self._persist_posts(posts)

    def increment_threads_retry(self, position: int) -> bool:
        """Record a failed Threads attempt so retries eventually back off.

        Raises CriticalStateFailure if reading current state fails.
        """
        posts = self.get_instagram_posts()
        idx = next((i for i, p in enumerate(posts) if p.position == position), None)
        if idx is None:
            self.logger.error(
                f"Cannot increment Threads retry: no record at position {position}"
            )
            return False
        posts[idx].add_threads_retry()
        return self._persist_posts(posts)
