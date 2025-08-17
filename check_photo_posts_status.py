#!/usr/bin/env python3
"""
Simple status checker using the same GitHub authentication as the main automation.
"""
import os
from state_manager import StateManager
from config import Config

def main():
    print("=== 🔍 GitHub Issues Status Check ===\n")
    
    try:
        # Initialize config and state manager (same as main automation)
        config = Config()
        state_manager = StateManager(config, "webmemo-code/flickr-to-instagram-automation")
        
        print("✅ Successfully connected to GitHub API")
        print(f"📂 Repository: webmemo-code/flickr-to-instagram-automation\n")
        
        # Get posted photos
        print("🔍 Checking posted photos...")
        posted_ids = state_manager.get_posted_photo_ids()
        print(f"✅ Successfully posted photos: {len(posted_ids)}")
        
        # Get failed photos
        print("\n🔍 Checking failed photos...")
        failed_ids = state_manager.get_failed_photo_ids()
        print(f"❌ Failed photos: {len(failed_ids)}")
        
        # Total processed
        total_processed = len(posted_ids) + len(failed_ids)
        print(f"\n📊 Total processed (posted + failed): {total_processed}")
        
        # Show some details if we have data
        if posted_ids:
            print(f"\n📋 Last few posted photo IDs: {posted_ids[-5:]}")
        
        if failed_ids:
            print(f"📋 Failed photo IDs: {failed_ids}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nThis might be due to:")
        print("1. Missing GitHub token (GITHUB_TOKEN environment variable)")
        print("2. Network connectivity issues")
        print("3. Repository access permissions")

if __name__ == "__main__":
    main()