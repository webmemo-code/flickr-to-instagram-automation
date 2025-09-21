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

    def migrate_from_repository_variables(self, old_state_manager) -> Dict[str, Any]:
        """
        Migrate existing data from repository variables to Git storage.

        Args:
            old_state_manager: StateManager instance with repository variable access

        Returns:
            Dict containing migration results and statistics
        """
        migration_results = {
            "success": False,
            "accounts_migrated": [],
            "albums_migrated": [],
            "posts_migrated": 0,
            "failed_positions_migrated": 0,
            "errors": []
        }

        try:
            # Get all repository variables that match our patterns
            repo_vars = self.repo.get_variables()

            for var in repo_vars:
                var_name = var.name

                # Parse variable names to extract account and album info
                if "_INSTA_POSTS_" in var_name:
                    # Format: {ENVIRONMENT}_INSTA_POSTS_{ALBUM_ID}
                    parts = var_name.split("_INSTA_POSTS_")
                    if len(parts) == 2:
                        environment = parts[0]
                        album_id = parts[1]

                        # Convert environment to account name
                        account = "primary" if environment == "PRIMARY_ACCOUNT" else "secondary"

                        try:
                            # Parse existing JSON data
                            posts_data = json.loads(var.value) if var.value else []

                            # Migrate posts data
                            if self.write_posts(account, album_id, posts_data):
                                migration_results["posts_migrated"] += len(posts_data)
                                if account not in migration_results["accounts_migrated"]:
                                    migration_results["accounts_migrated"].append(account)
                                if album_id not in migration_results["albums_migrated"]:
                                    migration_results["albums_migrated"].append(album_id)
                            else:
                                migration_results["errors"].append(f"Failed to migrate posts for {account}/{album_id}")

                        except json.JSONDecodeError as e:
                            migration_results["errors"].append(f"Invalid JSON in {var_name}: {e}")

                elif "_FAILED_POSITIONS_" in var_name:
                    # Format: {ENVIRONMENT}_FAILED_POSITIONS_{ALBUM_ID}
                    parts = var_name.split("_FAILED_POSITIONS_")
                    if len(parts) == 2:
                        environment = parts[0]
                        album_id = parts[1]

                        # Convert environment to account name
                        account = "primary" if environment == "PRIMARY_ACCOUNT" else "secondary"

                        try:
                            # Parse existing JSON data
                            failed_data = json.loads(var.value) if var.value else []

                            # Migrate failed positions data
                            if self.write_failed_positions(account, album_id, failed_data):
                                migration_results["failed_positions_migrated"] += len(failed_data)
                                if account not in migration_results["accounts_migrated"]:
                                    migration_results["accounts_migrated"].append(account)
                                if album_id not in migration_results["albums_migrated"]:
                                    migration_results["albums_migrated"].append(album_id)
                            else:
                                migration_results["errors"].append(f"Failed to migrate failed positions for {account}/{album_id}")

                        except json.JSONDecodeError as e:
                            migration_results["errors"].append(f"Invalid JSON in {var_name}: {e}")

            # Create initial metadata for migrated albums
            for account in migration_results["accounts_migrated"]:
                for album_id in migration_results["albums_migrated"]:
                    posts = self.read_posts(account, album_id)
                    failed = self.read_failed_positions(account, album_id)

                    metadata = {
                        "album_id": album_id,
                        "account": account,
                        "created_at": datetime.now().isoformat(),
                        "last_update": datetime.now().isoformat(),
                        "total_photos": 0,  # Will be updated by StateManager
                        "posted_count": len(posts),
                        "failed_count": len(failed),
                        "completion_status": "active",
                        "migrated_from": "repository_variables",
                        "migration_date": datetime.now().isoformat()
                    }

                    self.write_metadata(account, album_id, metadata)

            migration_results["success"] = len(migration_results["errors"]) == 0

        except Exception as e:
            migration_results["errors"].append(f"Migration failed: {e}")
            self.logger.error(f"Migration failed: {e}")

        return migration_results


class RepositoryVariableStorageAdapter(StateStorageAdapter):
    """
    Legacy repository variable storage adapter.

    This maintains the existing repository variable storage system for
    backward compatibility during migration.
    """

    def __init__(self, state_manager):
        """Initialize with existing StateManager instance."""
        self.state_manager = state_manager
        self.logger = logging.getLogger(__name__)

    def read_posts(self, account: str, album_id: str) -> List[Dict]:
        """Read posts using legacy repository variable method."""
        # Use the state manager's existing method
        return self.state_manager.get_instagram_posts()

    def write_posts(self, account: str, album_id: str, posts: List[Dict]) -> bool:
        """Write posts using legacy repository variable method."""
        # The legacy system doesn't support bulk writes, only individual appends
        # This is a limitation we're migrating away from
        return True

    def read_failed_positions(self, account: str, album_id: str) -> List[int]:
        """Read failed positions using legacy repository variable method."""
        return self.state_manager.get_failed_positions()

    def write_failed_positions(self, account: str, album_id: str, positions: List[int]) -> bool:
        """Write failed positions using legacy repository variable method."""
        # The legacy system manages this internally
        return True

    def read_metadata(self, account: str, album_id: str) -> Dict:
        """Read metadata (limited in legacy system)."""
        return {
            "album_id": album_id,
            "account": account,
            "legacy_system": True
        }

    def write_metadata(self, account: str, album_id: str, metadata: Dict) -> bool:
        """Write metadata (not supported in legacy system)."""
        return True

    def is_available(self) -> bool:
        """Check if legacy storage is available."""
        return hasattr(self.state_manager, 'repo') and self.state_manager.repo is not None