#!/usr/bin/env python3
"""
Script to verify which photos marked as "posted" in GitHub Issues 
are actually visible on Instagram using the Instagram Graph API.
"""
import subprocess
import json
import requests
import os
from datetime import datetime
from collections import defaultdict
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

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

def extract_instagram_post_id(issue_body):
    """Extract Instagram post ID from issue body."""
    lines = issue_body.split('\n')
    for line in lines:
        if line.startswith('**Instagram Post ID:**'):
            return line.split('**Instagram Post ID:**')[1].strip()
    return None

def check_instagram_post(post_id, access_token, app_id=None):
    """Check if an Instagram post still exists and is visible."""
    try:
        url = f"https://graph.facebook.com/v18.0/{post_id}"
        params = {
            'fields': 'id,media_type,media_url,permalink,timestamp',
            'access_token': access_token
        }
        
        # Add app_id if provided
        if app_id:
            params['app_id'] = app_id
        
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            return True, response.json()
        elif response.status_code == 400:
            # Post might be deleted or not accessible
            return False, response.json()
        else:
            return None, f"HTTP {response.status_code}: {response.text}"
            
    except Exception as e:
        return None, str(e)

def get_github_secret(secret_name, repo):
    """Retrieve a GitHub repository secret using GitHub CLI."""
    try:
        # Note: GitHub CLI doesn't allow direct access to secret values for security
        # But we can check if the secret exists
        cmd = f'gh secret list --repo {repo}'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0 and secret_name in result.stdout:
            print(f"✅ Secret {secret_name} found in repository")
            return True
        else:
            print(f"❌ Secret {secret_name} not found in repository")
            return False
    except Exception as e:
        print(f"Error checking secrets: {e}")
        return False

def main():
    print("=== 📱 Instagram Post Verification ===\n")
    
    repo = "webmemo-code/flickr-to-instagram-automation"
    
    # Check if we can access environment variables or GitHub secrets
    instagram_token = os.getenv('INSTAGRAM_ACCESS_TOKEN')
    instagram_app_id = os.getenv('INSTAGRAM_APP_ID')  # Load App ID
    
    if not instagram_token:
        print("🔍 Checking for Instagram access token...")
        
        # Check if secret exists in GitHub repository
        if get_github_secret('INSTAGRAM_ACCESS_TOKEN', repo):
            print("💡 Instagram access token is available in GitHub secrets.")
            print("   However, GitHub CLI doesn't allow direct secret access for security.")
            print("   Let's proceed with manual verification instead.")
            print()
            # Continue without token for manual verification
        else:
            print("❌ Instagram access token not found in environment or GitHub secrets")
            print("💡 This script needs access to your Instagram credentials to verify posts.")
            print("   You can either:")
            print("   1. Set the INSTAGRAM_ACCESS_TOKEN environment variable")
            print("   2. Check your Instagram account manually")
            print("   3. Use the Instagram Graph API Explorer")
            return
    
    repo = "webmemo-code/flickr-to-instagram-automation"
    
    # Get all posted issues
    print("📥 Fetching GitHub Issues marked as 'posted'...")
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
    
    print(f"📋 Found {len(issues)} GitHub Issues marked as 'posted'\n")
    
    # Group by photo ID and get unique posts
    photo_posts = {}
    duplicates_found = 0
    
    for issue in issues:
        photo_id = extract_photo_id(issue['body'])
        instagram_post_id = extract_instagram_post_id(issue['body'])
        
        if photo_id and instagram_post_id:
            if photo_id in photo_posts:
                duplicates_found += 1
                print(f"🔄 Duplicate found for photo {photo_id} (keeping latest)")
                # Keep the one with the latest creation date
                if issue['createdAt'] > photo_posts[photo_id]['created_at']:
                    photo_posts[photo_id] = {
                        'instagram_post_id': instagram_post_id,
                        'issue_number': issue['number'],
                        'title': issue['title'],
                        'created_at': issue['createdAt']
                    }
            else:
                photo_posts[photo_id] = {
                    'instagram_post_id': instagram_post_id,
                    'issue_number': issue['number'], 
                    'title': issue['title'],
                    'created_at': issue['createdAt']
                }
    
    print(f"📊 Analysis:")
    print(f"   Total GitHub Issues: {len(issues)}")
    print(f"   Duplicate issues found: {duplicates_found}")
    print(f"   Unique photos to verify: {len(photo_posts)}")
    print()
    
    # Verify each Instagram post
    print("🔍 Verifying Instagram posts...")
    print("=" * 70)
    
    verified_posts = 0
    missing_posts = 0
    error_posts = 0
    
    for photo_id, post_info in photo_posts.items():
        instagram_post_id = post_info['instagram_post_id']
        issue_number = post_info['issue_number']
        
        print(f"📸 Photo {photo_id} (Issue #{issue_number}):")
        print(f"   Instagram Post ID: {instagram_post_id}")
        
        exists, result = check_instagram_post(instagram_post_id, instagram_token, instagram_app_id)
        
        if exists is True:
            verified_posts += 1
            print(f"   ✅ VERIFIED - Post exists and is visible")
            if isinstance(result, dict) and 'permalink' in result:
                print(f"   🔗 Link: {result['permalink']}")
        elif exists is False:
            missing_posts += 1
            print(f"   ❌ MISSING - Post not found or not accessible")
            print(f"      This post should be re-labeled as 'failed'")
        else:
            error_posts += 1
            print(f"   ⚠️  ERROR - Unable to verify: {result}")
        
        print()
    
    # Final summary
    print("=" * 70)
    print("📊 **VERIFICATION SUMMARY:**")
    print(f"✅ Verified posts (actually on Instagram): {verified_posts}")
    print(f"❌ Missing posts (marked as posted but not found): {missing_posts}")
    print(f"⚠️  Error checking posts: {error_posts}")
    print(f"📝 Total posts checked: {len(photo_posts)}")
    
    if missing_posts > 0:
        remaining_to_post = 31 - verified_posts - 10  # 10 is the failed count
        print(f"\n🔧 **CORRECTION NEEDED:**")
        print(f"   Actual successfully posted photos: {verified_posts}")
        print(f"   Photos to re-label as 'failed': {missing_posts}")
        print(f"   Estimated remaining photos to post: {remaining_to_post}")
        
        print(f"\n💡 **RECOMMENDED ACTION:**")
        print(f"   The {missing_posts} missing posts should be re-labeled from 'posted' to 'failed'")
        print(f"   This will allow the automation to continue posting the remaining photos.")
    else:
        print(f"\n🎉 All posts marked as 'posted' are actually visible on Instagram!")

if __name__ == "__main__":
    main()
