"""
Configuration updates for new storage system.

This module extends the existing config to support storage backend selection
and migration settings.
"""

import os
from typing import Optional
from config import Config as BaseConfig


class EnhancedConfig(BaseConfig):
    """Enhanced configuration with storage backend support."""

    def __init__(self, account: str = 'primary', email_test_mode: bool = False,
                 skip_environment_validation: bool = False):
        """Initialize enhanced configuration."""
        super().__init__(account, email_test_mode, skip_environment_validation)

        # Storage backend configuration
        self.storage_backend = os.getenv('STORAGE_BACKEND', 'auto')  # auto, git, repository_variables
        self.enable_parallel_writes = os.getenv('ENABLE_PARALLEL_WRITES', 'false').lower() == 'true'
        self.storage_branch = os.getenv('STORAGE_BRANCH', 'automation-state')

        # Migration settings
        self.migration_mode = os.getenv('MIGRATION_MODE', 'disabled')  # disabled, testing, active
        self.migration_backup_enabled = os.getenv('MIGRATION_BACKUP_ENABLED', 'true').lower() == 'true'

        # Feature flags for new storage system
        self.enhanced_metadata_enabled = os.getenv('ENHANCED_METADATA_ENABLED', 'true').lower() == 'true'
        self.retry_tracking_enabled = os.getenv('RETRY_TRACKING_ENABLED', 'true').lower() == 'true'

        # Validation settings
        self.validate_storage_on_startup = os.getenv('VALIDATE_STORAGE_ON_STARTUP', 'true').lower() == 'true'
        self.fallback_to_legacy_on_error = os.getenv('FALLBACK_TO_LEGACY_ON_ERROR', 'true').lower() == 'true'

    def get_storage_config(self) -> dict:
        """Get storage-related configuration as a dictionary."""
        return {
            'backend': self.storage_backend,
            'parallel_writes': self.enable_parallel_writes,
            'branch': self.storage_branch,
            'migration_mode': self.migration_mode,
            'enhanced_metadata': self.enhanced_metadata_enabled,
            'retry_tracking': self.retry_tracking_enabled,
            'validate_on_startup': self.validate_storage_on_startup,
            'fallback_to_legacy': self.fallback_to_legacy_on_error
        }

    def is_migration_enabled(self) -> bool:
        """Check if migration mode is active."""
        return self.migration_mode in ['testing', 'active']

    def should_use_enhanced_storage(self) -> bool:
        """Determine if enhanced storage should be used."""
        if self.storage_backend == 'repository_variables':
            return False
        elif self.storage_backend == 'git':
            return True
        else:  # auto
            # Use enhanced storage unless explicitly disabled
            return os.getenv('DISABLE_ENHANCED_STORAGE', 'false').lower() != 'true'


def get_config_for_workflow() -> EnhancedConfig:
    """Get configuration appropriate for workflow context."""
    # Detect account from environment
    account = 'primary'
    if os.getenv('ACCOUNT_FLAG') == 'reisememo':
        account = 'reisememo'

    return EnhancedConfig(account=account)