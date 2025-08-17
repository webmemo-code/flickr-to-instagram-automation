#!/usr/bin/env python3
"""
Simple script to check current album state using Python GitHub API.
"""
import os
from config import Config
from state_manager import StateManager
from flickr_api import FlickrAPI

def main():
    try:
        # Initialize components
        config = Config()
        
        # Get repository name from environment or use default
        repo_name = os.getenv('GITHUB_REPOSITORY', 'w-sch/flickr-to-instagram-python')
        
        state_manager = StateManager(config, repo_name)
        flickr_api = FlickrAPI(config)
        
        print("=== 🔍 Album State Check ===\n")
        
        # Get all photos from Flickr
        photos = flickr_api.get_unposted_photos()
        total_photos = len(photos) if photos else 0
        print(f"📁 Total photos in album: {total_photos}")
        
        # Get posted photo IDs
        posted_ids = state_manager.get_posted_photo_ids()
        posted_count = len(posted_ids)
        print(f"✅ Successfully posted photos: {posted_count}")
        
        # Get failed photo IDs
        failed_ids = state_manager.get_failed_photo_ids()
        failed_count = len(failed_ids)
        print(f"❌ Failed photos: {failed_count}")
        
        # Calculate remaining
        remaining = total_photos - posted_count - failed_count
        print(f"⏳ Remaining photos: {remaining}")
        
        # Show next photo that would be posted
        next_photo = state_manager.get_next_photo_to_post(photos, include_dry_runs=False)
        if next_photo:
            position = next_photo.get('album_position', 'unknown')
            print(f"\n📸 Next photo to post: #{position} - {next_photo['title']} (ID: {next_photo['id']})")
        else:
            print(f"\n🎉 No more photos to post - album complete!")
        
        # Show some details about posted photos
        if posted_ids:
            print(f"\n📋 Posted photo IDs: {posted_ids[:5]}{'...' if len(posted_ids) > 5 else ''}")
        
        if failed_ids:
            print(f"🚫 Failed photo IDs: {failed_ids}")
            
    except Exception as e:
        print(f"❌ Error checking album state: {e}")

if __name__ == "__main__":
    main()