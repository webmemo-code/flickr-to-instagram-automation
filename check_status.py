#!/usr/bin/env python3
"""
Diagnostic script to check the current album status and GitHub Issues state.
"""
import os
import sys
from config import Config
from state_manager import StateManager
from flickr_api import FlickrAPI

def main():
    """Check current album status."""
    try:
        # Initialize components
        config = Config()
        
        # Set repository name for your actual repo
        repo_name = "webmemo-code/flickr-to-instagram-automation"
        state_manager = StateManager(config, repo_name)
        flickr_api = FlickrAPI(config)
        
        print("=== 🔍 Album Status Diagnostic ===\n")
        
        # Get photos from Flickr
        print("📸 Fetching photos from Flickr...")
        photos = flickr_api.get_unposted_photos()
        total_photos = len(photos) if photos else 0
        print(f"Total photos in Flickr album: {total_photos}")
        
        if total_photos == 0:
            print("❌ No photos found in album. Check your Flickr configuration.")
            return
        
        # Get state from GitHub Issues
        print("\n📋 Checking GitHub Issues state...")
        posted_ids = state_manager.get_posted_photo_ids()
        failed_ids = state_manager.get_failed_photo_ids()
        dry_run_ids = state_manager.get_dry_run_photo_ids()
        
        print(f"Successfully posted photos: {len(posted_ids)}")
        print(f"Failed photos: {len(failed_ids)}")  
        print(f"Dry run selections: {len(dry_run_ids)}")
        
        # Calculate remaining
        processed_count = len(posted_ids) + len(failed_ids)
        remaining_count = total_photos - processed_count
        
        print(f"\n📊 Summary:")
        print(f"Total photos: {total_photos}")
        print(f"Successfully posted: {len(posted_ids)}")
        print(f"Failed: {len(failed_ids)}")
        print(f"Processed (posted + failed): {processed_count}")
        print(f"Remaining to process: {remaining_count}")
        
        # Check album completion status
        is_complete = state_manager.is_album_complete(total_photos)
        print(f"\nAlbum marked as complete: {is_complete}")
        
        # Show detailed lists
        if posted_ids:
            print(f"\n✅ Successfully posted photo IDs: {posted_ids}")
        if failed_ids:
            print(f"\n❌ Failed photo IDs: {failed_ids}")
        if dry_run_ids:
            print(f"\n🧪 Dry run photo IDs: {dry_run_ids}")
            
        # Show next photo to process
        next_photo = state_manager.get_next_photo_to_post(photos, include_dry_runs=False)
        if next_photo:
            position = next_photo.get('album_position', 'unknown')
            print(f"\n➡️ Next photo to process: #{position} - {next_photo['title']} (ID: {next_photo['id']})")
        else:
            print(f"\n🎉 No more photos to process!")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()