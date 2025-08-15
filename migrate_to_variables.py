#!/usr/bin/env python3
"""
Migration script to populate GitHub Repository Variables from existing GitHub Issues.
This script reads the current posting state from GitHub Issues and initializes
the Repository Variables system for scalable state management.
"""
import os
import sys
import json
import logging
from datetime import datetime
from typing import Dict, List, Set
from github import Github
from config import Config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class StateMigrator:
    """Migrate state from GitHub Issues to Repository Variables."""
    
    def __init__(self, config: Config, repo_name: str):
        self.config = config
        self.github = Github(config.github_token)
        self.repo = self.github.get_repo(repo_name)
        self.current_album_id = config.flickr_album_id
        
    def _extract_photo_id(self, issue_body: str) -> str:
        """Extract photo ID from issue body."""
        if not issue_body:
            return None
            
        lines = issue_body.split('\n')
        for line in lines:
            if line.startswith('**Photo ID:**'):
                photo_id = line.split(':', 1)[1].strip()
                
                # Clean up markdown formatting
                while photo_id.startswith('**'):
                    photo_id = photo_id[2:].strip()
                while photo_id.startswith('*'):
                    photo_id = photo_id[1:].strip()
                while photo_id.endswith('**'):
                    photo_id = photo_id[:-2].strip()
                while photo_id.endswith('*'):
                    photo_id = photo_id[:-1].strip()
                
                if photo_id:
                    return str(photo_id).strip()
        return None
    
    def _extract_album_id(self, issue_body: str) -> str:
        """Extract album ID from issue body."""
        if not issue_body:
            return None
            
        lines = issue_body.split('\n')
        for line in lines:
            if line.startswith('**Album ID:**'):
                album_id = line.split(':', 1)[1].strip()
                
                # Clean up markdown formatting
                while album_id.startswith('**'):
                    album_id = album_id[2:].strip()
                while album_id.startswith('*'):
                    album_id = album_id[1:].strip()
                while album_id.endswith('**'):
                    album_id = album_id[:-2].strip()
                while album_id.endswith('*'):
                    album_id = album_id[:-1].strip()
                
                if album_id:
                    return str(album_id).strip()
        return None
    
    def _extract_album_position(self, issue_body: str) -> int:
        """Extract album position from issue body."""
        if not issue_body:
            return None
            
        lines = issue_body.split('\n')
        for line in lines:
            if line.startswith('**Album Position:**'):
                position_str = line.split(':', 1)[1].strip()
                
                # Clean up markdown formatting
                while position_str.startswith('**'):
                    position_str = position_str[2:].strip()
                while position_str.startswith('*'):
                    position_str = position_str[1:].strip()
                while position_str.endswith('**'):
                    position_str = position_str[:-2].strip()
                while position_str.endswith('*'):
                    position_str = position_str[:-1].strip()
                
                try:
                    return int(position_str)
                except ValueError:
                    return None
        return None
    
    def _extract_instagram_post_id(self, issue_body: str) -> str:
        """Extract Instagram post ID from issue body."""
        if not issue_body:
            return None
            
        lines = issue_body.split('\n')
        for line in lines:
            if line.startswith('**Instagram Post ID:**'):
                post_id = line.split(':', 1)[1].strip()
                
                # Clean up markdown formatting
                while post_id.startswith('**'):
                    post_id = post_id[2:].strip()
                while post_id.startswith('*'):
                    post_id = post_id[1:].strip()
                while post_id.endswith('**'):
                    post_id = post_id[:-2].strip()
                while post_id.endswith('*'):
                    post_id = post_id[:-1].strip()
                
                if post_id:
                    return str(post_id).strip()
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
        if album_id is None and issue_number is not None:
            return issue_number >= 65
        
        # Default fallback: assume it's from current album
        return True
    
    def _set_variable(self, name: str, value: str) -> bool:
        """Set a repository variable value."""
        try:
            # Try to update existing variable
            try:
                variable = self.repo.get_variable(name)
                variable.edit(value)
                logger.info(f"Updated variable {name} = {value}")
                return True
            except Exception:
                # Variable doesn't exist, create it
                self.repo.create_variable(name, value)
                logger.info(f"Created variable {name} = {value}")
                return True
        except Exception as e:
            logger.error(f"Failed to set variable {name}: {e}")
            return False
    
    def analyze_existing_issues(self) -> Dict:
        """Analyze existing GitHub Issues to extract posting state."""
        logger.info("Analyzing existing GitHub Issues for posting state...")
        
        # Get all automation-related issues
        issues = self.repo.get_issues(
            state='all',
            labels=['automated-post', 'flickr-album']
        )
        
        posted_positions = set()
        failed_positions = set()
        instagram_posts = []
        max_position = 0
        
        logger.info(f"Found {issues.totalCount} automation issues to analyze")
        
        for issue in issues:
            # Only analyze issues from current album
            if not self._is_from_current_album(issue.body, issue.number):
                logger.debug(f"Issue #{issue.number}: Not from current album, skipping")
                continue
                
            photo_id = self._extract_photo_id(issue.body)
            album_position = self._extract_album_position(issue.body)
            instagram_post_id = self._extract_instagram_post_id(issue.body)
            
            if not photo_id:
                logger.debug(f"Issue #{issue.number}: No photo ID found, skipping")
                continue
                
            # Use album position if available, otherwise skip
            if album_position is None:
                logger.warning(f"Issue #{issue.number}: No album position found, skipping")
                continue
                
            max_position = max(max_position, album_position)
            
            # Check issue labels to determine status
            labels = [label.name for label in issue.labels]
            
            if 'posted' in labels and instagram_post_id:
                # Successfully posted
                posted_positions.add(album_position)
                instagram_posts.append({
                    "position": album_position,
                    "photo_id": photo_id,
                    "instagram_post_id": instagram_post_id,
                    "posted_at": issue.created_at.isoformat(),
                    "title": issue.title.replace("Posted: ", "").split(" (")[0],
                    "issue_number": issue.number
                })
                logger.info(f"Issue #{issue.number}: Posted photo #{album_position} -> {instagram_post_id}")
                
            elif 'failed' in labels:
                # Failed to post
                failed_positions.add(album_position)
                logger.info(f"Issue #{issue.number}: Failed photo #{album_position}")
                
            elif 'dry-run' in labels:
                # Dry run - don't count as posted
                logger.debug(f"Issue #{issue.number}: Dry run photo #{album_position}")
        
        # Calculate last posted position (highest successfully posted position)
        last_posted_position = max(posted_positions) if posted_positions else 0
        
        analysis = {
            'last_posted_position': last_posted_position,
            'posted_positions': sorted(posted_positions),
            'failed_positions': sorted(failed_positions),
            'instagram_posts': sorted(instagram_posts, key=lambda x: x['position']),
            'max_position_seen': max_position,
            'total_issues_analyzed': issues.totalCount
        }
        
        logger.info(f"Analysis complete:")
        logger.info(f"  Last posted position: {last_posted_position}")
        logger.info(f"  Posted positions: {len(posted_positions)} photos")
        logger.info(f"  Failed positions: {len(failed_positions)} photos")
        logger.info(f"  Instagram posts recorded: {len(instagram_posts)}")
        
        return analysis
    
    def migrate_to_repository_variables(self, analysis: Dict) -> bool:
        """Migrate analyzed state to Repository Variables."""
        logger.info("Migrating state to Repository Variables...")
        
        success = True
        
        # Set last posted position
        var_name = f"LAST_POSTED_POSITION_{self.current_album_id}"
        if not self._set_variable(var_name, str(analysis['last_posted_position'])):
            success = False
            
        # Set failed positions
        var_name = f"FAILED_POSITIONS_{self.current_album_id}"
        failed_json = json.dumps(list(analysis['failed_positions']))
        if not self._set_variable(var_name, failed_json):
            success = False
            
        # Set Instagram posts
        var_name = f"INSTAGRAM_POSTS_{self.current_album_id}"
        posts_json = json.dumps(analysis['instagram_posts'])
        if not self._set_variable(var_name, posts_json):
            success = False
            
        # We'll set total album photos when we get the actual count from Flickr
        # For now, use the max position we've seen as a baseline
        var_name = f"TOTAL_ALBUM_PHOTOS_{self.current_album_id}"
        if not self._set_variable(var_name, str(analysis['max_position_seen'])):
            success = False
        
        if success:
            logger.info("✅ Migration to Repository Variables completed successfully!")
        else:
            logger.error("❌ Migration completed with some errors")
            
        return success
    
    def run_migration(self):
        """Run the complete migration process."""
        logger.info("="*60)
        logger.info("MIGRATION: GitHub Issues -> Repository Variables")
        logger.info(f"Album: {self.config.album_name} (ID: {self.current_album_id})")
        logger.info("="*60)
        
        try:
            # Analyze existing issues
            analysis = self.analyze_existing_issues()
            
            # Show summary
            logger.info("\n📊 MIGRATION SUMMARY:")
            logger.info(f"  Current album: {self.config.album_name}")
            logger.info(f"  Last posted position: {analysis['last_posted_position']}")
            logger.info(f"  Successfully posted: {len(analysis['posted_positions'])} photos")
            logger.info(f"  Failed attempts: {len(analysis['failed_positions'])} photos")
            logger.info(f"  Instagram posts to migrate: {len(analysis['instagram_posts'])}")
            
            if analysis['failed_positions']:
                logger.info(f"  Failed positions: {analysis['failed_positions']}")
            
            # Migrate to variables
            success = self.migrate_to_repository_variables(analysis)
            
            if success:
                logger.info("\n🎉 MIGRATION COMPLETE!")
                logger.info("The automation system now uses Repository Variables for state management.")
                logger.info("Next automation run will continue from the correct position.")
            else:
                logger.error("\n💥 MIGRATION FAILED!")
                logger.error("Please check the errors above and try again.")
                
            return success
            
        except Exception as e:
            logger.error(f"Migration failed with error: {e}")
            return False

def main():
    """Main migration entry point."""
    try:
        # Initialize components
        config = Config()
        
        # Get repository name from environment
        repo_name = os.getenv('GITHUB_REPOSITORY')
        if not repo_name:
            logger.error("GITHUB_REPOSITORY environment variable not set")
            logger.info("Please run this in GitHub Actions or set GITHUB_REPOSITORY manually")
            sys.exit(1)
        
        # Run migration
        migrator = StateMigrator(config, repo_name)
        success = migrator.run_migration()
        
        if success:
            logger.info("Migration completed successfully!")
            sys.exit(0)
        else:
            logger.error("Migration failed!")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Migration script failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()