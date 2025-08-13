#!/usr/bin/env python3
"""
Cleanup script for legacy GitHub Issues created by the old state management system.
This script will close unnecessary issues while preserving the audit trail for successfully posted photos.
"""
import os
import sys
import logging
from datetime import datetime
from github import Github


def setup_logging():
    """Setup logging for the cleanup script."""
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(console_handler)
    return logger


def cleanup_legacy_issues(dry_run=True):
    """Clean up legacy GitHub Issues created by old state management."""
    logger = logging.getLogger()
    
    # Get GitHub token and repository
    github_token = os.getenv('GITHUB_TOKEN')
    repo_name = os.getenv('GITHUB_REPOSITORY')
    
    if not github_token:
        logger.error("GITHUB_TOKEN environment variable not set")
        return False
    
    if not repo_name:
        logger.error("GITHUB_REPOSITORY environment variable not set")
        return False
    
    try:
        github = Github(github_token)
        repo = github.get_repo(repo_name)
        
        logger.info(f"Starting cleanup of legacy issues in {repo_name}")
        logger.info(f"DRY RUN: {dry_run}")
        
        # Get all issues (not just labeled ones) to find automation issues
        all_issues = repo.get_issues(state='all')
        
        # Filter for automation-related issues
        automation_issues = []
        automation_keywords = ['automated', 'flickr', 'instagram', 'dry-run', 'posted', 'failed', 'automation', 'album']
        
        for issue in all_issues:
            labels = [label.name.lower() for label in issue.labels]
            title_lower = issue.title.lower()
            
            # Check if this is an automation issue
            is_automation = (
                any(keyword in ' '.join(labels) for keyword in automation_keywords) or
                any(keyword in title_lower for keyword in automation_keywords) or
                'photo' in title_lower
            )
            
            if is_automation:
                automation_issues.append(issue)
        
        # Convert back to the format the rest of the script expects
        class MockPaginatedList:
            def __init__(self, items):
                self.items = items
                self.totalCount = len(items)
            
            def __iter__(self):
                return iter(self.items)
        
        all_issues = MockPaginatedList(automation_issues)
        
        total_issues = all_issues.totalCount
        logger.info(f"Found {total_issues} automation-related issues")
        
        # Categories for cleanup - now removing ALL automation issues
        close_categories = {
            'dry_runs': [],
            'automation_logs': [],
            'failed_posts': [],
            'successful_posts': []  # Now also removing successful posts - audit trail in variables
        }
        keep_categories = {
            'manual_issues': []  # Only keep non-automation issues
        }
        
        # Categorize issues
        for issue in all_issues:
            labels = [label.name for label in issue.labels]
            
            if 'dry-run' in labels:
                close_categories['dry_runs'].append(issue)
            elif 'automation-log' in labels:
                close_categories['automation_logs'].append(issue)
            elif 'failed' in labels and 'instagram' in labels:
                close_categories['failed_posts'].append(issue)
            elif 'posted' in labels and 'instagram' in labels:
                close_categories['successful_posts'].append(issue)  # Now also closing successful posts
            else:
                # This is likely a real project issue, keep it
                keep_categories['manual_issues'].append(issue)
                logger.debug(f"Keeping non-automation issue #{issue.number}: {issue.title}")
        
        # Report categorization
        logger.info("\n=== Issue Categorization ===")
        logger.info(f"Dry Run Issues (will close): {len(close_categories['dry_runs'])}")
        logger.info(f"Automation Log Issues (will close): {len(close_categories['automation_logs'])}")
        logger.info(f"Failed Post Issues (will close): {len(close_categories['failed_posts'])}")
        logger.info(f"Successful Post Issues (will close): {len(close_categories['successful_posts'])}")
        logger.info(f"Manual/Project Issues (will keep): {len(keep_categories['manual_issues'])}")
        
        total_to_close = sum(len(issues) for issues in close_categories.values())
        total_to_keep = len(keep_categories['manual_issues'])
        
        logger.info(f"\nSUMMARY: Will close {total_to_close} automation issues, keep {total_to_keep} project issues")
        
        if not dry_run:
            # Close unnecessary issues
            closed_count = 0
            
            for category, issues in close_categories.items():
                logger.info(f"\nClosing {len(issues)} {category} issues...")
                
                for issue in issues:
                    try:
                        # Add a comment explaining the closure
                        comment_text = f"""🧹 **Automated Cleanup**

This issue is being closed as part of the migration to a more efficient state management system using GitHub Repository Variables.

**Reason**: {category.replace('_', ' ').title()}
**Migration Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

The new system:
- Uses Repository Variables for state tracking (scales to unlimited photos)
- Stores complete audit trail in variables (INSTAGRAM_POSTS_*, LAST_POSTED_POSITION_*)
- Zero GitHub Issues created for automation (clean repository)
- Unlimited scalability without repository pollution

All Instagram post data, positions, and timestamps are preserved in repository variables for full audit trail.
"""
                        
                        issue.create_comment(comment_text)
                        issue.edit(state='closed')
                        closed_count += 1
                        
                        logger.debug(f"Closed issue #{issue.number}: {issue.title}")
                        
                    except Exception as e:
                        logger.error(f"Failed to close issue #{issue.number}: {e}")
            
            logger.info(f"\n✅ Successfully closed {closed_count} automation issues")
            logger.info(f"✅ Preserved {total_to_keep} project issues")
            logger.info(f"🏗️ Audit trail now stored in repository variables (INSTAGRAM_POSTS_*, LAST_POSTED_POSITION_*)")
            
        else:
            logger.info("\n🧪 DRY RUN - No issues were actually closed")
            logger.info("Run with --execute to perform the actual cleanup")
        
        return True
        
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        return False


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Cleanup legacy GitHub Issues')
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Actually perform the cleanup (default is dry run)'
    )
    
    args = parser.parse_args()
    
    logger = setup_logging()
    
    dry_run = not args.execute
    
    if dry_run:
        logger.info("🧪 RUNNING IN DRY RUN MODE")
        logger.info("Use --execute flag to perform actual cleanup")
    else:
        logger.info("🚀 EXECUTING CLEANUP")
    
    success = cleanup_legacy_issues(dry_run=dry_run)
    
    if success:
        logger.info("✅ Cleanup completed successfully")
        sys.exit(0)
    else:
        logger.error("❌ Cleanup failed")
        sys.exit(1)


if __name__ == "__main__":
    main()