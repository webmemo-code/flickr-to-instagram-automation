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
        
        # Get all automation-related issues
        all_issues = repo.get_issues(
            state='all',
            labels=['automated-post']
        )
        
        total_issues = all_issues.totalCount
        logger.info(f"Found {total_issues} automation-related issues")
        
        # Categories for cleanup
        close_categories = {
            'dry_runs': [],
            'automation_logs': [],
            'failed_posts': []
        }
        keep_categories = {
            'successful_posts': []
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
                keep_categories['successful_posts'].append(issue)
            else:
                logger.warning(f"Uncategorized issue #{issue.number}: {issue.title}")
        
        # Report categorization
        logger.info("\n=== Issue Categorization ===")
        logger.info(f"Dry Run Issues (will close): {len(close_categories['dry_runs'])}")
        logger.info(f"Automation Log Issues (will close): {len(close_categories['automation_logs'])}")
        logger.info(f"Failed Post Issues (will close): {len(close_categories['failed_posts'])}")
        logger.info(f"Successful Post Issues (will keep): {len(keep_categories['successful_posts'])}")
        
        total_to_close = sum(len(issues) for issues in close_categories.values())
        total_to_keep = len(keep_categories['successful_posts'])
        
        logger.info(f"\nSUMMARY: Will close {total_to_close} issues, keep {total_to_keep} issues")
        
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
- Only creates issues for successful posts (audit trail)
- Eliminates repository pollution from temporary records

This change improves performance and repository organization while maintaining all necessary audit trails.
"""
                        
                        issue.create_comment(comment_text)
                        issue.edit(state='closed')
                        closed_count += 1
                        
                        logger.debug(f"Closed issue #{issue.number}: {issue.title}")
                        
                    except Exception as e:
                        logger.error(f"Failed to close issue #{issue.number}: {e}")
            
            logger.info(f"\n✅ Successfully closed {closed_count} legacy issues")
            logger.info(f"✅ Preserved {total_to_keep} successful post issues for audit trail")
            
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