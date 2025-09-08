"""
Configuration management for Flickr to Instagram automation.
All sensitive credentials are loaded from environment variables.
"""
import os
from typing import Dict, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration class for social media automation."""
    
    def __init__(self, account: str = 'primary', email_test_mode: bool = False):
        """Initialize configuration for specified account.
        
        Args:
            account: Account type - 'primary' (default) or 'reisememo'
            email_test_mode: Skip validation for email testing mode
        """
        self.account = account
        
        # Common configuration (shared between accounts)
        self.flickr_api_key = os.getenv('FLICKR_API_KEY')
        self.flickr_user_id = os.getenv('FLICKR_USER_ID')
        self.flickr_username = os.getenv('FLICKR_USERNAME')  # Flickr username for URLs
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.github_token = os.getenv('GITHUB_TOKEN')
        
        # Account-specific configuration
        if account == 'reisememo':
            self.flickr_album_id = os.getenv('FLICKR_ALBUM_ID')
            self.instagram_access_token = os.getenv('INSTAGRAM_ACCESS_TOKEN_REISEMEMO')
            self.instagram_account_id = os.getenv('INSTAGRAM_ACCOUNT_ID_REISEMEMO')
            self.instagram_app_id = os.getenv('INSTAGRAM_APP_ID_REISEMEMO')  # Optional
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
        
        # Email notification settings (optional)
        self.notification_email = os.getenv('NOTIFICATION_EMAIL')  # Manager's email address
        self.smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')  # SMTP server
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))  # SMTP port
        self.smtp_username = os.getenv('SMTP_USERNAME')  # Email account for sending
        self.smtp_password = os.getenv('SMTP_PASSWORD')  # Email password/app password
        
        # Validate required environment variables (skip for email test mode)
        if not email_test_mode:
            self._validate_config()
        else:
            # Provide mock values for email testing
            self.flickr_username = self.flickr_username or "testuser"
            self.flickr_album_id = self.flickr_album_id or "12345678"
    
    def _validate_config(self):
        """Validate that all required environment variables are set."""
        # Common required variables
        required_vars = {
            'FLICKR_API_KEY': self.flickr_api_key,
            'FLICKR_USER_ID': self.flickr_user_id,
            'FLICKR_USERNAME': self.flickr_username,
            'OPENAI_API_KEY': self.openai_api_key,
            'GITHUB_TOKEN': self.github_token,
        }
        
        # Account-specific required variables
        if self.account == 'reisememo':
            required_vars.update({
                'FLICKR_ALBUM_ID': self.flickr_album_id,
                'INSTAGRAM_ACCESS_TOKEN_REISEMEMO': self.instagram_access_token,
                'INSTAGRAM_ACCOUNT_ID_REISEMEMO': self.instagram_account_id,
            })
        else:  # primary account
            required_vars.update({
                'FLICKR_ALBUM_ID': self.flickr_album_id,
                'INSTAGRAM_ACCESS_TOKEN': self.instagram_access_token,
                'INSTAGRAM_ACCOUNT_ID': self.instagram_account_id,
            })
        
        missing_vars = [var for var, value in required_vars.items() if not value]
        if missing_vars:
            account_info = f" for {self.account} account" if self.account != 'primary' else ""
            raise ValueError(f"Missing required environment variables{account_info}: {', '.join(missing_vars)}")
    
    @property
    def graph_endpoint_base(self) -> str:
        """Get the complete Graph API endpoint base URL."""
        return f"{self.graph_api_domain}{self.graph_api_version}/"
    
    @property
    def album_name(self) -> str:
        """Get the album name for logging and state management."""
        if self.account == 'reisememo':
            return 'Reisememo'
        
        # For primary account, try to get dynamic album name
        try:
            from flickr_api import FlickrAPI
            flickr_api = FlickrAPI(self)
            photoset_info = flickr_api.get_photoset_info(self.flickr_album_id)
            if photoset_info and 'photoset' in photoset_info:
                return photoset_info['photoset']['title']['_content']
        except:
            pass  # Fall back to default if API call fails
        
        return 'Istrien'
    
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