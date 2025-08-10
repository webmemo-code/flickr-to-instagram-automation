#!/usr/bin/env python3
"""
Complete analysis of album status to determine actual counts.
"""
import subprocess
import json
from collections import defaultdict

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

def main():
    print("=== 📊 Complete Album Status Analysis ===\n")
    
    repo = "webmemo-code/flickr-to-instagram-automation"
    
    # Get posted issues
    cmd_posted = f'gh issue list --repo {repo} --label "automated-post,instagram,flickr-album,posted" --state all --json number,title,body --limit 100'
    posted_output = run_gh_command(cmd_posted)
    
    # Get failed issues  
    cmd_failed = f'gh issue list --repo {repo} --label "automated-post,instagram,flickr-album,failed" --state all --json number,title,body --limit 100'
    failed_output = run_gh_command(cmd_failed)
    
    if not posted_output or not failed_output:
        print("❌ Failed to get issues")
        return
    
    try:
        posted_issues = json.loads(posted_output)
        failed_issues = json.loads(failed_output)
    except json.JSONDecodeError:
        print("❌ Failed to parse issues JSON")
        return
    
    # Get unique posted photo IDs
    posted_photos = set()
    for issue in posted_issues:
        photo_id = extract_photo_id(issue['body'])
        if photo_id:
            posted_photos.add(photo_id)
    
    # Get unique failed photo IDs
    failed_photos = set()
    for issue in failed_issues:
        photo_id = extract_photo_id(issue['body'])
        if photo_id:
            failed_photos.add(photo_id)
    
    # Calculate totals
    total_album_photos = 31  # From the statistics
    processed_photos = len(posted_photos) + len(failed_photos)
    remaining_photos = total_album_photos - processed_photos
    
    print("📊 **ACTUAL ALBUM STATUS:**")
    print("=" * 50)
    print(f"📁 Total photos in album: {total_album_photos}")
    print(f"✅ Successfully posted: {len(posted_photos)}")
    print(f"❌ Failed photos: {len(failed_photos)}")
    print(f"📝 Total processed: {processed_photos}")
    print(f"⏳ Remaining to post: {remaining_photos}")
    print(f"📈 Completion rate: {(processed_photos/total_album_photos)*100:.1f}%")
    
    print(f"\n🔍 **DETAILED BREAKDOWN:**")
    print(f"Posted photo IDs ({len(posted_photos)}): {sorted(list(posted_photos))}")
    print(f"Failed photo IDs ({len(failed_photos)}): {sorted(list(failed_photos))}")
    
    # Check for overlap (shouldn't happen)
    overlap = posted_photos.intersection(failed_photos)
    if overlap:
        print(f"⚠️  PROBLEM: Photos marked as both posted AND failed: {overlap}")
    else:
        print("✅ No overlap between posted and failed photos")
        
    print(f"\n🎯 **SUMMARY:**")
    if remaining_photos == 0:
        print("🎉 Album is COMPLETE! All photos have been processed.")
    else:
        print(f"📝 Album is NOT complete. {remaining_photos} photos remaining to be posted.")
        print(f"   The system should continue posting until all {total_album_photos} photos are processed.")

if __name__ == "__main__":
    main()
