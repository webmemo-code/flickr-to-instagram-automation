#!/usr/bin/env python3
"""
Create a manual verification checklist for Instagram posts.
This script generates a list of posts that you can manually verify on Instagram.
"""
import subprocess
import json
from collections import defaultdict
from datetime import datetime

def run_gh_command(cmd):
    """Run a GitHub CLI command and return the result."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            print(f"Error: {result.stderr}")
            return None
    except Exception as e:
        print(f"Exception: {e}")
        return None

def extract_photo_id(issue_body):
    """Extract photo ID from issue body."""
    lines = issue_body.split('\n')
    for line in lines:
        if line.startswith('**Photo ID:**'):
            return line.split('**Photo ID:**')[1].strip()
    return None

def extract_instagram_post_id(issue_body):
    """Extract Instagram post ID from issue body."""
    lines = issue_body.split('\n')
    for line in lines:
        if line.startswith('**Instagram Post ID:**'):
            return line.split('**Instagram Post ID:**')[1].strip()
    return None

def extract_title(issue_body):
    """Extract photo title from issue body."""
    lines = issue_body.split('\n')
    for line in lines:
        if line.startswith('**Title:**'):
            return line.split('**Title:**')[1].strip()
    return None

def main():
    print("=== 📋 Manual Instagram Verification Checklist ===\n")
    
    repo = "webmemo-code/flickr-to-instagram-automation"
    
    # Get all posted issues
    cmd = f'gh issue list --repo {repo} --label "automated-post,instagram,flickr-album,posted" --state all --json number,title,body,createdAt --limit 100'
    output = run_gh_command(cmd)
    
    if not output:
        print("❌ Failed to get GitHub Issues")
        return
    
    try:
        issues = json.loads(output)
    except json.JSONDecodeError:
        print("❌ Failed to parse GitHub Issues JSON")
        return
    
    # Group by photo ID to handle duplicates
    photo_posts = {}
    
    for issue in issues:
        photo_id = extract_photo_id(issue['body'])
        instagram_post_id = extract_instagram_post_id(issue['body'])
        title = extract_title(issue['body']) or issue['title']
        
        if photo_id and instagram_post_id:
            if photo_id not in photo_posts or issue['createdAt'] > photo_posts[photo_id]['created_at']:
                photo_posts[photo_id] = {
                    'instagram_post_id': instagram_post_id,
                    'issue_number': issue['number'],
                    'title': title,
                    'created_at': issue['createdAt'],
                    'flickr_url': f"https://flickr.com/photos/schaerer/{photo_id}"
                }
    
    # Sort by creation date (oldest first)
    sorted_posts = sorted(photo_posts.items(), key=lambda x: x[1]['created_at'])
    
    print(f"📊 Found {len(photo_posts)} unique posts to verify\n")
    print("🔍 **MANUAL VERIFICATION CHECKLIST**")
    print("=" * 80)
    print("Go to your Instagram account and check if these posts are visible:")
    print()
    
    for i, (photo_id, post_info) in enumerate(sorted_posts, 1):
        instagram_post_id = post_info['instagram_post_id']
        issue_number = post_info['issue_number']
        title = post_info['title'][:60]
        created_date = datetime.fromisoformat(post_info['created_at'].replace('Z', '+00:00')).strftime('%Y-%m-%d')
        
        print(f"{i:2}. 📸 Issue #{issue_number} | Photo {photo_id}")
        print(f"    📅 Posted: {created_date}")
        print(f"    📝 Title: {title}...")
        print(f"    🔗 Flickr: {post_info['flickr_url']}")
        print(f"    📱 Instagram Post ID: {instagram_post_id}")
        print(f"    ✅ Verify: Check if this post exists on your Instagram")
        print()
    
    print("=" * 80)
    print("📋 **INSTRUCTIONS:**")
    print("1. Go to your Instagram account (web or app)")
    print("2. For each post above, try to find it in your feed")
    print("3. You can search by the title or date")
    print("4. Count how many posts are actually visible")
    print("5. If a post is missing, note its Issue number")
    print()
    
    print("💡 **WHAT TO LOOK FOR:**")
    print("- Posts that were deleted by Instagram")
    print("- Posts that failed to upload but were marked as 'posted'")
    print("- Posts that are hidden or restricted")
    print()
    
    print("🔧 **AFTER VERIFICATION:**")
    print("- If you find posts that are missing from Instagram,")
    print("  I can help you re-label those GitHub Issues from 'posted' to 'failed'")
    print("- This will allow the automation to continue with the remaining photos")
    
    print(f"\n📊 **EXPECTED RESULTS:**")
    print(f"- If you find exactly 9 posts visible → 12 issues need re-labeling")
    print(f"- If you find a different number → we'll adjust accordingly")
    print(f"- Current GitHub count: {len(photo_posts)} unique posts marked as 'posted'")

if __name__ == "__main__":
    main()
