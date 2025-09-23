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

    def _read_json_file(self, file_path: str, default: Any = None) -> Any:
        """Read and parse JSON file from repository."""
        try:
            file_content = self.repo.get_contents(file_path, ref=self.branch)
            content_decoded = base64.b64decode(file_content.content).decode('utf-8')
            return json.loads(content_decoded)
        except GithubException as e:
            if e.status == 404:
                self.logger.debug(f"File {file_path} not found, returning default")
                return default if default is not None else []
            else:
                self.logger.error(f"Error reading file {file_path}: {e}")
                return default if default is not None else []
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in file {file_path}: {e}")
            return default if default is not None else []

    def _write_json_file(self, file_path: str, data: Any, commit_message: str) -> bool:
        """Write JSON data to repository file."""
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
                    raise e

            return True

        except Exception as e:
            self.logger.error(f"Failed to write file {file_path}: {e}")
            return False

    def read_posts(self, account: str, album_id: str) -> List[Dict]:
        """Read Instagram post records for an account/album."""
        if not self.is_available():
            return []

        file_path = self._get_file_path(account, album_id, "posts")
        return self._read_json_file(file_path, [])

    def write_posts(self, account: str, album_id: str, posts: List[Dict]) -> bool:
        """Write Instagram post records for an account/album."""
        if not self.is_available():
            return False

        file_path = self._get_file_path(account, album_id, "posts")
        timestamp = datetime.now().isoformat()
        commit_message = f"Update posts for {account}/album-{album_id} - {timestamp}"

        return self._write_json_file(file_path, posts, commit_message)

    def read_failed_positions(self, account: str, album_id: str) -> List[int]:
        """Read failed position records for an account/album."""
        if not self.is_available():
            return []

        file_path = self._get_file_path(account, album_id, "failed")
        return self._read_json_file(file_path, [])

    def write_failed_positions(self, account: str, album_id: str, positions: List[int]) -> bool:
        """Write failed position records for an account/album."""
        if not self.is_available():
            return False

        file_path = self._get_file_path(account, album_id, "failed")
        timestamp = datetime.now().isoformat()
        commit_message = f"Update failed positions for {account}/album-{album_id} - {timestamp}"

        return self._write_json_file(file_path, positions, commit_message)

    def read_metadata(self, account: str, album_id: str) -> Dict:
        """Read metadata for an account/album."""
        if not self.is_available():
            return {}

        file_path = self._get_file_path(account, album_id, "metadata")
        default_metadata = {
            "album_id": album_id,
            "account": account,
            "created_at": datetime.now().isoformat(),
            "last_update": datetime.now().isoformat(),
            "total_photos": 0,
            "posted_count": 0,
            "failed_count": 0,
            "completion_status": "active"
        }
        return self._read_json_file(file_path, default_metadata)

    def write_metadata(self, account: str, album_id: str, metadata: Dict) -> bool:
        """Write metadata for an account/album."""
        if not self.is_available():
            return False

        # Update last_update timestamp
        metadata["last_update"] = datetime.now().isoformat()

        file_path = self._get_file_path(account, album_id, "metadata")
        timestamp = datetime.now().isoformat()
        commit_message = f"Update metadata for {account}/album-{album_id} - {timestamp}"

        return self._write_json_file(file_path, metadata, commit_message)

    def is_available(self) -> bool:
        """Check if the storage backend is available and accessible."""
        if not self.github or not self.repo:
            return False

        try:
            # Try to access the repository to verify credentials
            self.repo.get_branch(self.branch)
            return True
        except Exception as e:
            self.logger.debug(f"Git storage not available: {e}")
            return False
