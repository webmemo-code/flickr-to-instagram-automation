#!/usr/bin/env python3
"""
Quick identification script for missing Instagram posts
"""
import subprocess
import json

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

def extract_instagram_post_id(issue_body):
    """Extract Instagram post ID from issue body."""
    lines = issue_body.split('\n')
    for line in lines:
        if line.startswith('**Instagram Post ID:**'):
            return line.split('**Instagram Post ID:**')[1].strip()
    return None

def main():
    print("=== 🔍 POSTED ISSUES VERIFICATION ===")
    print("These 23 issues are currently labeled as 'posted'")
    print("You say only 9 are actually visible on Instagram")
    print("Please identify which ones are MISSING:\n")
    
    repo = "webmemo-code/flickr-to-instagram-automation"
    
    # Get all posted issues
    cmd = f'gh issue list --repo {repo} --label "automated-post,instagram,flickr-album,posted" --state all --json number,title,body --limit 50'
    output = run_gh_command(cmd)
    
    if not output:
        print("❌ Failed to fetch issues")
        return
    
    issues = json.loads(output)
    
    print(f"Found {len(issues)} issues labeled as 'posted':\n")
    
    missing_issues = []
    
    for i, issue in enumerate(issues, 1):
        instagram_post_id = extract_instagram_post_id(issue['body'])
        
        if instagram_post_id:
            instagram_link = f"https://www.instagram.com/p/{instagram_post_id.split('/')[-1]}" if '/' in instagram_post_id else f"https://www.instagram.com/p/UNKNOWN/"
            # Try to construct proper Instagram link from post ID
            # Instagram post IDs are typically numeric, but the URL uses a different format
            print(f"{i:2d}. Issue #{issue['number']} - {issue['title'][:60]}...")
            print(f"    📱 Post ID: {instagram_post_id}")
            print(f"    🔗 Check: Go to your Instagram and search for this post")
            print(f"    Status: [ ] ✅ Visible  [ ] ❌ Missing")
            print()
        else:
            print(f"{i:2d}. Issue #{issue['number']} - {issue['title'][:60]}...")
            print(f"    ⚠️  No Instagram Post ID found in issue body")
            print()
    
    print("=" * 70)
    print("📝 INSTRUCTIONS:")
    print("1. Check your Instagram account manually")
    print("2. Count how many of these posts are actually visible")
    print("3. Tell me the Issue numbers that are MISSING")
    print("4. I'll re-label those from 'posted' to 'failed'")
    print()
    print("💡 Expected: You should find ~14 missing posts")
    print("   (since you see 9 posts but 23 are marked as posted)")

if __name__ == "__main__":
    main()
