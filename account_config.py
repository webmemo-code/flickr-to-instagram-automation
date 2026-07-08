"""
Account Configuration System

Provides configurable account settings to replace hardcoded 'reisememo' references.
Allows users to define custom secondary account names, languages, and branding.
"""

import os
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class AccountConfig:
    """Configuration for a specific Instagram account."""

    # Account identification
    account_id: str                    # CLI flag (e.g., "reisememo", "mybrand", "secondary")
    display_name: str                  # Human-readable name (e.g., "Reisememo", "My Brand")
    environment_name: str              # GitHub environment (e.g., "secondary-account")

    # Content generation settings
    language: str = "en"               # Language code: "en", "de", "fr", etc.
    caption_style: str = "travel"      # Caption style: "travel", "lifestyle", "business"

    # Branding
    brand_signature: Optional[str] = None     # Custom signature line
    blog_domains: list = None                 # List of blog domains for this account

    # WordPress content-path settings (custom endpoint + outbound request identity)
    wp_endpoint_namespace: str = "travelmemo-content/v1"  # Custom WP REST namespace
    wp_auth_key: str = "tm-post-retrieval"                # Custom endpoint auth_key param
    user_agent: Optional[str] = None                      # Outbound User-Agent; derived from display_name if unset

    def __post_init__(self):
        if self.blog_domains is None:
            self.blog_domains = []
        if self.user_agent is None:
            self.user_agent = f"{self.display_name.replace(' ', '')}-ContentFetcher/1.0"


class AccountConfigManager:
    """Manages account configurations for the automation system."""

    def __init__(self):
        self.accounts = self._load_account_configs()

    def _load_account_configs(self) -> Dict[str, AccountConfig]:
        """Load account configurations from environment variables."""
        accounts = {}

        # Primary account (always exists). Explicit values preserve today's
        # literals byte-for-byte now that the content path reads them from
        # AccountConfig instead of hardcoding them inline.
        accounts['primary'] = AccountConfig(
            account_id='primary',
            display_name='Primary',
            environment_name='primary-account',
            language='en',
            caption_style='travel',
            brand_signature=os.getenv('PRIMARY_BRAND_SIGNATURE') or 'Travelmemo from a one-of-a-kind travel experience.',
            blog_domains=self._get_domains('PRIMARY_BLOG_DOMAINS', ['travelmemo.com', 'reisememo.ch']),
            wp_endpoint_namespace=os.getenv('PRIMARY_WP_ENDPOINT_NAMESPACE') or 'travelmemo-content/v1',
            wp_auth_key=os.getenv('PRIMARY_WP_AUTH_KEY') or 'tm-post-retrieval',
            user_agent=os.getenv('PRIMARY_USER_AGENT') or 'TravelMemo-ContentFetcher/1.0',
        )

        # Secondary account (configurable). `or` (not getenv's default arg) so
        # an empty-string env var - which GitHub Actions `${{ vars.X || '' }}`
        # plumbing exports when a var is unset - doesn't override the default
        # (getenv's default only applies when the var is truly absent).
        secondary_id = os.getenv('SECONDARY_ACCOUNT_ID') or 'reisememo'
        secondary_name = os.getenv('SECONDARY_ACCOUNT_NAME') or 'Reisememo'
        secondary_env = os.getenv('SECONDARY_ENVIRONMENT_NAME') or 'secondary-account'
        secondary_lang = os.getenv('SECONDARY_ACCOUNT_LANGUAGE') or 'en'
        secondary_style = os.getenv('SECONDARY_ACCOUNT_STYLE') or 'travel'
        secondary_signature = os.getenv('SECONDARY_BRAND_SIGNATURE') or None
        secondary_domains = self._get_domains('SECONDARY_BLOG_DOMAINS', ['reisememo.ch', 'travelmemo.com'])
        secondary_namespace = os.getenv('SECONDARY_WP_ENDPOINT_NAMESPACE') or 'travelmemo-content/v1'
        secondary_auth_key = os.getenv('SECONDARY_WP_AUTH_KEY') or 'tm-post-retrieval'
        secondary_user_agent = os.getenv('SECONDARY_USER_AGENT')  # None -> derived from display_name

        accounts[secondary_id] = AccountConfig(
            account_id=secondary_id,
            display_name=secondary_name,
            environment_name=secondary_env,
            language=secondary_lang,
            caption_style=secondary_style,
            brand_signature=secondary_signature,
            blog_domains=secondary_domains,
            wp_endpoint_namespace=secondary_namespace,
            wp_auth_key=secondary_auth_key,
            user_agent=secondary_user_agent,
        )

        return accounts

    def _get_domains(self, env_var: str, default: list) -> list:
        """Parse blog domains from environment variable."""
        domains_str = os.getenv(env_var, '')
        if domains_str:
            return [domain.strip() for domain in domains_str.split(',') if domain.strip()]
        return default

    def get_account(self, account_id: str) -> Optional[AccountConfig]:
        """Get account configuration by ID."""
        return self.accounts.get(account_id)

    def get_secondary_account_id(self) -> str:
        """Get the configured secondary account ID."""
        return os.getenv('SECONDARY_ACCOUNT_ID') or 'reisememo'

    def is_secondary_account(self, account_id: str) -> bool:
        """Check if the given account ID is the secondary account."""
        return account_id == self.get_secondary_account_id()

    def get_all_account_ids(self) -> list:
        """Get list of all configured account IDs."""
        return list(self.accounts.keys())

    def get_environment_name(self, account_id: str) -> str:
        """Get GitHub environment name for account."""
        account = self.get_account(account_id)
        return account.environment_name if account else 'primary-account'


# Global instance for easy access
account_manager = AccountConfigManager()


def get_account_config(account_id: str) -> Optional[AccountConfig]:
    """Convenience function to get account configuration."""
    return account_manager.get_account(account_id)


def get_secondary_account_id() -> str:
    """Convenience function to get secondary account ID."""
    return account_manager.get_secondary_account_id()


def is_secondary_account(account_id: str) -> bool:
    """Convenience function to check if account is secondary."""
    return account_manager.is_secondary_account(account_id)
