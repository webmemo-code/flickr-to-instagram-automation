"""
State management using GitHub Repository Variables for scalable tracking.
"""
import json
import logging
import subprocess
import os
from datetime import datetime
from typing import List, Optional, Dict
from github import Github
from config import Config

class StateManager:
    """Manage posting state using GitHub Environment Variables for proper account isolation."""
    
    def __init__(self, config: Config, repo_name: str, environment_name: str = None):
        self.config = config
        self.github = Github(config.github_token)
        self.repo = self.github.get_repo(repo_name)
        self.logger = logging.getLogger(__name__)
        self.current_album_id = config.flickr_album_id  # Track current album ID
        self.environment_name = environment_name or self._detect_environment_name(config.account)
        self.logger.info(f"StateManager initialized for account: {self.environment_name}")
    
    def _detect_environment_name(self, account: str) -> str:
        """Detect account suffix for variable naming."""
        if account and account.lower() == 'reisememo':
            return 'REISEMEMO'
        return 'PRIMARY'
    
    def _get_variable(self, name: str, default: str = "") -> str:
        """Get a state variable value with account-aware naming."""
        # Determine if this should be fetched from environment or repository variables
        if self._is_environment_specific_variable(name):
            return self._get_environment_variable(name, default)
        else:
            return self._get_repository_variable(name, default)

    def _get_environment_variable(self, name: str, default: str = "") -> str:
        """Get an environment-specific variable using GitHub CLI."""
        try:
            # Convert full variable name to environment-appropriate name
            if name.startswith('LAST_POSTED_POSITION_'):
                base_name = 'LAST_POSTED_POSITION'
            elif name.startswith('FAILED_POSITIONS_'):
                base_name = 'FAILED_POSITIONS'
            elif name.startswith('INSTAGRAM_POSTS_'):
                base_name = 'INSTAGRAM_POSTS'
            else:
                base_name = name.split('_')[0]

            # Try to get from GitHub CLI environment variables
            cmd = ['gh', 'variable', 'get', base_name, '--env', self.environment_name]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                value = result.stdout.strip()
                self.logger.debug(f"Found environment variable {base_name} = {value} for {self.environment_name}")
                return value
            else:
                # Variable not found, check if it's just missing or an error
                if "not found" in result.stderr.lower() or "no such variable" in result.stderr.lower():
                    self.logger.debug(f"Environment variable {base_name} not found for {self.environment_name}, using default: {default}")
                else:
                    self.logger.warning(f"Error getting environment variable {base_name}: {result.stderr}")
                return default

        except Exception as e:
            self.logger.debug(f"Error retrieving environment variable {name}: {e}, using default: {default}")
            return default

    def _get_repository_variable(self, name: str, default: str = "") -> str:
        """Get a repository-wide variable using PyGithub."""
        # Create account-scoped variable name to ensure isolation
        scoped_name = f"{name}_{self.environment_name}"

        try:
            # First, try to get from current environment variables (runtime)
            import os
            env_value = os.getenv(scoped_name)
            if env_value is not None:
                self.logger.debug(f"Found account-scoped variable {scoped_name} from runtime")
                return env_value

            # Fallback: try the original name for backwards compatibility
            env_value = os.getenv(name)
            if env_value is not None:
                self.logger.debug(f"Found variable {name} from runtime (legacy naming)")
                return env_value

            # Try repository variables with scoped name
            try:
                variable = self.repo.get_variable(scoped_name)
                self.logger.debug(f"Found account-scoped repository variable {scoped_name}")
                return variable.value
            except Exception:
                # Try original name in repository variables for backwards compatibility
                # BUT only if this is the primary account to avoid cross-account contamination
                if self.environment_name == 'PRIMARY':
                    try:
                        variable = self.repo.get_variable(name)
                        self.logger.warning(f"Found {name} in repository variables (legacy). Consider migrating to account-scoped variables.")
                        return variable.value
                    except Exception:
                        self.logger.debug(f"State variable {name} not found anywhere, using default: {default}")
                        return default
                else:
                    # For non-primary accounts (like Reisememo), don't fall back to legacy variables
                    # to avoid cross-account state contamination
                    self.logger.debug(f"Account-scoped variable {scoped_name} not found for {self.environment_name} account, using default: {default}")
                    return default

        except Exception as e:
            self.logger.debug(f"Error retrieving repository variable {name}: {e}, using default: {default}")
            return default
    
    def _set_variable(self, name: str, value: str) -> bool:
        """Set a state variable value with account-aware naming."""
        # Determine if this should be an environment variable or repository variable
        if self._is_environment_specific_variable(name):
            return self._set_environment_variable(name, value)
        else:
            return self._set_repository_variable(name, value)

    def _is_environment_specific_variable(self, name: str) -> bool:
        """Determine if a variable should be stored per-environment."""
        environment_specific = [
            "LAST_POSTED_POSITION_",
            "FAILED_POSITIONS_",
            "INSTAGRAM_POSTS_"
        ]
        return any(name.startswith(prefix) for prefix in environment_specific)

    def _set_environment_variable(self, name: str, value: str) -> bool:
        """Set an environment-specific variable using GitHub CLI."""
        try:
            # Convert full variable name to environment-appropriate name
            # LAST_POSTED_POSITION_72177720326837749 -> LAST_POSTED_POSITION
            # FAILED_POSITIONS_72177720326837749 -> FAILED_POSITIONS
            # INSTAGRAM_POSTS_72177720326837749 -> INSTAGRAM_POSTS
            if name.startswith('LAST_POSTED_POSITION_'):
                base_name = 'LAST_POSTED_POSITION'
            elif name.startswith('FAILED_POSITIONS_'):
                base_name = 'FAILED_POSITIONS'
            elif name.startswith('INSTAGRAM_POSTS_'):
                base_name = 'INSTAGRAM_POSTS'
            else:
                # Fallback for other environment-specific variables
                base_name = name.split('_')[0]

            cmd = [
                'gh', 'variable', 'set', base_name,
                '--env', self.environment_name,
                '--body', value
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                self.logger.debug(f"Set environment variable {base_name} = {value} for {self.environment_name}")
                return True
            else:
                self.logger.error(f"Failed to set environment variable {base_name}: {result.stderr}")
                return False

        except Exception as e:
            self.logger.error(f"Error setting environment variable {name}: {e}")
            return False

    def _set_repository_variable(self, name: str, value: str) -> bool:
        """Set a repository-wide variable using PyGithub (for global state)."""
        # Create account-scoped variable name to ensure isolation
        scoped_name = f"{name}_{self.environment_name}"

        try:
            # Try to update existing scoped variable
            try:
                variable = self.repo.get_variable(scoped_name)
                variable.edit(value)
                self.logger.debug(f"Updated repository variable {scoped_name} = {value}")
                return True
            except Exception:
                # Variable doesn't exist, create it
                try:
                    self.repo.create_variable(scoped_name, value)
                    self.logger.debug(f"Created repository variable {scoped_name} = {value}")
                    return True
                except Exception as create_e:
                    self.logger.error(f"Failed to create repository variable {scoped_name}: {create_e}")
                    return False

        except Exception as e:
            self.logger.error(f"Failed to set repository variable {scoped_name}: {e}")
            return False
    
    def _get_json_variable(self, name: str, default: list = None) -> list:
        """Get a JSON array from repository variable."""
        if default is None:
            default = []
        try:
            value = self._get_variable(name, "[]")
            return json.loads(value) if value else default
        except json.JSONDecodeError:
            self.logger.warning(f"Invalid JSON in variable {name}, using default")
            return default
    
    def _set_json_variable(self, name: str, value: list) -> bool:
        """Set a JSON array to repository variable."""
        try:
            json_str = json.dumps(value)
            return self._set_variable(name, json_str)
        except Exception as e:
            self.logger.error(f"Failed to set JSON variable {name}: {e}")
            return False
    
    def _extract_photo_id(self, issue_body: str) -> Optional[str]:
        """Extract photo ID from issue body, handling different formats."""
        if not issue_body:
            return None
            
        lines = issue_body.split('\n')
        for line in lines:
            if line.startswith('**Photo ID:**'):
                photo_id = line.split(':', 1)[1].strip()
                
                # Clean up any markdown formatting that might be present
                while photo_id.startswith('**'):
                    photo_id = photo_id[2:].strip()
                while photo_id.startswith('*'):
                    photo_id = photo_id[1:].strip()
                while photo_id.endswith('**'):
                    photo_id = photo_id[:-2].strip()
                while photo_id.endswith('*'):
                    photo_id = photo_id[:-1].strip()
                
                # Return only if we have a valid non-empty ID
                if photo_id:
                    return str(photo_id).strip()
        return None
    
    def _extract_album_id(self, issue_body: str) -> Optional[str]:
        """Extract album ID from issue body."""
        if not issue_body:
            return None
            
        lines = issue_body.split('\n')
        for line in lines:
            if line.startswith('**Album ID:**'):
                album_id = line.split(':', 1)[1].strip()
                
                # Clean up any markdown formatting that might be present
                while album_id.startswith('**'):
                    album_id = album_id[2:].strip()
                while album_id.startswith('*'):
                    album_id = album_id[1:].strip()
                while album_id.endswith('**'):
                    album_id = album_id[:-2].strip()
                while album_id.endswith('*'):
                    album_id = album_id[:-1].strip()
                
                # Return only if we have a valid non-empty ID
                if album_id:
                    return str(album_id).strip()
        return None
    
    def _is_from_current_album(self, issue_body: str, issue_number: int = None) -> bool:
        """Check if an issue is from the current album."""
        album_id = self._extract_album_id(issue_body)
        
        # If album ID is explicitly set and matches current album, it's from current album
        if album_id == self.current_album_id:
            return True
        
        # If album ID is explicitly set but doesn't match, exclude it
        if album_id is not None and album_id != self.current_album_id:
            return False
        
        # For issues without album ID (legacy), use issue number heuristic
        # Based on user info: Issues #65-#101 are from current "Istrien" album
        # Issues #61 and below are from previous album
        if album_id is None and issue_number is not None:
            # Current Istrien album issues are #65 and above
            return issue_number >= 65
        
        # Default fallback: assume it's from current album (conservative approach)
        return True
    
    def get_last_posted_position(self) -> int:
        """Get the position of the last successfully posted photo."""
        try:
            position_str = self._get_variable(f"LAST_POSTED_POSITION_{self.current_album_id}", "0")
            return int(position_str)
        except (ValueError, TypeError):
            self.logger.warning(f"Invalid last posted position, defaulting to 0")
            return 0
    
    def set_last_posted_position(self, position: int) -> bool:
        """Set the position of the last successfully posted photo."""
        return self._set_variable(f"LAST_POSTED_POSITION_{self.current_album_id}", str(position))
    
    def get_failed_positions(self) -> List[int]:
        """Get list of photo positions that have failed to post."""
        try:
            failed_data = self._get_json_variable(f"FAILED_POSITIONS_{self.current_album_id}", [])
            return [int(pos) for pos in failed_data if isinstance(pos, (int, str))]
        except (ValueError, TypeError):
            self.logger.warning(f"Invalid failed positions data, defaulting to empty list")
            return []
    
    def add_failed_position(self, position: int) -> bool:
        """Add a position to the failed positions list."""
        failed_positions = self.get_failed_positions()
        if position not in failed_positions:
            failed_positions.append(position)
            return self._set_json_variable(f"FAILED_POSITIONS_{self.current_album_id}", failed_positions)
        return True
    
    def remove_failed_position(self, position: int) -> bool:
        """Remove a position from the failed positions list (when successfully posted)."""
        failed_positions = self.get_failed_positions()
        if position in failed_positions:
            failed_positions.remove(position)
            return self._set_json_variable(f"FAILED_POSITIONS_{self.current_album_id}", failed_positions)
        return True
    
    def get_total_album_photos(self) -> int:
        """Get the total number of photos in the current album."""
        try:
            total_str = self._get_variable(f"TOTAL_ALBUM_PHOTOS_{self.current_album_id}", "0")
            return int(total_str)
        except (ValueError, TypeError):
            self.logger.warning(f"Invalid total album photos, defaulting to 0")
            return 0
    
    def set_total_album_photos(self, total: int) -> bool:
        """Set the total number of photos in the current album."""
        return self._set_variable(f"TOTAL_ALBUM_PHOTOS_{self.current_album_id}", str(total))
    
    def get_instagram_posts(self) -> List[Dict]:
        """Get all Instagram post records for the current album."""
        return self._get_json_variable(f"INSTAGRAM_POSTS_{self.current_album_id}", [])
    
    def get_posted_photo_ids(self) -> List[str]:
        """Legacy method for compatibility - returns empty list since we track by position now."""
        self.logger.warning("get_posted_photo_ids() is deprecated - use position-based tracking instead")
        return []

    def get_dry_run_photo_ids(self) -> List[str]:
        """Get list of photo IDs that have been selected in dry runs from the current album."""
        try:
            issues = self.repo.get_issues(
                state='all',
                labels=['automated-post', 'dry-run', 'flickr-album']
            )
            
            dry_run_ids = []
            for issue in issues:
                # Only include photos from the current album
                if self._is_from_current_album(issue.body, issue.number):
                    photo_id = self._extract_photo_id(issue.body)
                    if photo_id:
                        # Ensure photo ID is a string and not already in list
                        photo_id_str = str(photo_id).strip()
                        if photo_id_str and photo_id_str not in dry_run_ids:
                            dry_run_ids.append(photo_id_str)
                            self.logger.debug(f"Found dry run photo ID: {photo_id_str} from issue #{issue.number} (current album)")
            
            self.logger.info(f"Found {len(dry_run_ids)} dry run selections from current album: {dry_run_ids}")
            return dry_run_ids
            
        except Exception as e:
            self.logger.error(f"Failed to get dry run photo IDs: {e}")
            return []

    def get_failed_photo_ids(self) -> List[str]:
        """Get list of photo IDs that have failed to post from the current album."""
        try:
            issues = self.repo.get_issues(
                state='all',
                labels=['automated-post', 'instagram', 'flickr-album', 'failed']
            )
            
            failed_ids = []
            for issue in issues:
                # Only include photos from the current album
                if self._is_from_current_album(issue.body, issue.number):
                    photo_id = self._extract_photo_id(issue.body)
                    if photo_id:
                        # Ensure photo ID is a string and not already in list
                        photo_id_str = str(photo_id).strip()
                        if photo_id_str and photo_id_str not in failed_ids:
                            failed_ids.append(photo_id_str)
                            self.logger.debug(f"Found failed photo ID: {photo_id_str} from issue #{issue.number} (current album)")
            
            self.logger.info(f"Found {len(failed_ids)} failed photos from current album: {failed_ids}")
            return failed_ids
            
        except Exception as e:
            self.logger.error(f"Failed to get failed photo IDs: {e}")
            return []
    
    def create_post_record(self, photo_data: Dict, instagram_post_id: Optional[str] = None, is_dry_run: bool = False, create_audit_issue: bool = False) -> Optional[str]:
        """Record a successful post using position-based tracking."""
        try:
            position = photo_data.get('album_position', 0)
            title = photo_data.get('title', 'Unknown')
            
            if is_dry_run:
                # For dry runs, just log - don't create issues or update state
                self.logger.info(f"DRY RUN: Would post photo #{position} - {title}")
                return "dry_run"
            
            # For successful posts, update position tracking
            if instagram_post_id:
                # Update last posted position
                self.set_last_posted_position(position)
                
                # Remove from failed positions if it was there
                self.remove_failed_position(position)
                
                # Store Instagram post ID in repository variable for reference
                instagram_posts = self._get_json_variable(f"INSTAGRAM_POSTS_{self.current_album_id}", [])
                post_record = {
                    "position": position,
                    "photo_id": photo_data['id'],
                    "instagram_post_id": instagram_post_id,
                    "posted_at": datetime.now().isoformat(),
                    "title": title
                }
                instagram_posts.append(post_record)
                self._set_json_variable(f"INSTAGRAM_POSTS_{self.current_album_id}", instagram_posts)
                
                # Optionally create audit trail issue (disabled by default for scale)
                issue_number = None
                if create_audit_issue:
                    timestamp = datetime.now().isoformat()
                    title_text = f"Posted: {title} (#{position}) - {timestamp}"
                    
                    body_parts = [
                        f"**Photo ID:** {photo_data['id']}",
                        f"**Album ID:** {self.current_album_id}",
                        f"**Album Position:** {position}",
                        f"**Title:** {title}",
                        f"**Description:** {photo_data.get('description', 'N/A')}",
                        f"**Image URL:** {photo_data['url']}",
                        f"**Posted At:** {timestamp}",
                        f"**Instagram Post ID:** {instagram_post_id}"
                    ]
                    
                    body = '\n'.join(body_parts)
                    
                    issue = self.repo.create_issue(
                        title=title_text,
                        body=body,
                        labels=['automated-post', 'instagram', 'flickr-album', 'posted']
                    )
                    issue_number = str(issue.number)
                    self.logger.info(f"✅ POSTED: Photo #{position} successfully posted to Instagram (issue #{issue.number})")
                else:
                    self.logger.info(f"✅ POSTED: Photo #{position} successfully posted to Instagram (ID: {instagram_post_id})")
                
                return issue_number or "success"
            else:
                # For failed posts, add to failed positions
                self.add_failed_position(position)
                self.logger.error(f"❌ FAILED: Photo #{position} failed to post, added to retry list")
                return None
            
        except Exception as e:
            self.logger.error(f"Failed to create post record: {e}")
            return None
    
    def update_post_record(self, issue_number: str, instagram_post_id: str) -> bool:
        """Update a post record with Instagram post ID."""
        try:
            issue = self.repo.get_issue(int(issue_number))
            
            # Update body with Instagram post ID
            current_body = issue.body or ""
            if "Instagram Post ID:" not in current_body:
                updated_body = current_body + f"\n**Instagram Post ID:** {instagram_post_id}"
                issue.edit(body=updated_body)
            
            # Update labels
            current_labels = [label.name for label in issue.labels]
            if 'failed' in current_labels:
                current_labels.remove('failed')
            if 'posted' not in current_labels:
                current_labels.append('posted')
            
            issue.edit(labels=current_labels)
            
            self.logger.info(f"Updated issue #{issue_number} with Instagram post ID")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update post record: {e}")
            return False
    
    def get_next_photo_to_post(self, photos: List[Dict], include_dry_runs: bool = False) -> Optional[Dict]:
        """Get the next photo that hasn't been posted yet, using position-based tracking."""
        # Initialize total photos count if not set
        if not photos:
            self.logger.warning("No photos provided to get_next_photo_to_post")
            return None
        
        total_photos = len(photos)
        if self.get_total_album_photos() != total_photos:
            self.set_total_album_photos(total_photos)
            self.logger.info(f"Updated total album photos to {total_photos}")
        
        # Sort photos by their album position to ensure correct chronological order (oldest first)
        sorted_photos = sorted(photos, key=lambda x: x.get('album_position', 0))
        
        last_posted_position = self.get_last_posted_position()
        failed_positions = self.get_failed_positions()
        
        self.logger.info(f"Position tracking - Last posted: {last_posted_position}, Failed positions: {failed_positions}")
        self.logger.info(f"Checking {len(sorted_photos)} photos for next position to post")
        
        # Find the next photo to post
        for photo in sorted_photos:
            position = photo.get('album_position', 0)
            title = photo.get('title', 'Unknown')
            photo_id = photo.get('id', 'unknown')
            
            # Skip if position is less than or equal to last posted position
            if position <= last_posted_position:
                self.logger.debug(f"Photo #{position}: {title} - ALREADY POSTED (last posted: {last_posted_position})")
                continue
            
            # Skip if position is in failed positions (unless retrying)
            if position in failed_positions:
                self.logger.debug(f"Photo #{position}: {title} - PREVIOUSLY FAILED (skipping for now)")
                continue
            
            # This is the next photo to post
            self.logger.info(f"✅ SELECTED: Next photo to post is #{position} - {title} (ID: {photo_id})")
            return photo
        
        # Check if we should retry any failed positions
        if failed_positions:
            self.logger.info(f"No new photos to post, checking {len(failed_positions)} failed positions for retry")
            for position in sorted(failed_positions):
                for photo in sorted_photos:
                    if photo.get('album_position') == position:
                        title = photo.get('title', 'Unknown')
                        photo_id = photo.get('id', 'unknown')
                        self.logger.info(f"🔄 RETRY: Attempting failed photo #{position} - {title} (ID: {photo_id})")
                        return photo
        
        self.logger.info("No unposted photos found - all photos have been posted!")
        return None

    def clear_dry_run_records(self) -> int:
        """Clear all dry run records. Returns number of records cleared."""
        try:
            issues = self.repo.get_issues(
                state='all',
                labels=['automated-post', 'dry-run', 'flickr-album']
            )
            
            cleared_count = 0
            for issue in issues:
                issue.edit(state='closed')
                cleared_count += 1
                self.logger.debug(f"Closed dry run issue #{issue.number}")
            
            self.logger.info(f"Cleared {cleared_count} dry run records")
            return cleared_count
            
        except Exception as e:
            self.logger.error(f"Failed to clear dry run records: {e}")
            return 0
    
    def log_automation_run(self, success: bool, details: str = "", account_name: str = "", album_name: str = "", album_url: str = "") -> None:
        """Log an automation run with enhanced context."""
        try:
            timestamp = datetime.now().isoformat()
            status = "SUCCESS" if success else "FAILED"
            
            # Build enhanced title with account and album info
            title_parts = [f"Automation Run: {status}"]
            if account_name:
                title_parts.append(f"({account_name} account)")
            title_parts.append(f"({timestamp})")
            title = " ".join(title_parts)
            
            # Build enhanced details with album context
            enhanced_details = details
            if account_name or album_name:
                context_parts = []
                if account_name:
                    context_parts.append(f"{account_name} account")
                if album_name:
                    context_parts.append(f"{album_name}")
                    if album_url:
                        context_parts.append(f"({album_url})")
                
                if context_parts:
                    if enhanced_details:
                        enhanced_details = f"{' '.join(context_parts)} - {enhanced_details}"
                    else:
                        enhanced_details = ' '.join(context_parts)
            
            body_parts = [
                f"**Status:** {status}",
                f"**Timestamp:** {timestamp}",
                f"**Details:** {enhanced_details}",
            ]
            
            # Add account and album info to body if available
            if account_name:
                body_parts.append(f"**Account:** {account_name}")
            if album_name:
                body_parts.append(f"**Album:** {album_name}")
            if album_url:
                body_parts.append(f"**Album URL:** {album_url}")
            
            body = '\n'.join(body_parts)
            
            labels = [
                'automation-log',
                'flickr-album',
                'success' if success else 'failure'
            ]
            
            # Add account-specific label if available
            if account_name and account_name.lower() != 'primary':
                labels.append(f'account-{account_name.lower()}')
            
            issue = self.repo.create_issue(
                title=title,
                body=body,
                labels=labels
            )
            
            self.logger.info(f"Created automation log issue #{issue.number}")
            
        except Exception as e:
            self.logger.error(f"Failed to log automation run: {e}")
    
    def get_automation_stats(self) -> Dict:
        """Get automation statistics."""
        try:
            # Get posted photos count
            posted_issues = self.repo.get_issues(
                state='all',
                labels=['automated-post', 'instagram', 'flickr-album', 'posted']
            )
            posted_count = posted_issues.totalCount
            
            # Get failed posts count
            failed_issues = self.repo.get_issues(
                state='all',
                labels=['automated-post', 'instagram', 'flickr-album', 'failed']
            )
            failed_count = failed_issues.totalCount
            
            # Get automation run stats
            success_runs = self.repo.get_issues(
                state='all',
                labels=['automation-log', 'flickr-album', 'success']
            )
            success_count = success_runs.totalCount
            
            failed_runs = self.repo.get_issues(
                state='all',
                labels=['automation-log', 'flickr-album', 'failure']
            )
            failure_count = failed_runs.totalCount
            
            stats = {
                'posted_photos': posted_count,
                'failed_photos': failed_count,
                'successful_runs': success_count,
                'failed_runs': failure_count,
                'success_rate': round(success_count / (success_count + failure_count) * 100, 2) if (success_count + failure_count) > 0 else 0
            }
            
            self.logger.info(f"Album stats: {stats}")
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get automation stats: {e}")
            return {}
    
    def is_album_complete(self, total_photos: int) -> bool:
        """Check if all photos in the album have been processed using position tracking."""
        if total_photos <= 0:
            self.logger.warning(f"No photos found in album (total_photos: {total_photos}). This might indicate a Flickr API issue.")
            return False  # If we can't get photos, assume not complete to allow retry
        
        # Update total photos if different
        stored_total = self.get_total_album_photos()
        if stored_total != total_photos:
            self.set_total_album_photos(total_photos)
            self.logger.info(f"Updated total album photos from {stored_total} to {total_photos}")
        
        last_posted_position = self.get_last_posted_position()
        failed_positions = self.get_failed_positions()
        failed_count = len(failed_positions)
        
        # Album is complete if last posted position equals total photos
        is_complete = last_posted_position >= total_photos
        
        if is_complete:
            self.logger.info(f"✅ Album complete! Posted {last_posted_position} of {total_photos} photos ({failed_count} failed positions remaining for manual retry)")
        else:
            remaining = total_photos - last_posted_position
            self.logger.info(f"📊 Album progress: {last_posted_position} of {total_photos} photos posted ({remaining} remaining, {failed_count} failed)")
        
        return is_complete