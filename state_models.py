"""
Enhanced data models for state management.

This module defines the data structures used by the new Git-based storage system,
providing rich metadata and better tracking capabilities.
"""

from dataclasses import dataclass, asdict, fields
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum


class PostStatus(Enum):
    """Status of an Instagram post."""
    PENDING = "pending"
    POSTED = "posted"
    FAILED = "failed"


class AlbumStatus(Enum):
    """Status of an album."""
    ACTIVE = "active"
    COMPLETED = "completed"
    PAUSED = "paused"
    ERROR = "error"


@dataclass
class InstagramPost:
    """Enhanced Instagram post record with rich metadata."""
    position: int
    photo_id: str
    instagram_post_id: Optional[str] = None
    facebook_post_id: Optional[str] = None
    threads_post_id: Optional[str] = None
    threads_posted_at: Optional[str] = None
    threads_caption: Optional[str] = None
    threads_retry_count: int = 0
    generated_body: Optional[str] = None
    posted_at: Optional[str] = None
    title: Optional[str] = None
    status: PostStatus = PostStatus.PENDING
    retry_count: int = 0
    workflow_run_id: Optional[str] = None
    account: Optional[str] = None
    created_at: Optional[str] = None
    last_update: Optional[str] = None
    flickr_url: Optional[str] = None
    instagram_url: Optional[str] = None
    caption_length: Optional[int] = None
    hashtags_count: Optional[int] = None
    is_dry_run: bool = False

    def __post_init__(self):
        """Initialize default values after creation."""
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.last_update is None:
            self.last_update = datetime.now().isoformat()

    @staticmethod
    def get_real_posted(posts: List['InstagramPost']) -> List['InstagramPost']:
        """Get posts that were actually posted (excludes dry runs)."""
        return [p for p in posts if p.status == PostStatus.POSTED and not p.is_dry_run]

    @staticmethod
    def count_real_posted(posts: List['InstagramPost']) -> int:
        """Count posts that were actually posted (excludes dry runs)."""
        return len(InstagramPost.get_real_posted(posts))

    def mark_as_posted(self, instagram_post_id: str, instagram_url: Optional[str] = None):
        """Mark the post as successfully posted."""
        self.status = PostStatus.POSTED
        self.instagram_post_id = instagram_post_id
        self.posted_at = datetime.now().isoformat()
        self.last_update = datetime.now().isoformat()
        if instagram_url:
            self.instagram_url = instagram_url

    def mark_threads_posted(self, threads_post_id: str, caption: str):
        """Record a successful Threads cross-post on this record."""
        self.threads_post_id = threads_post_id
        self.threads_caption = caption
        self.threads_posted_at = datetime.now().isoformat()
        self.last_update = datetime.now().isoformat()

    def add_threads_retry(self):
        """Increment the Threads retry counter on this record."""
        self.threads_retry_count += 1
        self.last_update = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        # Convert enum to string
        data['status'] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'InstagramPost':
        """Create from dictionary (JSON deserialization)."""
        payload = data.copy()

        # Normalize legacy keys
        if 'photo_id' not in payload and 'flickr_photo_id' in payload:
            payload['photo_id'] = payload.pop('flickr_photo_id')

        # Convert status string to enum
        if 'status' in payload:
            payload['status'] = PostStatus(payload['status'])

        # Drop unknown legacy fields (e.g. retry_history from pre-WP5 records)
        allowed = {field.name for field in fields(cls)}
        for key in list(payload.keys()):
            if key not in allowed:
                payload.pop(key)

        return cls(**payload)

@dataclass
class AlbumMetadata:
    """Enhanced album metadata with comprehensive tracking."""
    album_id: str
    account: str
    created_at: str
    last_update: str
    total_photos: int = 0
    posted_count: int = 0
    failed_count: int = 0
    pending_count: int = 0
    completion_status: AlbumStatus = AlbumStatus.ACTIVE
    completion_percentage: float = 0.0
    last_posted_position: Optional[int] = None
    last_posted_at: Optional[str] = None
    workflow_runs_count: int = 0
    error_count: int = 0
    last_error_message: Optional[str] = None
    last_error_at: Optional[str] = None

    def update_counts(self, posts: List[InstagramPost]):
        """Update statistics based on current post data (excludes dry runs from posted count)."""
        self.posted_count = InstagramPost.count_real_posted(posts)
        self.failed_count = len([p for p in posts if p.status == PostStatus.FAILED])
        self.pending_count = len([p for p in posts if p.status == PostStatus.PENDING])

        # Update completion percentage
        if self.total_photos > 0:
            self.completion_percentage = (self.posted_count / self.total_photos) * 100
        else:
            self.completion_percentage = 0.0

        # Update completion status
        if self.posted_count == self.total_photos and self.total_photos > 0:
            self.completion_status = AlbumStatus.COMPLETED
        elif self.failed_count > 0:
            self.completion_status = AlbumStatus.ERROR
        else:
            self.completion_status = AlbumStatus.ACTIVE

        # Update last posted information
        posted_posts = [p for p in posts if p.status == PostStatus.POSTED and p.posted_at]
        if posted_posts:
            latest_post = max(posted_posts, key=lambda p: p.posted_at)
            self.last_posted_position = latest_post.position
            self.last_posted_at = latest_post.posted_at

        self.last_update = datetime.now().isoformat()

    def add_workflow_run(self, workflow_run_id: str):
        """Record a new workflow run."""
        self.workflow_runs_count += 1
        self.last_update = datetime.now().isoformat()

    def add_error(self, error_message: str):
        """Record an error."""
        self.error_count += 1
        self.last_error_message = error_message
        self.last_error_at = datetime.now().isoformat()
        self.last_update = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        # Convert enum to string
        data['completion_status'] = self.completion_status.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AlbumMetadata':
        """Create from dictionary (JSON deserialization)."""
        payload = data.copy()

        # Normalize completion status
        if 'completion_status' in payload:
            payload['completion_status'] = AlbumStatus(payload['completion_status'])

        # Drop unknown legacy fields
        allowed = {field.name for field in fields(cls)}
        for key in list(payload.keys()):
            if key not in allowed:
                payload.pop(key)

        return cls(**payload)

    @classmethod
    def create_new(cls, album_id: str, account: str, total_photos: int = 0) -> 'AlbumMetadata':
        """Create new album metadata."""
        now = datetime.now().isoformat()
        return cls(
            album_id=album_id,
            account=account,
            created_at=now,
            last_update=now,
            total_photos=total_photos
        )


@dataclass
class FailedPosition:
    """Enhanced failed position record with context."""
    position: int
    photo_id: Optional[str] = None
    failed_at: Optional[str] = None
    error_message: Optional[str] = None
    workflow_run_id: Optional[str] = None
    retry_count: int = 0
    resolved: bool = False
    resolved_at: Optional[str] = None

    def __post_init__(self):
        """Initialize default values after creation."""
        if self.failed_at is None:
            self.failed_at = datetime.now().isoformat()

    def mark_resolved(self):
        """Mark the failed position as resolved."""
        self.resolved = True
        self.resolved_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FailedPosition':
        """Create from dictionary (JSON deserialization)."""
        payload = data.copy()
        if 'photo_id' not in payload and 'flickr_photo_id' in payload:
            payload['photo_id'] = payload.pop('flickr_photo_id')
        return cls(**payload)

    @classmethod
    def from_position(cls, position: int, photo_id: Optional[str] = None,
                     error_message: Optional[str] = None,
                     workflow_run_id: Optional[str] = None) -> 'FailedPosition':
        """Create from basic position information."""
        return cls(
            position=position,
            photo_id=photo_id,
            error_message=error_message,
            workflow_run_id=workflow_run_id
        )


