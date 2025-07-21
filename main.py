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


def post_next_photo(dry_run: bool = False, include_dry_runs: bool = True) -> bool:
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
        if dry_run:
            logger.info("🧪 Running in DRY RUN mode")
            if include_dry_runs:
                logger.info("📝 Including previous dry run selections in photo selection")
        
        # Get photos from Flickr
        photos = flickr_api.get_unposted_photos()
        if not photos:
            logger.warning("No photos found in the album")
            state_manager.log_automation_run(False, "No photos found in album")
            return False
        
        logger.info(f"Retrieved {len(photos)} photos from album")
        
        # Debug: Log all photos and their positions
        for photo in sorted(photos, key=lambda x: x.get('album_position', 0)):
            logger.debug(f"Album photo #{photo.get('album_position', '?')}: {photo['id']} - {photo['title']}")
        
        # Check if album is complete (only count actual posts, not dry runs)
        if state_manager.is_album_complete(len(photos)):
            logger.info("🎉 Album complete! All photos have been posted to Instagram.")
            state_manager.log_automation_run(True, "Album complete - all photos posted")
            return True
        
        # Get next photo to post
        next_photo = state_manager.get_next_photo_to_post(photos, include_dry_runs=include_dry_runs and dry_run)
        if not next_photo:
            if dry_run and include_dry_runs:
                logger.info("🎉 All photos have been selected in dry runs! Use --reset-dry-runs to start over.")
            else:
                logger.info("🎉 Album complete! All photos have been posted to Instagram.")
            state_manager.log_automation_run(True, "No more photos to process")
            return True
        
        position = next_photo.get('album_position', 'unknown')
        logger.info(f"📸 Processing photo #{position}: {next_photo['title']} (ID: {next_photo['id']})")
        
        # Validate image URL
        if not instagram_api.validate_image_url(next_photo['url']):
            logger.error(f"❌ Invalid or inaccessible image URL: {next_photo['url']}")
            logger.info(f"⏭️ Skipping photo #{position} and marking as failed to continue with next photo")
            state_manager.create_post_record(next_photo, None, is_dry_run=dry_run)
            state_manager.log_automation_run(True, f"Skipped photo #{position} due to invalid image URL")
            return True  # Return True to continue with next photo
        
        # Generate caption with GPT-4 Vision
        logger.info("🤖 Generating enhanced caption with GPT-4 Vision...")
        generated_caption = caption_generator.generate_with_retry(next_photo)
        
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
            
            # Create dry run record to track selection
            state_manager.create_post_record(next_photo, None, is_dry_run=True)
            state_manager.log_automation_run(True, f"Dry run completed for photo #{position}")
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
            else:
                # Fallback: create new record if the initial one failed
                logger.warning("No issue number from initial record creation, creating new one")
                state_manager.create_post_record(next_photo, instagram_post_id)
            
            # Log progress - get actual posted count after updating record
            posted_count = len(state_manager.get_posted_photo_ids())
            total_count = len(photos)
            progress_msg = f"Posted photo #{position} ({next_photo['id']}) - {posted_count}/{total_count} - Instagram post {instagram_post_id}"
            
            state_manager.log_automation_run(True, progress_msg)
            logger.info(f"📊 Progress: {posted_count}/{total_count} photos posted (just posted #{position})")
            
            if posted_count >= total_count:
                logger.info("🎉 Album complete! All photos have been posted.")
            
            return True
        else:
            logger.error("❌ Failed to post to Instagram")
            logger.info(f"⏭️ Marking photo #{position} as failed and continuing with next photo")
            state_manager.log_automation_run(True, f"Photo #{position} failed to post to Instagram, continuing")
            return True  # Return True to continue with next photo
    
    except Exception as e:
        logger.error(f"💥 Automation failed: {e}")
        try:
            if 'state_manager' in locals():
                state_manager.log_automation_run(False, f"Exception: {str(e)}")
        except:
            pass  # Don't fail if logging fails
        return False


def reset_dry_runs() -> None:
    """Reset all dry run records."""
    logger = logging.getLogger(__name__)
    
    try:
        config = Config()
        repo_name = os.getenv('GITHUB_REPOSITORY')
        if not repo_name:
            raise ValueError("GITHUB_REPOSITORY environment variable not set")
        
        state_manager = StateManager(config, repo_name)
        cleared_count = state_manager.clear_dry_run_records()
        
        print(f"✅ Cleared {cleared_count} dry run records")
        logger.info(f"Reset {cleared_count} dry run records")
        
    except Exception as e:
        logger.error(f"Failed to reset dry runs: {e}")
        print(f"❌ Failed to reset dry runs: {e}")


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
        '--reset-dry-runs',
        action='store_true',
        help='Clear all dry run records'
    )
    parser.add_argument(
        '--ignore-dry-runs',
        action='store_true',
        help='Ignore previous dry run selections when choosing next photo'
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
    
    # Reset dry runs if requested
    if args.reset_dry_runs:
        reset_dry_runs()
        return
    
    # Show stats if requested
    if args.stats:
        show_stats()
        return
    
    # Run automation
    logger.info("🚀 Starting Flickr to Instagram automation")
    include_dry_runs = not args.ignore_dry_runs
    success = post_next_photo(args.dry_run, include_dry_runs)
    
    if success:
        logger.info("✅ Automation completed successfully")
        sys.exit(0)
    else:
        logger.error("❌ Automation failed")
        sys.exit(1)


if __name__ == "__main__":
    main()