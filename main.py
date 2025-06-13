#!/usr/bin/env python3
"""
Main automation script for Flickr to Instagram posting.
"""
import os
import sys
import logging
import argparse
from datetime import datetime
from typing import Optional

from config import Config
from flickr_api import FlickrAPI
from caption_generator import CaptionGenerator
from instagram_api import InstagramAPI
from state_manager import StateManager


def setup_logging(level: str = "INFO") -> None:
    """Setup logging configuration."""
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Setup console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # Setup file handler
    log_file = f"automation_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)


def post_next_photo(dry_run: bool = False) -> bool:
    """Post the next available photo from the configured album."""
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize components
        config = Config()
        flickr_api = FlickrAPI(config)
        caption_generator = CaptionGenerator(config)
        instagram_api = InstagramAPI(config)
        
        # Get repository name from environment
        repo_name = os.getenv('GITHUB_REPOSITORY')
        if not repo_name:
            raise ValueError("GITHUB_REPOSITORY environment variable not set")
        
        state_manager = StateManager(config, repo_name)
        
        logger.info(f"Starting automation for album: {config.album_name}")
        logger.info(f"Album URL: {config.album_url}")
        
        # Get photos from Flickr
        photos = flickr_api.get_unposted_photos()
        if not photos:
            logger.warning("No photos found in the album")
            state_manager.log_automation_run(False, "No photos found in album")
            return False
        
        # Check if album is complete
        if state_manager.is_album_complete(len(photos)):
            logger.info("🎉 Album complete! All photos have been posted to Instagram.")
            state_manager.log_automation_run(True, "Album complete - all photos posted")
            return True
        
        # Get next photo to post
        next_photo = state_manager.get_next_photo_to_post(photos)
        if not next_photo:
            logger.info("🎉 Album complete! All photos have been posted to Instagram.")
            state_manager.log_automation_run(True, "Album complete - all photos posted")
            return True
        
        logger.info(f"📸 Processing photo: {next_photo['title']} (ID: {next_photo['id']})")
        
        # Validate image URL
        if not instagram_api.validate_image_url(next_photo['url']):
            logger.error(f"❌ Invalid or inaccessible image URL: {next_photo['url']}")
            state_manager.create_post_record(next_photo, None)
            state_manager.log_automation_run(False, "Invalid image URL")
            return False
        
        # Generate caption with GPT-4 Vision
        logger.info("🤖 Generating caption with GPT-4 Vision...")
        generated_caption = caption_generator.generate_with_retry(
            next_photo['url'], 
            next_photo['title'], 
            next_photo['description']
        )
        
        if not generated_caption:
            logger.warning("⚠️ Failed to generate caption, using fallback")
            generated_caption = "Beautiful moment captured during our travels."
        
        # Build full caption
        full_caption = caption_generator.build_full_caption(next_photo, generated_caption)
        
        logger.info(f"📝 Generated caption: {full_caption[:100]}...")
        
        if dry_run:
            logger.info("🧪 DRY RUN: Would post to Instagram")
            logger.info(f"Image URL: {next_photo['url']}")
            logger.info(f"Caption: {full_caption}")
            state_manager.log_automation_run(True, "Dry run completed")
            return True
        
        # Create record before posting
        issue_number = state_manager.create_post_record(next_photo, None)
        
        # Post to Instagram
        logger.info("📱 Posting to Instagram...")
        instagram_post_id = instagram_api.post_with_retry(next_photo['url'], full_caption)
        
        if instagram_post_id:
            logger.info(f"✅ Successfully posted to Instagram: {instagram_post_id}")
            
            # Update record with Instagram post ID
            if issue_number:
                state_manager.update_post_record(issue_number, instagram_post_id)
            
            # Log progress
            posted_count = len(state_manager.get_posted_photo_ids()) + 1  # +1 for current post
            total_count = len(photos)
            progress_msg = f"Posted photo {next_photo['id']} ({posted_count}/{total_count}) - Instagram post {instagram_post_id}"
            
            state_manager.log_automation_run(True, progress_msg)
            logger.info(f"📊 Progress: {posted_count}/{total_count} photos posted")
            
            if posted_count >= total_count:
                logger.info("🎉 Album complete! All photos have been posted.")
            
            return True
        else:
            logger.error("❌ Failed to post to Instagram")
            state_manager.log_automation_run(False, "Instagram posting failed")
            return False
    
    except Exception as e:
        logger.error(f"💥 Automation failed: {e}")
        try:
            state_manager.log_automation_run(False, f"Exception: {str(e)}")
        except:
            pass  # Don't fail if logging fails
        return False


def show_stats() -> None:
    """Show automation statistics."""
    logger = logging.getLogger(__name__)
    
    try:
        config = Config()
        repo_name = os.getenv('GITHUB_REPOSITORY')
        if not repo_name:
            raise ValueError("GITHUB_REPOSITORY environment variable not set")
        
        state_manager = StateManager(config, repo_name)
        flickr_api = FlickrAPI(config)
        
        # Get total photos in album
        photos = flickr_api.get_unposted_photos()
        total_photos = len(photos) if photos else 0
        
        stats = state_manager.get_automation_stats()
        
        print(f"\n=== 📊 Album Statistics ===")
        print(f"Album: {config.album_name}")
        print(f"Album ID: {config.flickr_album_id}")
        print(f"Album URL: {config.album_url}")
        print(f"\n📈 Progress:")
        print(f"  Total Photos in Album: {total_photos}")
        print(f"  Posted Photos: {stats.get('posted_photos', 0)}")
        print(f"  Failed Photos: {stats.get('failed_photos', 0)}")
        print(f"  Remaining Photos: {total_photos - stats.get('posted_photos', 0)}")
        
        if total_photos > 0:
            completion_rate = round((stats.get('posted_photos', 0) / total_photos) * 100, 1)
            print(f"  Completion Rate: {completion_rate}%")
        
        print(f"\n🤖 Automation Runs:")
        print(f"  Successful Runs: {stats.get('successful_runs', 0)}")
        print(f"  Failed Runs: {stats.get('failed_runs', 0)}")
        print(f"  Success Rate: {stats.get('success_rate', 0)}%")
        
        # Check if complete
        if state_manager.is_album_complete(total_photos):
            print(f"\n🎉 Status: COMPLETE - All photos posted!")
        else:
            print(f"\n⏳ Status: IN PROGRESS")
    
    except Exception as e:
        logger.error(f"Failed to show stats: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Flickr to Instagram Automation')
    parser.add_argument(
        '--dry-run', 
        action='store_true',
        help='Run without actually posting to Instagram'
    )
    parser.add_argument(
        '--stats', 
        action='store_true',
        help='Show automation statistics'
    )
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    # Show stats if requested
    if args.stats:
        show_stats()
        return
    
    # Run automation
    logger.info("🚀 Starting Flickr to Instagram automation")
    success = post_next_photo(args.dry_run)
    
    if success:
        logger.info("✅ Automation completed successfully")
        sys.exit(0)
    else:
        logger.error("❌ Automation failed")
        sys.exit(1)


if __name__ == "__main__":
    main()