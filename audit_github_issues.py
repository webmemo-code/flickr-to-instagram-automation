#!/usr/bin/env python3
"""
Script to audit GitHub Issues and identify issues that need label corrections.
"""
import os
import re
from config import Config
from state_manager import StateManager

def main():
    try:
        config = Config()
        repo_name = os.getenv('GITHUB_REPOSITORY', 'w-sch/flickr-to-instagram-python')
        state_manager = StateManager(config, repo_name)
        
        print("=== 🔍 GitHub Issues Audit ===\n")
        
        # Get all automated post issues
        issues = state_manager.repo.get_issues(
            state='all',
            labels=['automated-post', 'flickr-album']
        )
        
        posted_issues = []
        failed_issues = []
        suspicious_issues = []
        
        for issue in issues:
            if 'dry-run' in [label.name for label in issue.labels]:
                continue  # Skip dry run issues
                
            labels = [label.name for label in issue.labels]
            body = issue.body or ""
            
            # Check if it has Instagram Post ID in body
            has_instagram_id = "Instagram Post ID:" in body
            has_posted_label = 'posted' in labels
            has_failed_label = 'failed' in labels
            
            if has_posted_label and has_instagram_id:
                posted_issues.append({
                    'number': issue.number,
                    'title': issue.title,
                    'photo_id': state_manager._extract_photo_id(body),
                    'status': 'correctly_posted'
                })
            elif has_posted_label and not has_instagram_id:
                suspicious_issues.append({
                    'number': issue.number,
                    'title': issue.title,
                    'photo_id': state_manager._extract_photo_id(body),
                    'status': 'posted_without_instagram_id',
                    'issue': 'Has "posted" label but no Instagram Post ID'
                })
            elif has_failed_label:
                failed_issues.append({
                    'number': issue.number,
                    'title': issue.title,
                    'photo_id': state_manager._extract_photo_id(body),
                    'status': 'correctly_failed'
                })
            elif not has_posted_label and not has_failed_label:
                suspicious_issues.append({
                    'number': issue.number,
                    'title': issue.title,
                    'photo_id': state_manager._extract_photo_id(body),
                    'status': 'no_status_label',
                    'issue': 'Missing both "posted" and "failed" labels'
                })
        
        print(f"✅ Correctly posted issues: {len(posted_issues)}")
        print(f"❌ Correctly failed issues: {len(failed_issues)}")
        print(f"⚠️  Suspicious issues needing attention: {len(suspicious_issues)}")
        
        if suspicious_issues:
            print(f"\n🔍 Issues that need attention:")
            for issue in suspicious_issues:
                print(f"  Issue #{issue['number']}: {issue['title']}")
                print(f"    Photo ID: {issue['photo_id']}")
                print(f"    Problem: {issue['issue']}")
                print(f"    URL: https://github.com/{repo_name}/issues/{issue['number']}")
                print()
        
        print(f"\n📊 Summary:")
        print(f"  Total processed: {len(posted_issues) + len(failed_issues)}")
        print(f"  Successfully posted: {len(posted_issues)}")
        print(f"  Failed posts: {len(failed_issues)}")
        print(f"  Need manual review: {len(suspicious_issues)}")
        
        return suspicious_issues
        
    except Exception as e:
        print(f"❌ Error auditing issues: {e}")
        return []

if __name__ == "__main__":
    main()