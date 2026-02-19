"""
Configuration management for Flickr to Instagram automation.
All sensitive credentials are loaded from environment variables.
"""
import os
from typing import Dict, Optional, List
from dotenv import load_dotenv
import re
from account_config import get_account_config, is_secondary_account, get_secondary_account_id

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration class for social media automation."""

    def __init__(self, account: str = 'primary', email_test_mode: bool = False, skip_environment_validation: bool = False):
        """Initialize configuration for specified account.

        Args:
            account: Account type - 'primary' (default) or secondary account ID
            email_test_mode: Skip validation for email testing mode
            skip_environment_validation: Skip validation of environment-specific variables (for secondary account workflow validation step)
        """
        self.account = account
        self.account_config = get_account_config(account)
        
        # Common configuration (shared between accounts)
        self.flickr_api_key = os.getenv('FLICKR_API_KEY')
        self.flickr_user_id = os.getenv('FLICKR_USER_ID')
        self.flickr_username = os.getenv('FLICKR_USERNAME')  # Flickr username for URLs
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.github_token = os.getenv('GITHUB_TOKEN')

        # WordPress credentials for authenticated content access
        self.wordpress_username = os.getenv('WORDPRESS_USERNAME')
        self.wordpress_app_password = os.getenv('WORDPRESS_APP_PASSWORD')
        
        # Account-specific configuration
        if is_secondary_account(account):
            # Secondary account - use environment-specific variables
            self.flickr_album_id = os.getenv('FLICKR_ALBUM_ID')
            self.instagram_access_token = os.getenv('INSTAGRAM_ACCESS_TOKEN')
            self.instagram_account_id = os.getenv('INSTAGRAM_ACCOUNT_ID')
            self.instagram_app_id = os.getenv(f'INSTAGRAM_APP_ID_{account.upper()}')  # Optional
        else:  # primary account (default)
            self.flickr_album_id = os.getenv('FLICKR_ALBUM_ID')
            self.instagram_access_token = os.getenv('INSTAGRAM_ACCESS_TOKEN')
            self.instagram_account_id = os.getenv('INSTAGRAM_ACCOUNT_ID')
            self.instagram_app_id = os.getenv('INSTAGRAM_APP_ID')  # Optional
        
        # API endpoints and versions
        self.flickr_api_url = 'https://www.flickr.com/services/rest/'
        self.graph_api_domain = 'https://graph.facebook.com/'
        self.graph_api_version = os.getenv('GRAPH_API_VERSION', 'v18.0')  # Default to v18.0
        self.openai_model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')  # Default to gpt-4o-mini
        
        # State management options
        self.create_audit_issues = os.getenv('CREATE_AUDIT_ISSUES', 'false').lower() == 'true'  # Default: disabled for scale
        
        # Optional blog post URL for enhanced caption generation
        self.blog_post_url = os.getenv('BLOG_POST_URL')  # Optional: URL to blog post with photo descriptions
        raw_blog_urls = os.getenv('BLOG_POST_URLS', '')
        self.blog_post_urls = self._parse_blog_post_urls(raw_blog_urls)

        
        # Email notification settings (optional)
        self.notification_email = os.getenv('NOTIFICATION_EMAIL')  # Manager's email address
        self.smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')  # SMTP server

        # Handle SMTP_PORT safely - default to 587 if empty or invalid
        smtp_port_str = os.getenv('SMTP_PORT', '587').strip()
        try:
            self.smtp_port = int(smtp_port_str) if smtp_port_str else 587
        except ValueError:
            self.smtp_port = 587

        self.smtp_username = os.getenv('SMTP_USERNAME')  # Email account for sending
        self.smtp_password = os.getenv('SMTP_PASSWORD')  # Email password/app password
        
        # Validate required environment variables (skip for email test mode or environment validation step)
        if not email_test_mode and not skip_environment_validation:
            self._validate_config()
        elif email_test_mode:
            # Provide mock values for email testing
            self.flickr_username = self.flickr_username or "testuser"
            self.flickr_album_id = self.flickr_album_id or "12345678"
        # If skip_environment_validation is True, don't validate environment-specific variables
        # This allows the workflow validation step to run before environment scope is available
    
    def _validate_config(self):
        """Validate that all required environment variables are set."""
        # Common required variables (these should always be available at repository level)
        required_vars = {
            'FLICKR_API_KEY': self.flickr_api_key,
            'FLICKR_USER_ID': self.flickr_user_id,
            'FLICKR_USERNAME': self.flickr_username,
            'OPENAI_API_KEY': self.openai_api_key,
            'GITHUB_TOKEN': self.github_token,
        }

        # Account-specific required variables
        # For secondary accounts, these are environment-specific and might not be available during early workflow validation
        account_specific_vars = {
            'FLICKR_ALBUM_ID': self.flickr_album_id,
            'INSTAGRAM_ACCESS_TOKEN': self.instagram_access_token,
            'INSTAGRAM_ACCOUNT_ID': self.instagram_account_id,
        }

        # Always check common variables
        missing_common = [var for var, value in required_vars.items() if not value]
        if missing_common:
            account_info = f" for {self.account} account" if self.account != 'primary' else ""
            raise ValueError(f"Missing required repository-level environment variables{account_info}: {', '.join(missing_common)}")

        # For account-specific variables, only validate if we have at least one of them
        # This allows for the workflow validation step to run before environment scope
        missing_account_specific = [var for var, value in account_specific_vars.items() if not value]
        if missing_account_specific:
            # If we have NONE of the account-specific variables, this might be the validation step
            if len(missing_account_specific) == len(account_specific_vars):
                # All account-specific variables are missing - this might be expected during validation step
                import os
                if os.getenv('GITHUB_ACTIONS') and is_secondary_account(self.account):
                    # We're in GitHub Actions for secondary account and all account-specific vars are missing
                    # This is expected for the validation step that runs outside environment scope
                    print(f"Warning: Account-specific variables not available yet for {self.account} account (expected during validation step)")
                    return

            # If we have some but not all, or if this is primary account, it's an error
            account_info = f" for {self.account} account" if self.account != 'primary' else ""
            raise ValueError(f"Missing required account-specific environment variables{account_info}: {', '.join(missing_account_specific)}")
    
    def _parse_blog_post_urls(self, raw_urls: str) -> List[str]:
        """Parse multi-value blog post URLs from configuration."""
        if not raw_urls:
            return []

        parts = re.split(r'[;,\n]', raw_urls)
        cleaned = []
        seen = set()
        for part in parts:
            url = part.strip()
            if not url:
                continue
            if url in seen:
                continue
            cleaned.append(url)
            seen.add(url)
        return cleaned

    def get_default_blog_post_url(self) -> Optional[str]:
        """Return the primary blog post URL if available."""
        if self.blog_post_urls:
            return self.blog_post_urls[0]
        return self.blog_post_url

    @property
    def graph_endpoint_base(self) -> str:
        """Get the complete Graph API endpoint base URL."""
        return f"{self.graph_api_domain}{self.graph_api_version}/"
    
    @property
    def album_name(self) -> str:
        """Get the album name for logging and state management."""
        # Use configured display name for secondary accounts
        if is_secondary_account(self.account):
            return self.account_config.display_name

        # For primary account, try to get dynamic album name from Flickr
        try:
            from flickr_api import FlickrAPI
            flickr_api = FlickrAPI(self)
            photoset_info = flickr_api.get_photoset_info(self.flickr_album_id)
            if photoset_info and 'photoset' in photoset_info:
                return photoset_info['photoset']['title']['_content']
        except:
            pass  # Fall back to default if API call fails

        # Default fallback for primary account
        return 'Primary Album'
    
    @property
    def album_url(self) -> str:
        """Get the Flickr album URL."""
        return f"https://flickr.com/photos/{self.flickr_username}/albums/{self.flickr_album_id}"
    
    @property
    def email_notifications_enabled(self) -> bool:
        """Check if email notifications are properly configured."""
        return all([
            self.notification_email,
            self.smtp_username,
            self.smtp_password
        ])