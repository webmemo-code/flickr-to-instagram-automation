"""
Storage adapters for state management.

This module provides abstract interfaces and concrete implementations for storing
automation state data, replacing the repository variable storage system.
"""

import json
import base64
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from datetime import datetime
from github import Github
from github.Repository import Repository
from github.GithubException import GithubException


class StateFileNotFound(Exception):
    """Raised when a state file (or its branch) does not exist yet.

    This is the ONLY 'absent' outcome — a fresh album or first-ever run where
    the Contents API returns 404. Callers translate it into an empty default.
    Every other read failure (401/403, 5xx, rate-limit, connection error,
    malformed JSON) propagates as a real exception so it can never be mistaken
    for empty state (see docs/refactor/03-state-layer-spec.md, error taxonomy).
    """
    pass


class StateStorageError(Exception):
    """Raised when a storage read/write fails for any non-absent reason.

    Distinct from StateFileNotFound so StateManager can fail loud
    (CriticalStateFailure) instead of silently returning empty/false.
    """
    pass


class StateStorageAdapter(ABC):
    """Abstract base class for state storage backends."""

    @abstractmethod
    def read_posts(self, account: str, album_id: str) -> List[Dict]:
        """Read Instagram post records for an account/album."""
        pass

    @abstractmethod
    def write_posts(self, account: str, album_id: str, posts: List[Dict]) -> bool:
        """Write Instagram post records for an account/album."""
        pass

    @abstractmethod
    def read_failed_positions(self, account: str, album_id: str) -> List[int]:
        """Read failed position records for an account/album."""
        pass

    @abstractmethod
    def write_failed_positions(self, account: str, album_id: str, positions: List[int]) -> bool:
        """Write failed position records for an account/album."""
        pass

    @abstractmethod
    def read_metadata(self, account: str, album_id: str) -> Dict:
        """Read metadata for an account/album."""
        pass

    @abstractmethod
    def write_metadata(self, account: str, album_id: str, metadata: Dict) -> bool:
        """Write metadata for an account/album."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the storage backend is available and accessible."""
        pass


class GitFileStorageAdapter(StateStorageAdapter):
    """Git-based file storage implementation using GitHub Contents API."""

    def __init__(self, repo_name: str, github_token: str, branch: str = "automation-state"):
        """
        Initialize Git file storage adapter.

        Args:
            repo_name: Full repository name (e.g., 'owner/repo')
            github_token: GitHub token with contents:write permission
            branch: Branch name to store state files (default: 'automation-state')
        """
        self.repo_name = repo_name
        self.github_token = github_token
        self.branch = branch
        self.logger = logging.getLogger(__name__)

        # is_available() result is cached for the adapter instance lifetime
        # (one instance per run) so reads/writes don't each issue a live
        # get_branch call. None = not yet checked.
        self._available: Optional[bool] = None

        # Initialize GitHub client
        try:
            self.github = Github(github_token)
            self.repo = self.github.get_repo(repo_name)
            self._ensure_branch_exists()
        except Exception as e:
            self.logger.error(f"Failed to initialize GitFileStorageAdapter: {e}")
            self.github = None
            self.repo = None

    def _ensure_branch_exists(self) -> bool:
        """Ensure the automation-state branch exists."""
        try:
            # Try to get the branch
            self.repo.get_branch(self.branch)
            self.logger.debug(f"Branch '{self.branch}' already exists")
            return True
        except GithubException as e:
            if e.status == 404:
                # Branch doesn't exist, create it
                try:
                    # Get the default branch's latest commit
                    default_branch = self.repo.default_branch
                    ref = self.repo.get_git_ref(f"heads/{default_branch}")

                    # Create new branch from default branch
                    self.repo.create_git_ref(f"refs/heads/{self.branch}", ref.object.sha)
                    self.logger.info(f"Created branch '{self.branch}'")
                    return True
                except Exception as create_e:
                    self.logger.error(f"Failed to create branch '{self.branch}': {create_e}")
                    return False
            else:
                self.logger.error(f"Error accessing branch '{self.branch}': {e}")
                return False

    def _get_file_path(self, account: str, album_id: str, file_type: str) -> str:
        """Generate file path for state data."""
        # Normalize account name for filesystem
        account_normalized = account.lower().replace('-', '_')
        return f"state-data/{account_normalized}/album-{album_id}/{file_type}.json"

    def _read_json_file(self, file_path: str) -> Any:
        """Read and parse a JSON file from the repository.

        Returns the parsed JSON on success.

        Raises:
            StateFileNotFound: the file does not exist yet (Contents API 404).
                This is the ONLY 'absent' outcome; callers translate it into
                their empty default.
            StateStorageError: any other failure (401/403, 5xx, rate-limit,
                connection error, malformed JSON). Never silently downgraded
                to an empty result.
        """
        try:
            file_content = self.repo.get_contents(file_path, ref=self.branch)
            content_decoded = base64.b64decode(file_content.content).decode('utf-8')
            return json.loads(content_decoded)
        except GithubException as e:
            if e.status == 404:
                self.logger.debug(f"File {file_path} not found (absent)")
                raise StateFileNotFound(file_path) from e
            self.logger.error(f"Error reading file {file_path}: {e}")
            raise StateStorageError(f"Failed to read {file_path}: {e}") from e
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in file {file_path}: {e}")
            raise StateStorageError(f"Malformed JSON in {file_path}: {e}") from e
        except StateFileNotFound:
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error reading file {file_path}: {e}")
            raise StateStorageError(f"Failed to read {file_path}: {e}") from e

    def _write_json_file(self, file_path: str, data: Any, commit_message: str) -> bool:
        """Write JSON data to a repository file.

        Returns True on success.

        Raises:
            StateStorageError: the write failed (stale sha from a concurrent
                update, 5xx, permission error, connection error, ...). A failed
                write must never be reported to StateManager as success, or a
                post could be published without its state record being saved.
        """
        try:
            content = json.dumps(data, indent=2, default=str)
            # GitHub Contents API automatically handles base64 encoding - don't encode manually

            # Check if file exists to determine if we're creating or updating
            try:
                existing_file = self.repo.get_contents(file_path, ref=self.branch)
                # File exists, update it
                self.repo.update_file(
                    path=file_path,
                    message=commit_message,
                    content=content,
                    sha=existing_file.sha,
                    branch=self.branch
                )
                self.logger.debug(f"Updated file {file_path}")
            except GithubException as e:
                if e.status == 404:
                    # File doesn't exist, create it
                    self.repo.create_file(
                        path=file_path,
                        message=commit_message,
                        content=content,
                        branch=self.branch
                    )
                    self.logger.debug(f"Created file {file_path}")
                else:
                    raise

            return True

        except Exception as e:
            self.logger.error(f"Failed to write file {file_path}: {e}")
            raise StateStorageError(f"Failed to write {file_path}: {e}") from e

    def _require_available(self) -> None:
        """Raise StateStorageError if the storage backend can't be reached.

        An unreachable branch is a Denied/Failed outcome, not Absent — it must
        never be silently downgraded to an empty read or a no-op write.
        """
        if not self.is_available():
            raise StateStorageError(
                f"State storage unavailable: cannot reach branch "
                f"'{self.branch}' on {self.repo_name}"
            )

    def read_posts(self, account: str, album_id: str) -> List[Dict]:
        """Read Instagram post records for an account/album.

        Returns [] only when the file is absent (first run). Any access
        failure raises StateStorageError — never a spurious empty list.
        """
        self._require_available()

        file_path = self._get_file_path(account, album_id, "posts")
        try:
            return self._read_json_file(file_path)
        except StateFileNotFound:
            return []

    def write_posts(self, account: str, album_id: str, posts: List[Dict]) -> bool:
        """Write Instagram post records for an account/album."""
        self._require_available()

        file_path = self._get_file_path(account, album_id, "posts")
        timestamp = datetime.now().isoformat()
        commit_message = f"Update posts for {account}/album-{album_id} - {timestamp}"

        return self._write_json_file(file_path, posts, commit_message)

    def read_failed_positions(self, account: str, album_id: str) -> List[int]:
        """Read failed position records for an account/album.

        Returns [] only when the file is absent; access failures raise.
        """
        self._require_available()

        file_path = self._get_file_path(account, album_id, "failed")
        try:
            return self._read_json_file(file_path)
        except StateFileNotFound:
            return []

    def write_failed_positions(self, account: str, album_id: str, positions: List[int]) -> bool:
        """Write failed position records for an account/album."""
        self._require_available()

        file_path = self._get_file_path(account, album_id, "failed")
        timestamp = datetime.now().isoformat()
        commit_message = f"Update failed positions for {account}/album-{album_id} - {timestamp}"

        return self._write_json_file(file_path, positions, commit_message)

    def read_metadata(self, account: str, album_id: str) -> Dict:
        """Read metadata for an account/album.

        Returns a fresh default dict only when the file is absent (first run);
        access failures raise.
        """
        self._require_available()

        file_path = self._get_file_path(account, album_id, "metadata")
        try:
            return self._read_json_file(file_path)
        except StateFileNotFound:
            return {
                "album_id": album_id,
                "account": account,
                "created_at": datetime.now().isoformat(),
                "last_update": datetime.now().isoformat(),
                "total_photos": 0,
                "posted_count": 0,
                "failed_count": 0,
                "completion_status": "active"
            }

    def write_metadata(self, account: str, album_id: str, metadata: Dict) -> bool:
        """Write metadata for an account/album."""
        self._require_available()

        # Update last_update timestamp
        metadata["last_update"] = datetime.now().isoformat()

        file_path = self._get_file_path(account, album_id, "metadata")
        timestamp = datetime.now().isoformat()
        commit_message = f"Update metadata for {account}/album-{album_id} - {timestamp}"

        return self._write_json_file(file_path, metadata, commit_message)

    def is_available(self) -> bool:
        """Check if the storage backend is available and accessible.

        The result is cached for the adapter instance lifetime (one instance
        per run), so consecutive reads/writes issue exactly one get_branch
        call rather than one per operation.
        """
        if self._available is not None:
            return self._available

        if not self.github or not self.repo:
            self._available = False
            return False

        try:
            # Try to access the repository to verify credentials
            self.repo.get_branch(self.branch)
            self._available = True
        except Exception as e:
            self.logger.debug(f"Git storage not available: {e}")
            self._available = False

        return self._available
