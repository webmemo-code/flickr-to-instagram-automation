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
    
    def get_posted_photo_ids(self) -> List[str]:
        """Get list of photo IDs that have already been posted."""
        try:
            issues = self.repo.get_issues(
                state='all',
                labels=['automated-post', 'instagram', 'flickr-album']
            )
            
            posted_ids = []
            for issue in issues:
                # Extract photo ID from issue body
                if issue.body:
                    lines = issue.body.split('\n')
                    for line in lines:
                        if line.startswith('**Photo ID:**'):
                            photo_id = line.split(':', 1)[1].strip()
                            if photo_id and photo_id not in posted_ids:  # Avoid duplicates and empty IDs
                                posted_ids.append(photo_id)
                                self.logger.debug(f"Found posted photo ID: {photo_id} from issue #{issue.number}")
                            break
            
            self.logger.info(f"Found {len(posted_ids)} already posted photos: {posted_ids}")
            return posted_ids
            
        except Exception as e:
            self.logger.error(f"Failed to get posted photo IDs: {e}")
            return []
    
    def create_post_record(self, photo_data: Dict, instagram_post_id: Optional[str] = None) -> Optional[str]:
        """Create a GitHub issue to record the posted photo."""
        try:
            timestamp = datetime.now().isoformat()
            position = photo_data.get('album_position', 'unknown')
            
            title = f"Posted: {photo_data['title']} (#{position}) - {timestamp}"
            
            body_parts = [
                f"**Photo ID:** {photo_data['id']}",
                f"**Album Position:** {position}",
                f"**Title:** {photo_data['title']}",
                f"**Description:** {photo_data.get('description', 'N/A')}",
                f"**Image URL:** {photo_data['url']}",
                f"**Posted At:** {timestamp}",
            ]
            
            if instagram_post_id:
                body_parts.append(f"**Instagram Post ID:** {instagram_post_id}")
            
            body = '\n'.join(body_parts)
            
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
            
            self.logger.info(f"Created issue #{issue.number} for photo {photo_data['id']} (position {position})")
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
    
    def get_next_photo_to_post(self, photos: List[Dict]) -> Optional[Dict]:
        """Get the next photo that hasn't been posted yet, respecting album order."""
        posted_ids = self.get_posted_photo_ids()
        
        # Sort photos by their album position to ensure correct order
        sorted_photos = sorted(photos, key=lambda x: x.get('album_position', 0))
        
        self.logger.info(f"Checking {len(sorted_photos)} photos against {len(posted_ids)} posted IDs")
        self.logger.debug(f"Posted IDs: {posted_ids}")
        
        for photo in sorted_photos:
            photo_id = photo['id']
            position = photo.get('album_position', 'unknown')
            
            self.logger.debug(f"Checking photo {photo_id} (position {position}): {'POSTED' if photo_id in posted_ids else 'UNPOSTED'}")
            
            if photo_id not in posted_ids:
                self.logger.info(f"Next photo to post: {photo_id} - {photo['title']} (position {position} in album)")
                return photo
        
        self.logger.info("No unposted photos found - all photos have been posted!")
        return None
    
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
        """Check if all photos in the album have been posted."""
        posted_count = len(self.get_posted_photo_ids())
        is_complete = posted_count >= total_photos
        
        if is_complete:
            self.logger.info(f"Album complete! Posted {posted_count} of {total_photos} photos")
        else:
            self.logger.info(f"Album progress: {posted_count} of {total_photos} photos posted")
        
        return is_complete