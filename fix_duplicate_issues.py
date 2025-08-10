#!/usr/bin/env python3
"""
Script to identify and optionally fix duplicate GitHub Issues for posted photos.
"""
import subprocess
import json
import sys
from collections import defaultdict

def run_gh_command(cmd):
    """Run a GitHub CLI command and return the result."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            print(f"Error running command: {cmd}")
            print(f"Error: {result.stderr}")
            return None
    except Exception as e:
        print(f"Exception running command: {e}")
        return None

def extract_photo_id(issue_body):
    """Extract photo ID from issue body."""
    lines = issue_body.split('\n')
    for line in lines:
        if line.startswith('**Photo ID:**'):
            return line.split('**Photo ID:**')[1].strip()
    return None

def main():
    """Analyze duplicate posted photos."""
    print("=== 🔍 Duplicate Posted Photos Analysis ===\n")
    
    repo = "webmemo-code/flickr-to-instagram-automation"
    
    # Get all posted issues
    cmd = f'gh issue list --repo {repo} --label "automated-post,instagram,flickr-album,posted" --state all --json number,title,body,createdAt --limit 100'
    output = run_gh_command(cmd)
    
    if not output:
        print("❌ Failed to get issues")
        return
    
    try:
        issues = json.loads(output)
    except json.JSONDecodeError:
        print("❌ Failed to parse issues JSON")
        return
    
    # Group issues by photo ID
    photo_issues = defaultdict(list)
    
    for issue in issues:
        photo_id = extract_photo_id(issue['body'])
        if photo_id:
            photo_issues[photo_id].append({
                'number': issue['number'],
                'title': issue['title'],
                'created_at': issue['createdAt']
            })
    
    # Analyze duplicates
    unique_photos = 0
    duplicate_photos = 0
    total_duplicate_issues = 0
    
    print("📊 Analysis Results:")
    print("=" * 50)
    
    for photo_id, issue_list in photo_issues.items():
        if len(issue_list) == 1:
            unique_photos += 1
        else:
            duplicate_photos += 1
            total_duplicate_issues += len(issue_list) - 1
            print(f"🔄 Photo {photo_id} has {len(issue_list)} issues:")
            for issue_info in sorted(issue_list, key=lambda x: x['created_at']):
                print(f"   #{issue_info['number']}: {issue_info['title'][:60]}... ({issue_info['created_at']})")
            print()
    
    print("=" * 50)
    print(f"✅ Unique posted photos: {unique_photos}")
    print(f"🔄 Photos with duplicates: {duplicate_photos}")
    print(f"📝 Total duplicate issues: {total_duplicate_issues}")
    print(f"📊 Total posted issues: {len(issues)}")
    print(f"🎯 Actual successfully posted photos: {len(photo_issues)}")
    
    # Show the correction needed
    print(f"\n🔧 **CORRECTION NEEDED:**")
    print(f"   Current system count: {len(issues)} (WRONG)")
    print(f"   Actual unique photos posted: {len(photo_issues)} (CORRECT)")
    print(f"   Remaining photos to post: {31 - len(photo_issues)}")

if __name__ == "__main__":
    main()
