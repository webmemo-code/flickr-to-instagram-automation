#!/usr/bin/env python3
"""
Test script for the new Git-based storage system.

This script tests the functionality of the new storage adapters and state management
to ensure they work correctly before migration.
"""

import json
import logging
import sys
import tempfile
import os
from typing import Dict, Any
from datetime import datetime

# Import new storage components
from storage_adapter import GitFileStorageAdapter
from state_models import InstagramPost, FailedPosition, AlbumMetadata, PostStatus
from state_manager_v2 import EnhancedStateManager
from config import Config


def setup_logging():
    """Set up logging for tests."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def test_storage_adapter(repo_name: str, github_token: str) -> Dict[str, Any]:
    """Test the Git storage adapter functionality."""
    logging.info("Testing Git storage adapter...")

    test_results = {
        "adapter_initialization": False,
        "branch_creation": False,
        "write_posts": False,
        "read_posts": False,
        "write_failed_positions": False,
        "read_failed_positions": False,
        "write_metadata": False,
        "read_metadata": False,
        "errors": []
    }

    try:
        # Initialize adapter
        adapter = GitFileStorageAdapter(
            repo_name=repo_name,
            github_token=github_token,
            branch="test-storage-branch"
        )

        if adapter.is_available():
            test_results["adapter_initialization"] = True
            test_results["branch_creation"] = True
            logging.info("✓ Adapter initialization and branch creation successful")
        else:
            test_results["errors"].append("Adapter is not available")
            return test_results

        # Test data
        test_account = "test-primary"
        test_album_id = "test-album-123"

        # Test posts
        test_posts = [
            {
                "position": 1,
                "photo_id": "test_photo_1",
                "instagram_post_id": "test_insta_1",
                "posted_at": datetime.now().isoformat(),
                "title": "Test Photo 1",
                "status": "posted",
                "account": test_account
            }
        ]

        # Write posts
        if adapter.write_posts(test_account, test_album_id, test_posts):
            test_results["write_posts"] = True
            logging.info("✓ Write posts successful")
        else:
            test_results["errors"].append("Failed to write posts")

        # Read posts
        read_posts = adapter.read_posts(test_account, test_album_id)
        if read_posts and len(read_posts) == 1:
            test_results["read_posts"] = True
            logging.info("✓ Read posts successful")
        else:
            test_results["errors"].append(f"Failed to read posts: got {read_posts}")

        # Test failed positions
        test_failed = [2, 5, 8]

        # Write failed positions
        if adapter.write_failed_positions(test_account, test_album_id, test_failed):
            test_results["write_failed_positions"] = True
            logging.info("✓ Write failed positions successful")
        else:
            test_results["errors"].append("Failed to write failed positions")

        # Read failed positions
        read_failed = adapter.read_failed_positions(test_account, test_album_id)
        if read_failed == test_failed:
            test_results["read_failed_positions"] = True
            logging.info("✓ Read failed positions successful")
        else:
            test_results["errors"].append(f"Failed to read failed positions: got {read_failed}")

        # Test metadata
        test_metadata = {
            "album_id": test_album_id,
            "account": test_account,
            "created_at": datetime.now().isoformat(),
            "total_photos": 10,
            "posted_count": 1,
            "failed_count": 3
        }

        # Write metadata
        if adapter.write_metadata(test_account, test_album_id, test_metadata):
            test_results["write_metadata"] = True
            logging.info("✓ Write metadata successful")
        else:
            test_results["errors"].append("Failed to write metadata")

        # Read metadata
        read_metadata = adapter.read_metadata(test_account, test_album_id)
        if read_metadata and read_metadata.get("album_id") == test_album_id:
            test_results["read_metadata"] = True
            logging.info("✓ Read metadata successful")
        else:
            test_results["errors"].append(f"Failed to read metadata: got {read_metadata}")

    except Exception as e:
        test_results["errors"].append(f"Test failed with exception: {e}")
        logging.error(f"Storage adapter test failed: {e}")

    return test_results


def test_enhanced_models() -> Dict[str, Any]:
    """Test the enhanced data models."""
    logging.info("Testing enhanced data models...")

    test_results = {
        "instagram_post_creation": False,
        "instagram_post_status_changes": False,
        "failed_position_creation": False,
        "album_metadata_creation": False,
        "serialization_deserialization": False,
        "legacy_migration": False,
        "errors": []
    }

    try:
        # Test InstagramPost
        post = InstagramPost(
            position=1,
            photo_id="test_photo_123",
            title="Test Photo"
        )

        if post.position == 1 and post.status == PostStatus.PENDING:
            test_results["instagram_post_creation"] = True
            logging.info("✓ InstagramPost creation successful")

        # Test status changes
        post.mark_as_posted("instagram_123", "https://instagram.com/p/123")
        if post.status == PostStatus.POSTED and post.instagram_post_id == "instagram_123":
            test_results["instagram_post_status_changes"] = True
            logging.info("✓ InstagramPost status changes successful")

        # Test FailedPosition
        failed_pos = FailedPosition.from_position(5, "photo_456", "Network error")
        if failed_pos.position == 5 and failed_pos.error_message == "Network error":
            test_results["failed_position_creation"] = True
            logging.info("✓ FailedPosition creation successful")

        # Test AlbumMetadata
        metadata = AlbumMetadata.create_new("album_789", "primary", 50)
        if metadata.album_id == "album_789" and metadata.total_photos == 50:
            test_results["album_metadata_creation"] = True
            logging.info("✓ AlbumMetadata creation successful")

        # Test serialization/deserialization
        post_dict = post.to_dict()
        post_restored = InstagramPost.from_dict(post_dict)
        if post_restored.position == post.position and post_restored.status == post.status:
            test_results["serialization_deserialization"] = True
            logging.info("✓ Serialization/deserialization successful")

        # Test legacy migration
        legacy_post = {
            "position": 3,
            "photo_id": "legacy_photo",
            "instagram_post_id": "legacy_insta",
            "posted_at": "2024-01-01T00:00:00Z",
            "title": "Legacy Photo"
        }

        migrated_post = InstagramPost.from_legacy_dict(legacy_post)
        if migrated_post.position == 3 and migrated_post.status == PostStatus.POSTED:
            test_results["legacy_migration"] = True
            logging.info("✓ Legacy migration successful")

    except Exception as e:
        test_results["errors"].append(f"Model test failed: {e}")
        logging.error(f"Enhanced models test failed: {e}")

    return test_results


def test_enhanced_state_manager(config: Config, repo_name: str) -> Dict[str, Any]:
    """Test the enhanced state manager."""
    logging.info("Testing enhanced state manager...")

    test_results = {
        "initialization": False,
        "post_recording": False,
        "failed_position_recording": False,
        "statistics_generation": False,
        "album_completion_check": False,
        "errors": []
    }

    try:
        # Initialize with Git storage
        state_manager = EnhancedStateManager(
            config=config,
            repo_name=repo_name,
            environment_name="test-account",
            storage_backend="git"
        )

        if state_manager.storage_adapter.is_available():
            test_results["initialization"] = True
            logging.info("✓ Enhanced state manager initialization successful")
        else:
            test_results["errors"].append("Enhanced state manager storage not available")
            return test_results

        # Test post recording
        test_photo_data = {
            "id": "test_photo_123",
            "title": "Test Photo for State Manager",
            "url": "https://flickr.com/photo/123"
        }

        result = state_manager.record_post(
            position=1,
            photo_data=test_photo_data,
            instagram_post_id="test_instagram_123",
            title="Test Photo"
        )

        # Check if post was recorded
        posts = state_manager.get_instagram_posts()
        if posts and len(posts) >= 1:
            test_results["post_recording"] = True
            logging.info("✓ Post recording successful")
        else:
            test_results["errors"].append("Failed to record post")

        # Test failed position recording
        if state_manager.record_failed_position(2, "test_photo_456", "Test error"):
            failed_positions = state_manager.get_failed_positions()
            if 2 in failed_positions:
                test_results["failed_position_recording"] = True
                logging.info("✓ Failed position recording successful")
            else:
                test_results["errors"].append("Failed position not found in list")
        else:
            test_results["errors"].append("Failed to record failed position")

        # Test statistics
        stats = state_manager.get_statistics()
        if stats and "album_id" in stats:
            test_results["statistics_generation"] = True
            logging.info("✓ Statistics generation successful")
        else:
            test_results["errors"].append("Failed to generate statistics")

        # Test album completion check
        is_complete = state_manager.is_album_complete(10)
        if isinstance(is_complete, bool):
            test_results["album_completion_check"] = True
            logging.info("✓ Album completion check successful")
        else:
            test_results["errors"].append("Album completion check failed")

    except Exception as e:
        test_results["errors"].append(f"State manager test failed: {e}")
        logging.error(f"Enhanced state manager test failed: {e}")

    return test_results


def run_all_tests(repo_name: str) -> Dict[str, Any]:
    """Run all tests and compile results."""
    logging.info("Starting comprehensive tests for new storage system...")

    try:
        config = Config()
    except Exception as e:
        return {"error": f"Failed to load config: {e}"}

    all_results = {
        "test_started_at": datetime.now().isoformat(),
        "storage_adapter_tests": {},
        "enhanced_models_tests": {},
        "enhanced_state_manager_tests": {},
        "overall_success": False,
        "total_errors": 0
    }

    # Test storage adapter
    all_results["storage_adapter_tests"] = test_storage_adapter(repo_name, config.github_token)

    # Test enhanced models
    all_results["enhanced_models_tests"] = test_enhanced_models()

    # Test enhanced state manager
    all_results["enhanced_state_manager_tests"] = test_enhanced_state_manager(config, repo_name)

    # Calculate overall results
    total_errors = 0
    for test_category in [all_results["storage_adapter_tests"],
                         all_results["enhanced_models_tests"],
                         all_results["enhanced_state_manager_tests"]]:
        total_errors += len(test_category.get("errors", []))

    all_results["total_errors"] = total_errors
    all_results["overall_success"] = total_errors == 0
    all_results["test_completed_at"] = datetime.now().isoformat()

    return all_results


def main():
    """Main test script entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Test new Git-based storage system")
    parser.add_argument("--repo", required=True, help="Repository name (owner/repo)")
    parser.add_argument("--output", help="Output file for test results (JSON)")

    args = parser.parse_args()

    setup_logging()
    logging.info("Starting storage system tests...")

    # Run tests
    results = run_all_tests(args.repo)

    # Output results
    results_json = json.dumps(results, indent=2, default=str)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(results_json)
        logging.info(f"Test results written to {args.output}")
    else:
        print("\n" + "="*50)
        print("STORAGE SYSTEM TEST RESULTS")
        print("="*50)
        print(results_json)

    # Print summary
    if results["overall_success"]:
        logging.info("✅ All tests passed successfully!")
        print("\n🎉 ALL TESTS PASSED - New storage system is ready for migration!")
    else:
        logging.error(f"❌ Tests failed with {results['total_errors']} errors")
        print(f"\n⚠️  TESTS FAILED - {results['total_errors']} errors found")
        sys.exit(1)


if __name__ == "__main__":
    main()