#!/usr/bin/env python3
"""
State Storage Migration Tool

This script migrates state data from the legacy repository variables system
to the new Git-based file storage system.
"""

import json
import logging
import sys
import argparse
from datetime import datetime
from typing import Dict, Any
from config import Config
from storage_adapter import GitFileStorageAdapter, RepositoryVariableStorageAdapter
from state_manager_legacy import StateManager as LegacyStateManager
from state_manager import StateManager
from state_models import InstagramPost, FailedPosition, AlbumMetadata, migrate_legacy_data


def setup_logging(verbose: bool = False):
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(f'migration_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        ]
    )


def validate_config() -> Config:
    """Validate configuration and requirements."""
    try:
        config = Config()

        # Check required settings
        if not config.github_token:
            raise ValueError("GitHub token is required for migration")

        if not config.flickr_album_id:
            raise ValueError("Flickr album ID is required")

        return config
    except Exception as e:
        logging.error(f"Configuration validation failed: {e}")
        sys.exit(1)


def get_repository_variables(config: Config, repo_name: str) -> Dict[str, str]:
    """Get all repository variables that match state patterns."""
    try:
        from github import Github

        github = Github(config.github_token)
        repo = github.get_repo(repo_name)

        variables = {}
        for var in repo.get_variables():
            if any(pattern in var.name for pattern in ["_INSTA_POSTS_", "_FAILED_POSITIONS_"]):
                variables[var.name] = var.value
                logging.debug(f"Found variable: {var.name} = {var.value[:100]}...")

        return variables
    except Exception as e:
        logging.error(f"Failed to get repository variables: {e}")
        return {}


def analyze_current_data(config: Config, repo_name: str) -> Dict[str, Any]:
    """Analyze current repository variable data."""
    logging.info("Analyzing current repository variable data...")

    variables = get_repository_variables(config, repo_name)

    analysis = {
        "total_variables": len(variables),
        "accounts": set(),
        "albums": set(),
        "posts_by_account": {},
        "failed_by_account": {},
        "data_size_bytes": 0,
        "potential_issues": []
    }

    for var_name, var_value in variables.items():
        analysis["data_size_bytes"] += len(var_value.encode('utf-8'))

        try:
            data = json.loads(var_value) if var_value else []

            if "_INSTA_POSTS_" in var_name:
                # Parse account and album from variable name
                parts = var_name.split("_INSTA_POSTS_")
                if len(parts) == 2:
                    environment = parts[0]
                    album_id = parts[1]

                    account = "primary" if environment == "PRIMARY_ACCOUNT" else "secondary"
                    analysis["accounts"].add(account)
                    analysis["albums"].add(album_id)

                    if account not in analysis["posts_by_account"]:
                        analysis["posts_by_account"][account] = {}
                    analysis["posts_by_account"][account][album_id] = len(data)

                    # Check for data size issues
                    if len(var_value) > 200:  # Approaching 256-char limit
                        analysis["potential_issues"].append(
                            f"Variable {var_name} is {len(var_value)} chars (near 256 limit)"
                        )

            elif "_FAILED_POSITIONS_" in var_name:
                parts = var_name.split("_FAILED_POSITIONS_")
                if len(parts) == 2:
                    environment = parts[0]
                    album_id = parts[1]

                    account = "primary" if environment == "PRIMARY_ACCOUNT" else "secondary"
                    analysis["accounts"].add(account)
                    analysis["albums"].add(album_id)

                    if account not in analysis["failed_by_account"]:
                        analysis["failed_by_account"][account] = {}
                    analysis["failed_by_account"][account][album_id] = len(data)

        except json.JSONDecodeError as e:
            analysis["potential_issues"].append(
                f"Invalid JSON in variable {var_name}: {e}"
            )

    # Convert sets to lists for JSON serialization
    analysis["accounts"] = list(analysis["accounts"])
    analysis["albums"] = list(analysis["albums"])

    return analysis


def perform_migration(config: Config, repo_name: str, dry_run: bool = True) -> Dict[str, Any]:
    """Perform the actual migration from repository variables to Git storage."""
    logging.info(f"Starting migration (dry_run={dry_run})...")

    migration_result = {
        "success": False,
        "dry_run": dry_run,
        "started_at": datetime.now().isoformat(),
        "accounts_migrated": 0,
        "albums_migrated": 0,
        "posts_migrated": 0,
        "failed_positions_migrated": 0,
        "errors": [],
        "warnings": []
    }

    try:
        # Initialize Git storage adapter
        git_adapter = GitFileStorageAdapter(
            repo_name=repo_name,
            github_token=config.github_token
        )

        if not git_adapter.is_available():
            raise Exception("Git storage adapter is not available")

        # Get current repository variables
        variables = get_repository_variables(config, repo_name)

        # Group data by account and album
        data_by_account_album = {}

        for var_name, var_value in variables.items():
            try:
                data = json.loads(var_value) if var_value else []

                if "_INSTA_POSTS_" in var_name:
                    parts = var_name.split("_INSTA_POSTS_")
                    if len(parts) == 2:
                        environment = parts[0]
                        album_id = parts[1]
                        account = "primary" if environment == "PRIMARY_ACCOUNT" else "secondary"

                        key = (account, album_id)
                        if key not in data_by_account_album:
                            data_by_account_album[key] = {"posts": [], "failed": []}
                        data_by_account_album[key]["posts"] = data

                elif "_FAILED_POSITIONS_" in var_name:
                    parts = var_name.split("_FAILED_POSITIONS_")
                    if len(parts) == 2:
                        environment = parts[0]
                        album_id = parts[1]
                        account = "primary" if environment == "PRIMARY_ACCOUNT" else "secondary"

                        key = (account, album_id)
                        if key not in data_by_account_album:
                            data_by_account_album[key] = {"posts": [], "failed": []}
                        data_by_account_album[key]["failed"] = data

            except json.JSONDecodeError as e:
                migration_result["errors"].append(f"Invalid JSON in {var_name}: {e}")

        # Migrate each account/album combination
        for (account, album_id), data in data_by_account_album.items():
            logging.info(f"Migrating {account}/album-{album_id}...")

            try:
                # Convert legacy data to enhanced models
                enhanced_posts, enhanced_failed, metadata = migrate_legacy_data(
                    legacy_posts=data["posts"],
                    legacy_failed=data["failed"],
                    account=account,
                    album_id=album_id
                )

                if not dry_run:
                    # Write posts
                    posts_data = [post.to_dict() for post in enhanced_posts]
                    if git_adapter.write_posts(account, album_id, posts_data):
                        logging.info(f"Migrated {len(enhanced_posts)} posts for {account}/album-{album_id}")
                    else:
                        raise Exception(f"Failed to write posts for {account}/album-{album_id}")

                    # Write failed positions
                    failed_data = [failed.to_dict() for failed in enhanced_failed]
                    if git_adapter.write_failed_positions(account, album_id, failed_data):
                        logging.info(f"Migrated {len(enhanced_failed)} failed positions for {account}/album-{album_id}")
                    else:
                        raise Exception(f"Failed to write failed positions for {account}/album-{album_id}")

                    # Write metadata
                    if git_adapter.write_metadata(account, album_id, metadata.to_dict()):
                        logging.info(f"Created metadata for {account}/album-{album_id}")
                    else:
                        raise Exception(f"Failed to write metadata for {account}/album-{album_id}")

                # Update statistics
                migration_result["posts_migrated"] += len(enhanced_posts)
                migration_result["failed_positions_migrated"] += len(enhanced_failed)
                migration_result["albums_migrated"] += 1

                logging.info(f"Successfully {'planned' if dry_run else 'migrated'} {account}/album-{album_id}")

            except Exception as e:
                error_msg = f"Failed to migrate {account}/album-{album_id}: {e}"
                migration_result["errors"].append(error_msg)
                logging.error(error_msg)

        # Count unique accounts
        accounts = set(account for account, _ in data_by_account_album.keys())
        migration_result["accounts_migrated"] = len(accounts)

        # Migration succeeded if no errors
        migration_result["success"] = len(migration_result["errors"]) == 0
        migration_result["completed_at"] = datetime.now().isoformat()

        if dry_run:
            logging.info("Dry run completed successfully - no data was written")
        else:
            logging.info("Migration completed successfully")

    except Exception as e:
        error_msg = f"Migration failed: {e}"
        migration_result["errors"].append(error_msg)
        logging.error(error_msg)

    return migration_result


def validate_migration(config: Config, repo_name: str) -> Dict[str, Any]:
    """Validate migration by comparing old and new data."""
    logging.info("Validating migration...")

    validation_result = {
        "success": False,
        "accounts_validated": 0,
        "albums_validated": 0,
        "posts_match": 0,
        "failed_positions_match": 0,
        "discrepancies": [],
        "errors": []
    }

    try:
        # Get repository variables (old data)
        variables = get_repository_variables(config, repo_name)

        # Initialize Git adapter (new data)
        git_adapter = GitFileStorageAdapter(
            repo_name=repo_name,
            github_token=config.github_token
        )

        if not git_adapter.is_available():
            raise Exception("Git storage adapter is not available for validation")

        # Group old data by account and album
        old_data = {}
        for var_name, var_value in variables.items():
            try:
                data = json.loads(var_value) if var_value else []

                if "_INSTA_POSTS_" in var_name:
                    parts = var_name.split("_INSTA_POSTS_")
                    if len(parts) == 2:
                        environment = parts[0]
                        album_id = parts[1]
                        account = "primary" if environment == "PRIMARY_ACCOUNT" else "secondary"

                        key = (account, album_id)
                        if key not in old_data:
                            old_data[key] = {"posts": [], "failed": []}
                        old_data[key]["posts"] = data

                elif "_FAILED_POSITIONS_" in var_name:
                    parts = var_name.split("_FAILED_POSITIONS_")
                    if len(parts) == 2:
                        environment = parts[0]
                        album_id = parts[1]
                        account = "primary" if environment == "PRIMARY_ACCOUNT" else "secondary"

                        key = (account, album_id)
                        if key not in old_data:
                            old_data[key] = {"posts": [], "failed": []}
                        old_data[key]["failed"] = data

            except json.JSONDecodeError as e:
                validation_result["errors"].append(f"Invalid JSON in {var_name}: {e}")

        # Compare with new data
        for (account, album_id), old_account_data in old_data.items():
            try:
                # Get new data
                new_posts_data = git_adapter.read_posts(account, album_id)
                new_failed_data = git_adapter.read_failed_positions(account, album_id)

                # Compare posts
                old_posts = old_account_data["posts"]
                if len(old_posts) == len(new_posts_data):
                    validation_result["posts_match"] += 1
                else:
                    validation_result["discrepancies"].append(
                        f"Post count mismatch for {account}/album-{album_id}: "
                        f"old={len(old_posts)}, new={len(new_posts_data)}"
                    )

                # Compare failed positions
                old_failed = old_account_data["failed"]
                # Extract just the position numbers from new failed data
                new_failed_positions = []
                for item in new_failed_data:
                    if isinstance(item, dict):
                        if not item.get('resolved', False):  # Only count unresolved
                            new_failed_positions.append(item['position'])
                    else:
                        new_failed_positions.append(item)

                if set(old_failed) == set(new_failed_positions):
                    validation_result["failed_positions_match"] += 1
                else:
                    validation_result["discrepancies"].append(
                        f"Failed positions mismatch for {account}/album-{album_id}: "
                        f"old={old_failed}, new={new_failed_positions}"
                    )

                validation_result["albums_validated"] += 1

            except Exception as e:
                error_msg = f"Failed to validate {account}/album-{album_id}: {e}"
                validation_result["errors"].append(error_msg)
                logging.error(error_msg)

        # Count unique accounts
        accounts = set(account for account, _ in old_data.keys())
        validation_result["accounts_validated"] = len(accounts)

        # Validation succeeded if no errors and no discrepancies
        validation_result["success"] = (
            len(validation_result["errors"]) == 0 and
            len(validation_result["discrepancies"]) == 0
        )

        if validation_result["success"]:
            logging.info("Migration validation passed - data matches between systems")
        else:
            logging.warning("Migration validation found issues")

    except Exception as e:
        error_msg = f"Validation failed: {e}"
        validation_result["errors"].append(error_msg)
        logging.error(error_msg)

    return validation_result


def cleanup_repository_variables(config: Config, repo_name: str, dry_run: bool = True) -> Dict[str, Any]:
    """Clean up old repository variables after successful migration."""
    logging.info(f"Cleaning up repository variables (dry_run={dry_run})...")

    cleanup_result = {
        "success": False,
        "dry_run": dry_run,
        "variables_removed": 0,
        "variables_backed_up": 0,
        "errors": []
    }

    try:
        from github import Github

        github = Github(config.github_token)
        repo = github.get_repo(repo_name)

        # Get state-related variables
        variables_to_remove = []
        for var in repo.get_variables():
            if any(pattern in var.name for pattern in ["_INSTA_POSTS_", "_FAILED_POSITIONS_"]):
                variables_to_remove.append((var.name, var.value))

        if not dry_run:
            # Create backup of all variables
            backup_data = {
                "backup_created_at": datetime.now().isoformat(),
                "variables": {name: value for name, value in variables_to_remove}
            }

            backup_filename = f"repository_variables_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(backup_filename, 'w') as f:
                json.dump(backup_data, f, indent=2)
            cleanup_result["variables_backed_up"] = len(variables_to_remove)
            logging.info(f"Created backup file: {backup_filename}")

            # Remove variables
            for var_name, _ in variables_to_remove:
                try:
                    var = repo.get_variable(var_name)
                    var.delete()
                    cleanup_result["variables_removed"] += 1
                    logging.info(f"Removed variable: {var_name}")
                except Exception as e:
                    error_msg = f"Failed to remove variable {var_name}: {e}"
                    cleanup_result["errors"].append(error_msg)
                    logging.error(error_msg)
        else:
            cleanup_result["variables_backed_up"] = len(variables_to_remove)
            logging.info(f"Would remove {len(variables_to_remove)} variables in production run")

        cleanup_result["success"] = len(cleanup_result["errors"]) == 0

    except Exception as e:
        error_msg = f"Cleanup failed: {e}"
        cleanup_result["errors"].append(error_msg)
        logging.error(error_msg)

    return cleanup_result


def main():
    """Main migration script entry point."""
    parser = argparse.ArgumentParser(description="Migrate state storage from repository variables to Git files")
    parser.add_argument("--repo", required=True, help="Repository name (owner/repo)")
    parser.add_argument("--action", choices=["analyze", "migrate", "validate", "cleanup"],
                       default="analyze", help="Action to perform")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Perform dry run (default)")
    parser.add_argument("--execute", action="store_true", help="Execute for real (overrides dry-run)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--output", help="Output file for results (JSON)")

    args = parser.parse_args()

    # Set up logging
    setup_logging(args.verbose)

    # Determine if this is a dry run
    dry_run = not args.execute

    logging.info(f"Starting migration tool - Action: {args.action}, Dry Run: {dry_run}")

    # Validate configuration
    config = validate_config()

    # Perform requested action
    result = None

    if args.action == "analyze":
        result = analyze_current_data(config, args.repo)

    elif args.action == "migrate":
        result = perform_migration(config, args.repo, dry_run)

    elif args.action == "validate":
        result = validate_migration(config, args.repo)

    elif args.action == "cleanup":
        result = cleanup_repository_variables(config, args.repo, dry_run)

    # Output results
    if result:
        result_json = json.dumps(result, indent=2, default=str)

        if args.output:
            with open(args.output, 'w') as f:
                f.write(result_json)
            logging.info(f"Results written to {args.output}")
        else:
            print("\n" + "="*50)
            print("MIGRATION RESULTS")
            print("="*50)
            print(result_json)

    # Exit with appropriate code
    if result and not result.get("success", False):
        sys.exit(1)
    else:
        logging.info("Migration tool completed successfully")


if __name__ == "__main__":
    main()