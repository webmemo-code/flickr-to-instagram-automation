"""
Configuration management for Flickr to Instagram automation.
All sensitive credentials are loaded from environment variables.
"""
import os
from typing import Dict, Optional


class Config:
    """Configuration class for social media automation."""
    
    def __init__(self):
        self.flickr_api_key = os.getenv('FLICKR_API_KEY')
        self.flickr_user_id = os.getenv('FLICKR_USER_ID')
        self.flickr_username = os.getenv('FLICKR_USERNAME')  # New: Flickr username for URLs
        self.instagram_access_token = os.getenv('INSTAGRAM_ACCESS_TOKEN')
        self.instagram_account_id = os.getenv('INSTAGRAM_ACCOUNT_ID')
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.github_token = os.getenv('GITHUB_TOKEN')
        
        # API endpoints and versions
        self.flickr_api_url = 'https://www.flickr.com/services/rest/'
        self.graph_api_domain = 'https://graph.facebook.com/'
        self.graph_api_version = os.getenv('GRAPH_API_VERSION', 'v18.0')  # Default to v18.0
        self.openai_model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')  # Default to gpt-4o-mini
        
        # Validate required environment variables
        self._validate_config()
    
    def _validate_config(self):
        """Validate that all required environment variables are set."""
        required_vars = {
            'FLICKR_API_KEY': self.flickr_api_key,
            'FLICKR_USER_ID': self.flickr_user_id,
            'FLICKR_USERNAME': self.flickr_username,
            'INSTAGRAM_ACCESS_TOKEN': self.instagram_access_token,
            'INSTAGRAM_ACCOUNT_ID': self.instagram_account_id,
            'OPENAI_API_KEY': self.openai_api_key,
            'GITHUB_TOKEN': self.github_token,
        }
        
        missing_vars = [var for var, value in required_vars.items() if not value]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    @property
    def graph_endpoint_base(self) -> str:
        """Get the complete Graph API endpoint base URL."""
        return f"{self.graph_api_domain}{self.graph_api_version}/"
    
    @property
    def flickr_album_id(self) -> str:
        """Get the Flickr album ID to process."""
        # Set your specific album ID here
        return '72177720326826937'  # Istrien - Gourmet Fine Dining
    
    @property
    def album_name(self) -> str:
        """Get the album name for logging and state management."""
        return 'Istrien'
    
    @property
    def album_url(self) -> str:
        """Get the Flickr album URL."""
        return f"https://flickr.com/photos/{self.flickr_username}/albums/{self.flickr_album_id}"