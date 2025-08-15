#!/usr/bin/env python3
"""
Test script to check current state management and trigger variable creation.
"""
import os
from state_manager import StateManager
from config import Config

def test_state_management():
    """Test the current state management system."""
    
    try:
        print("Testing state management system...")
        print("="*50)
        
        # Initialize components
        config = Config()
        repo_name = os.getenv('GITHUB_REPOSITORY', 'webmemo-code/flickr-to-instagram-automation')
        
        state_manager = StateManager(config, repo_name)
        
        # Test getting last posted position (this should trigger fallback and migration)
        print("Testing get_last_posted_position()...")
        last_position = state_manager.get_last_posted_position()
        print(f"✅ Last posted position: {last_position}")
        
        # Test getting failed positions
        print("\nTesting get_failed_positions()...")
        failed_positions = state_manager.get_failed_positions()
        print(f"✅ Failed positions: {failed_positions}")
        
        # Test getting total photos
        print("\nTesting get_total_album_photos()...")
        total_photos = state_manager.get_total_album_photos()
        print(f"✅ Total album photos: {total_photos}")
        
        # Test Instagram posts
        print("\nTesting get_instagram_posts()...")
        instagram_posts = state_manager.get_instagram_posts()
        print(f"✅ Instagram posts recorded: {len(instagram_posts)}")
        
        print("\n" + "="*50)
        print("🎉 State management test completed!")
        print("\nIf variables were created, check:")
        print("GitHub → Settings → Secrets and variables → Actions → Variables")
        
    except Exception as e:
        print(f"❌ Error testing state management: {e}")
        print("\nThis is likely because environment variables are not set.")
        print("The test needs GITHUB_TOKEN and other config variables.")

if __name__ == "__main__":
    test_state_management()