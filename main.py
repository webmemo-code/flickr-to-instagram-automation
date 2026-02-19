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
from email_notifier import EmailNotifier
from account_config import account_manager


def setup_logging(level: str = "INFO") -> None:
    """Setup logging configuration."""
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Setup console handler with UTF-8 encoding for Windows compatibility
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    # Force UTF-8 encoding to handle emoji characters on Windows
    if hasattr(console_handler.stream, 'reconfigure'):
        console_handler.stream.reconfigure(encoding='utf-8')
    
    # Setup file handler with UTF-8 encoding
    log_file = f"automation_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)


def post_next_photo(dry_run: bool = False, include_dry_runs: bool = True, account: str = 'primary') -> bool:
    """Post the next available photo from the configured album using modular orchestration."""
    logger = logging.getLogger(__name__)

    try:
        # Initialize components
        config = Config(account=account)
        flickr_api = FlickrAPI(config)
        caption_generator = CaptionGenerator(config)
        instagram_api = InstagramAPI(config)
        email_notifier = EmailNotifier(config)

        # Get repository name from environment
        repo_name = os.getenv('GITHUB_REPOSITORY')
        if not repo_name:
            raise ValueError("GITHUB_REPOSITORY environment variable not set")

        environment_name = account_manager.get_environment_name(account)
        state_manager = StateManager(config, repo_name, environment_name=environment_name)

        # Initialize orchestration modules
        from orchestration import (
            create_photo_selector,
            create_photo_validator,
            create_caption_orchestrator,
            create_caption_preprocessor,
            create_posting_orchestrator,
            create_state_orchestrator,
            create_validation_state_handler
        )

        photo_selector = create_photo_selector(flickr_api, state_manager)
        photo_validator = create_photo_validator(instagram_api)
        caption_orchestrator = create_caption_orchestrator(caption_generator)
        caption_preprocessor = create_caption_preprocessor()
        posting_orchestrator = create_posting_orchestrator(instagram_api)
        state_orchestrator = create_state_orchestrator(state_manager, email_notifier)
        validation_state_handler = create_validation_state_handler(state_manager)

        logger.info(f"Starting automation for album: {config.album_name}")
        logger.info(f"Album URL: {config.album_url}")
        if dry_run:
            logger.info("🧪 Running in DRY RUN mode")
            if include_dry_runs:
                logger.info("📝 Including previous dry run selections in photo selection")

        # Photo Selection Phase
        selection_result = photo_selector.get_next_photo_to_post(include_dry_runs, dry_run)

        if not selection_result.success:
            logger.warning(selection_result.message)
            account_display = account.capitalize() if account != 'primary' else 'Primary'
            state_orchestrator.log_automation_run(
                False, selection_result.message, account_display, config.album_name, config.album_url
            )
            return False

        if selection_result.is_album_complete:
            logger.info(f"🎉 {selection_result.message}")

            # Signal completion to workflow for auto-disable
            if not dry_run:
                with open('album_complete.marker', 'w') as f:
                    f.write('true')

            # Handle album completion
            state_orchestrator.handle_album_completion(selection_result.photos_total, config.album_name)

            account_display = account.capitalize() if account != 'primary' else 'Primary'
            completion_message = "Album complete - all photos posted" if selection_result.photos_total > 0 else "No more photos to process"
            state_orchestrator.log_automation_run(
                True, completion_message, account_display, config.album_name, config.album_url
            )
            return True

        # We have a photo to process
        selected_photo = selection_result.photo
        position = selected_photo.get('album_position', 'unknown')

        # Photo Validation Phase
        is_valid, validation_error = photo_validator.validate_photo_for_posting(selected_photo)

        if not is_valid:
            logger.error(f"❌ Photo validation failed: {validation_error}")

            # Handle validation failure
            validation_state_handler.handle_validation_failure(selected_photo, validation_error, dry_run)

            account_display = account.capitalize() if account != 'primary' else 'Primary'
            state_orchestrator.log_automation_run(
                True, f"Skipped photo #{position} due to validation failure",
                account_display, config.album_name, config.album_url
            )
            return True  # Continue with next photo

        # Caption Generation Phase
        preprocessed_photo = caption_preprocessor.preprocess_photo_data(selected_photo)
        caption_result = caption_orchestrator.generate_full_caption(preprocessed_photo)

        if not caption_result.success:
            logger.error(f"❌ Caption generation failed: {caption_result.message}")
            return False

        if caption_result.used_fallback:
            logger.warning(f"⚠️ Used fallback caption: {caption_result.message}")

        # Posting Phase
        posting_workflow_result = posting_orchestrator.execute_posting_workflow(
            selected_photo,
            caption_result.caption,
            selection_result.photos_total,
            dry_run
        )

        if not posting_workflow_result['workflow_success']:
            logger.error(f"❌ Posting workflow failed: {posting_workflow_result['posting_message']}")

            # Record the failed post
            state_result = state_orchestrator.record_post_outcome(
                selected_photo, None, dry_run, config.create_audit_issues
            )

            if state_result.critical_failure:
                logger.error("💥 Critical error: Cannot record failed post - stopping automation")
                return False

            logger.warning("⚠️ Photo processing failed but automation can continue")
            return True  # Continue with next photo

        # State Recording Phase
        state_result = state_orchestrator.record_post_outcome(
            selected_photo,
            posting_workflow_result['instagram_post_id'],
            dry_run,
            config.create_audit_issues
        )

        if not state_result.success:
            if state_result.critical_failure:
                logger.error(f"💥 Critical state management error: {state_result.message}")
                return False
            else:
                logger.warning(f"⚠️ State management warning: {state_result.message}")

        # Check for album completion after successful posting
        progress_info = posting_workflow_result['progress_info']
        if progress_info.get('is_complete', False):
            state_orchestrator.handle_album_completion(selection_result.photos_total, config.album_name)
            # Signal completion to workflow for auto-disable
            if not dry_run:
                with open('album_complete.marker', 'w') as f:
                    f.write('true')

        return True

    except Exception as e:
        logger.error(f"💥 Automation failed: {e}")
        return False


def reset_dry_runs(account: str = 'primary') -> None:
    """Reset all dry run records."""
    logger = logging.getLogger(__name__)
    
    try:
        config = Config(account=account)
        repo_name = os.getenv('GITHUB_REPOSITORY')
        if not repo_name:
            raise ValueError("GITHUB_REPOSITORY environment variable not set")
        
        environment_name = account_manager.get_environment_name(account)
        state_manager = StateManager(config, repo_name, environment_name=environment_name)
        cleared_count = state_manager.clear_dry_run_records()
        
        print(f"✅ Cleared {cleared_count} dry run records")
        logger.info(f"Reset {cleared_count} dry run records")
        
    except Exception as e:
        logger.error(f"Failed to reset dry runs: {e}")
        print(f"❌ Failed to reset dry runs: {e}")


def show_stats(account: str = 'primary') -> None:
    """Show automation statistics."""
    logger = logging.getLogger(__name__)
    
    try:
        config = Config(account=account)
        repo_name = os.getenv('GITHUB_REPOSITORY')
        if not repo_name:
            raise ValueError("GITHUB_REPOSITORY environment variable not set")
        
        environment_name = account_manager.get_environment_name(account)
        state_manager = StateManager(config, repo_name, environment_name=environment_name)
        flickr_api = FlickrAPI(config)
        
        # Get total photos in album
        photos = flickr_api.get_unposted_photos()
        total_photos = len(photos) if photos else 0
        
        stats = state_manager.get_automation_stats()
        
        print(f"\n=== 📊 Album Statistics ===")
        print(f"Album: {config.album_name}")
        print(f"Album ID: {config.flickr_album_id}")
        print(f"Album URL: {config.album_url}")
        # Get position-based stats
        last_position = state_manager.get_last_posted_position()
        failed_positions = state_manager.get_failed_positions()
        instagram_posts = state_manager.get_instagram_posts()
        
        print(f"\n📈 Progress:")
        print(f"  Total Photos in Album: {total_photos}")
        print(f"  Posted Photos (by position): {last_position}")
        print(f"  Instagram Posts Recorded: {len(instagram_posts)}")
        print(f"  Failed Photos: {len(failed_positions)}")
        print(f"  Remaining Photos: {total_photos - last_position}")
        
        if total_photos > 0:
            completion_rate = round((last_position / total_photos) * 100, 1)
            print(f"  Completion Rate: {completion_rate}%")
        
        if failed_positions:
            print(f"  Failed Positions for Retry: {sorted(failed_positions)}")
        
        print(f"\n⚙️  Configuration:")
        print(f"  Audit Issues Creation: {'Enabled' if config.create_audit_issues else 'Disabled (recommended for scale)'}")
        
        if instagram_posts:
            print(f"\n📱 Recent Instagram Posts:")
            for post in sorted(instagram_posts, key=lambda x: x.get('position', 0))[-5:]:
                print(f"  #{post.get('position', '?')}: {post.get('title', 'Unknown')} -> {post.get('instagram_post_id', 'Unknown')}")
        
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
    parser.add_argument(
        '--test-email',
        action='store_true',
        help='Test email notification configuration'
    )
    # Get available account choices dynamically from account configuration
    available_accounts = account_manager.get_all_account_ids()
    parser.add_argument(
        '--account',
        choices=available_accounts,
        default='primary',
        help=f'Account to use (available: {", ".join(available_accounts)})'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    # Reset dry runs if requested
    if args.reset_dry_runs:
        reset_dry_runs(args.account)
        return
    
    # Show stats if requested
    if args.stats:
        show_stats(args.account)
        return
    
    # Test email configuration if requested
    if args.test_email:
        config = Config(email_test_mode=True)
        email_notifier = EmailNotifier(config)
        
        logger.info("Testing email notification configuration...")
        success = email_notifier.test_email_configuration()
        
        if success:
            print("Email configuration test successful!")
            logger.info("Email test completed successfully")
        else:
            print("Email configuration test failed - check logs for details")
            logger.error("Email test failed")
            sys.exit(1)
        return
    
    # Run automation
    account_name = args.account.capitalize() if args.account != 'primary' else 'Primary'
    logger.info(f"🚀 Starting Flickr to Instagram automation for {account_name} account")
    include_dry_runs = not args.ignore_dry_runs
    success = post_next_photo(args.dry_run, include_dry_runs, args.account)
    
    if success:
        logger.info("✅ Automation run completed")
        sys.exit(0)
    else:
        logger.error("❌ Automation failed - unable to continue")
        sys.exit(1)


if __name__ == "__main__":
    main()