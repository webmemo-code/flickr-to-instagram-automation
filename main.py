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


def _log_run(state_manager: StateManager, success: bool, message: str,
             account_display: str, config: Config) -> None:
    """Log an automation run result to state."""
    state_manager.log_automation_run(
        success, message, account_display, config.album_name, config.album_url
    )


def _handle_album_complete(state_manager: StateManager, email_notifier: EmailNotifier,
                           total_photos: int, config: Config,
                           account_display: str, dry_run: bool) -> None:
    """Handle album completion: notify, log, write marker."""
    logger = logging.getLogger(__name__)
    logger.info("Album complete! All photos have been posted.")

    try:
        email_notifier.send_completion_notification(total_photos, config.album_name)
    except Exception as e:
        logger.warning(f"Completion email failed: {e}")

    if not dry_run:
        with open('album_complete.marker', 'w') as f:
            f.write('true')

    _log_run(state_manager, True, "Album complete", account_display, config)


def post_next_photo(dry_run: bool = False, include_dry_runs: bool = True, account: str = 'primary') -> bool:
    """Post the next available photo from the configured album."""
    logger = logging.getLogger(__name__)

    try:
        # Initialize components
        config = Config(account=account)
        flickr_api = FlickrAPI(config)
        caption_generator = CaptionGenerator(config)
        instagram_api = InstagramAPI(config)
        email_notifier = EmailNotifier(config)

        repo_name = os.getenv('GITHUB_REPOSITORY')
        if not repo_name:
            raise ValueError("GITHUB_REPOSITORY environment variable not set")

        environment_name = account_manager.get_environment_name(account)
        state_manager = StateManager(config, repo_name, environment_name=environment_name)
        account_display = account.capitalize() if account != 'primary' else 'Primary'

        logger.info(f"Starting automation for album: {config.album_name}")
        logger.info(f"Album URL: {config.album_url}")
        if dry_run:
            logger.info("Running in DRY RUN mode")
            if include_dry_runs:
                logger.info("Including previous dry run selections in photo selection")

        # --- Photo Selection ---
        photos = flickr_api.get_photo_list()
        if not photos:
            _log_run(state_manager, False, "No photos found in album", account_display, config)
            return False

        total_photos = len(photos)
        logger.info(f"Retrieved {total_photos} photos from album")

        if state_manager.is_album_complete(total_photos):
            _handle_album_complete(state_manager, email_notifier,
                                   total_photos, config, account_display, dry_run)
            return True

        selected_photo = state_manager.get_next_photo_to_post(
            photos, include_dry_runs=(include_dry_runs and dry_run)
        )

        if not selected_photo:
            if dry_run and include_dry_runs:
                logger.info("All photos have been selected in dry runs! Use --reset-dry-runs to start over.")
            _handle_album_complete(state_manager, email_notifier,
                                   total_photos, config, account_display, dry_run)
            return True

        selected_photo = flickr_api.enrich_photo(selected_photo)
        position = selected_photo.album_position
        logger.info(f"Selected photo #{position}: {selected_photo.title} (ID: {selected_photo.id})")

        # --- Photo Validation ---
        logger.info("Validating image URL (includes retry if needed)...")
        if not instagram_api.validate_image_url(selected_photo.url):
            error_msg = f"Invalid or inaccessible image URL after retries: {selected_photo.url}"
            logger.error(f"Photo validation failed: {error_msg}")
            state_manager.create_post_record(selected_photo, None, is_dry_run=dry_run)
            _log_run(state_manager, False,
                     f"Skipped photo #{position} due to validation failure",
                     account_display, config)
            return True  # Non-fatal: will try next photo on next run

        # --- Caption Generation ---
        logger.info("Generating caption with Claude Vision...")
        generated_caption = caption_generator.generate_with_retry(selected_photo)

        if not generated_caption:
            logger.warning("Caption generation failed, using fallback")
            generated_caption = "Beautiful moment captured during our travels."

        full_caption = caption_generator.build_full_caption(selected_photo, generated_caption)
        logger.info(f"Generated caption: {full_caption[:100]}...")

        # --- Posting ---
        instagram_post_id = None
        if dry_run:
            logger.info(f"DRY RUN: Would post to Instagram")
            logger.info(f"Image URL: {selected_photo.url}")
            logger.info(f"Caption: {full_caption}")
            logger.info(f"Dry run completed for photo #{position}")
        else:
            logger.info("Posting to Instagram...")
            instagram_post_id = instagram_api.post_with_retry(selected_photo.url, full_caption)
            if not instagram_post_id:
                logger.error(f"Failed to post photo #{position} to Instagram")
                state_manager.create_post_record(selected_photo, None, is_dry_run=False)
                state_manager.record_failed_position(
                    position, selected_photo.id, "Instagram posting failed"
                )
                _log_run(state_manager, False,
                         f"Failed to post photo #{position} to Instagram",
                         account_display, config)
                return False

        # --- Record State ---
        logger.info(f"Progress: Posted {position}/{total_photos} photos (just posted #{position})")
        record_id = state_manager.create_post_record(
            selected_photo, instagram_post_id,
            is_dry_run=dry_run, create_audit_issue=config.create_audit_issues
        )
        if not record_id and not dry_run:
            logger.error("Critical: failed to record post state")
            return False

        # Check if album just completed
        if isinstance(position, int) and position >= total_photos:
            _handle_album_complete(state_manager, email_notifier,
                                   total_photos, config, account_display, dry_run)

        _log_run(state_manager, True,
                 f"{'DRY RUN: ' if dry_run else ''}Posted photo #{position}",
                 account_display, config)
        return True

    except Exception as e:
        logger.error(f"Automation failed: {e}")
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

        print(f"Cleared {cleared_count} dry run records")
        logger.info(f"Reset {cleared_count} dry run records")

    except Exception as e:
        logger.error(f"Failed to reset dry runs: {e}")
        print(f"Failed to reset dry runs: {e}")


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

        # Get total photos in album (lightweight, 1 API call)
        total_photos = flickr_api.get_album_photo_count()

        stats = state_manager.get_statistics()
        metadata = state_manager.get_album_metadata()
        failed_positions = state_manager.get_failed_positions()
        instagram_posts = state_manager.get_instagram_posts()

        last_position = metadata.last_posted_position or 0
        posted_count = stats.get('posted_count', 0)

        print(f"\n=== Album Statistics ===")
        print(f"Album: {config.album_name}")
        print(f"Album ID: {config.flickr_album_id}")
        print(f"Album URL: {config.album_url}")

        print(f"\nProgress:")
        print(f"  Total Photos in Album: {total_photos}")
        print(f"  Posted Photos: {posted_count}")
        print(f"  Instagram Posts Recorded: {len(instagram_posts)}")
        print(f"  Failed Photos: {len(failed_positions)}")
        print(f"  Remaining Photos: {total_photos - posted_count}")

        if total_photos > 0:
            completion_rate = round((posted_count / total_photos) * 100, 1)
            print(f"  Completion Rate: {completion_rate}%")

        if failed_positions:
            print(f"  Failed Positions for Retry: {sorted(failed_positions)}")

        print(f"\nConfiguration:")
        print(f"  Audit Issues Creation: {'Enabled' if config.create_audit_issues else 'Disabled (recommended for scale)'}")

        if instagram_posts:
            print(f"\nRecent Instagram Posts:")
            sorted_posts = sorted(instagram_posts, key=lambda x: x.position)[-5:]
            for post in sorted_posts:
                print(f"  #{post.position}: {post.title or 'Unknown'} -> {post.instagram_post_id or 'Unknown'}")

        print(f"\nAutomation Runs:")
        print(f"  Workflow Runs: {stats.get('workflow_runs_count', 0)}")
        print(f"  Errors: {stats.get('error_count', 0)}")

        # Check if complete
        if state_manager.is_album_complete(total_photos):
            print(f"\nStatus: COMPLETE - All photos posted!")
        else:
            print(f"\nStatus: IN PROGRESS")

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
    logger.info(f"Starting Flickr to Instagram automation for {account_name} account")
    include_dry_runs = not args.ignore_dry_runs
    success = post_next_photo(args.dry_run, include_dry_runs, args.account)

    if success:
        logger.info("Automation completed successfully")
        sys.exit(0)
    else:
        logger.error("Automation failed - check logs for details")
        sys.exit(1)


if __name__ == "__main__":
    main()
