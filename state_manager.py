"""
State management using GitHub Issues for tracking posted content.
"""
import json
import logging
from datetime import datetime
from typing import List, Optional, Dict
from github import Github
from config import Config

class StateManager:
    """Manage posting state using GitHub Issues."""
    
    def __init__(self, config: Config, repo_name: str):
        self.config = config
        self.github = Github(config.github_token)
        self.repo = self.github.get_repo(repo_name)
        self.logger = logging.getLogger(__name__)
        self.current_album_id = config.flickr_album_id  # Track current album ID
    
    def _extract_photo_id(self, issue_body: str) -> Optional[str]:
        """Extract photo ID from issue body, handling different formats."""
        if not issue_body:
            return None
            
        lines = issue_body.split('\n')
        for line in lines:
            if line.startswith('**Photo ID:**'):
                photo_id = line.split(':', 1)[1].strip()
                # Remove any prefix like "** " that might be present
                if photo_id.startswith('** '):
                    photo_id = photo_id[3:]
                elif photo_id.startswith('**'):
                    photo_id = photo_id[2:].strip()
                
                # Return only if we have a valid ID
                if photo_id:
                    return photo_id
        return None
    
    def _extract_album_id(self, issue_body: str) -> Optional[str]:
        """Extract album ID from issue body."""
        if not issue_body:
            return None
            
        lines = issue_body.split('\n')
        for line in lines:
            if line.startswith('**Album ID:**'):
                album_id = line.split(':', 1)[1].strip()
                if album_id:
                    return album_id
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
    
    def get_posted_photo_ids(self) -> List[str]:
        """Get list of photo IDs that have already been posted successfully from the current album."""
        try:
            issues = self.repo.get_issues(
                state='all',
                labels=['automated-post', 'instagram', 'flickr-album', 'posted']
            )
            
            posted_ids = []
            for issue in issues:
                # Only include photos from the current album
                if self._is_from_current_album(issue.body, issue.number):
                    photo_id = self._extract_photo_id(issue.body)
                    if photo_id and photo_id not in posted_ids:  # Avoid duplicates
                        posted_ids.append(photo_id)
                        self.logger.debug(f"Found posted photo ID: {photo_id} from issue #{issue.number} (current album)")
            
            self.logger.info(f"Found {len(posted_ids)} successfully posted photos from current album: {posted_ids}")
            return posted_ids
            
        except Exception as e:
            self.logger.error(f"Failed to get posted photo IDs: {e}")
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
                    if photo_id and photo_id not in dry_run_ids:
                        dry_run_ids.append(photo_id)
                        self.logger.debug(f"Found dry run photo ID: {photo_id} from issue #{issue.number} (current album)")
            
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
                    if photo_id and photo_id not in failed_ids:
                        failed_ids.append(photo_id)
                        self.logger.debug(f"Found failed photo ID: {photo_id} from issue #{issue.number} (current album)")
            
            self.logger.info(f"Found {len(failed_ids)} failed photos from current album: {failed_ids}")
            return failed_ids
            
        except Exception as e:
            self.logger.error(f"Failed to get failed photo IDs: {e}")
            return []
    
    def create_post_record(self, photo_data: Dict, instagram_post_id: Optional[str] = None, is_dry_run: bool = False) -> Optional[str]:
        """Create a GitHub issue to record the posted photo."""
        try:
            timestamp = datetime.now().isoformat()
            position = photo_data.get('album_position', 'unknown')
            
            if is_dry_run:
                title = f"Dry Run: {photo_data['title']} (#{position}) - {timestamp}"
            else:
                title = f"Posted: {photo_data['title']} (#{position}) - {timestamp}"
            
            body_parts = [
                f"**Photo ID:** {photo_data['id']}",
                f"**Album ID:** {self.current_album_id}",
                f"**Album Position:** {position}",
                f"**Title:** {photo_data['title']}",
                f"**Description:** {photo_data.get('description', 'N/A')}",
                f"**Image URL:** {photo_data['url']}",
                f"**Posted At:** {timestamp}",
            ]
            
            if instagram_post_id:
                body_parts.append(f"**Instagram Post ID:** {instagram_post_id}")
            elif is_dry_run:
                body_parts.append(f"**Status:** Dry run - not actually posted")
            
            body = '\n'.join(body_parts)
            
            if is_dry_run:
                labels = [
                    'automated-post',
                    'dry-run',
                    'flickr-album'
                ]
            else:
                labels = [
                    'automated-post',
                    'instagram',
                    'flickr-album',
                    'posted' if instagram_post_id else 'failed'
                ]
            
            issue = self.repo.create_issue(
                title=title,
                body=body,
                labels=labels
            )
            
            run_type = "dry run" if is_dry_run else "post"
            self.logger.info(f"Created {run_type} issue #{issue.number} for photo {photo_data['id']} (position {position})")
            return str(issue.number)
            
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
        """Get the next photo that hasn't been posted yet, respecting album order."""
        posted_ids = self.get_posted_photo_ids()
        failed_ids = self.get_failed_photo_ids()
        excluded_ids = posted_ids.copy()
        excluded_ids.extend(failed_ids)
        
        # Optionally include dry run selections in exclusion list
        if include_dry_runs:
            dry_run_ids = self.get_dry_run_photo_ids()
            excluded_ids.extend(dry_run_ids)
            self.logger.info(f"Including {len(dry_run_ids)} dry run selections in exclusion list")
        
        self.logger.info(f"Excluding {len(posted_ids)} posted photos and {len(failed_ids)} failed photos")
        
        # Sort photos by their album position to ensure correct order
        sorted_photos = sorted(photos, key=lambda x: x.get('album_position', 0))
        
        self.logger.info(f"Checking {len(sorted_photos)} photos against {len(excluded_ids)} excluded IDs")
        self.logger.debug(f"Excluded IDs: {excluded_ids}")
        
        for photo in sorted_photos:
            photo_id = str(photo['id'])  # Ensure photo ID is string for comparison
            position = photo.get('album_position', 'unknown')
            
            # Check if this photo ID is in the excluded list
            is_excluded = photo_id in excluded_ids
            self.logger.debug(f"Checking photo {photo_id} (position {position}): {'EXCLUDED' if is_excluded else 'AVAILABLE'}")
            
            if not is_excluded:
                self.logger.info(f"Next photo to post: {photo_id} - {photo['title']} (position {position} in album)")
                return photo
        
        self.logger.info("No unposted photos found - all photos have been posted or selected!")
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
    
    def log_automation_run(self, success: bool, details: str = "") -> None:
        """Log an automation run."""
        try:
            timestamp = datetime.now().isoformat()
            status = "SUCCESS" if success else "FAILED"
            
            title = f"Automation Run: {status} ({timestamp})"
            
            body_parts = [
                f"**Status:** {status}",
                f"**Timestamp:** {timestamp}",
                f"**Details:** {details}",
            ]
            
            body = '\n'.join(body_parts)
            
            labels = [
                'automation-log',
                'flickr-album',
                'success' if success else 'failure'
            ]
            
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
        """Check if all photos in the album have been processed (posted or failed)."""
        posted_count = len(self.get_posted_photo_ids())
        failed_count = len(self.get_failed_photo_ids())
        processed_count = posted_count + failed_count
        is_complete = processed_count >= total_photos
        
        if is_complete:
            self.logger.info(f"Album complete! Processed {processed_count} of {total_photos} photos ({posted_count} posted, {failed_count} failed)")
        else:
            remaining = total_photos - processed_count
            self.logger.info(f"Album progress: {processed_count} of {total_photos} photos processed ({posted_count} posted, {failed_count} failed, {remaining} remaining)")
        
        return is_complete