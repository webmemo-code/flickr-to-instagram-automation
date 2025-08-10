"""
Instagram Graph API integration for posting photos.
"""
import requests
import json
import time
import logging
from typing import Optional, Dict
from config import Config


class InstagramAPI:
    """Instagram Graph API client for posting photos."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def create_media_container(self, image_url: str, caption: str) -> Optional[str]:
        """Create a media container for the image."""
        endpoint = f"{self.config.graph_endpoint_base}{self.config.instagram_account_id}/media"
        
        params = {
            'image_url': image_url,
            'caption': caption,
            'access_token': self.config.instagram_access_token
        }
        
        try:
            response = requests.post(endpoint, data=params, timeout=60)
            response.raise_for_status()
            
            data = response.json()
            if 'id' in data:
                self.logger.info(f"Created media container: {data['id']}")
                return data['id']
            else:
                self.logger.error(f"Failed to create media container: {data}")
                return None
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to create media container: {e}")
            return None
    
    def publish_media_container(self, creation_id: str) -> Optional[str]:
        """Publish the media container to Instagram."""
        endpoint = f"{self.config.graph_endpoint_base}{self.config.instagram_account_id}/media_publish"
        
        params = {
            'creation_id': creation_id,
            'access_token': self.config.instagram_access_token
        }
        
        try:
            response = requests.post(endpoint, data=params, timeout=60)
            response.raise_for_status()
            
            data = response.json()
            if 'id' in data:
                self.logger.info(f"Published post: {data['id']}")
                return data['id']
            else:
                self.logger.error(f"Failed to publish media container: {data}")
                return None
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to publish media container: {e}")
            return None
    
    def post_photo(self, image_url: str, caption: str) -> Optional[str]:
        """Post a photo to Instagram with the given caption."""
        # Step 1: Create media container
        container_id = self.create_media_container(image_url, caption)
        if not container_id:
            return None
        
        # Step 2: Publish the media container
        post_id = self.publish_media_container(container_id)
        
        if post_id:
            self.logger.info(f"Successfully posted to Instagram: {post_id}")
        else:
            self.logger.error("Failed to publish to Instagram")
        
        return post_id
    
    def post_with_retry(self, image_url: str, caption: str, max_retries: int = 3) -> Optional[str]:
        """Post to Instagram with retry logic."""
        for attempt in range(max_retries):
            try:
                post_id = self.post_photo(image_url, caption)
                if post_id:
                    return post_id
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    self.logger.warning(f"Posting failed, waiting {wait_time} seconds before retry {attempt + 1}")
                    time.sleep(wait_time)
                    continue
                else:
                    self.logger.error(f"Failed to post after {attempt + 1} attempts: {e}")
                    break
        
        return None
    
    def check_api_limits(self) -> Dict:
        """Check Instagram API rate limits."""
        endpoint = f"{self.config.graph_endpoint_base}{self.config.instagram_account_id}"
        
        params = {
            'fields': 'id,username',
            'access_token': self.config.instagram_access_token
        }
        
        try:
            response = requests.get(endpoint, params=params, timeout=30)
            
            # Check rate limit headers
            rate_limit_info = {
                'calls_remaining': response.headers.get('X-App-Usage'),
                'reset_time': response.headers.get('X-API-Version'),
                'status_code': response.status_code
            }
            
            self.logger.info(f"API rate limit info: {rate_limit_info}")
            return rate_limit_info
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to check API limits: {e}")
            return {}
    
    def validate_image_url(self, image_url: str, max_retries: int = 2, retry_delay: int = 60) -> bool:
        """Validate that the image URL is accessible, with retry logic for temporary failures."""
        for attempt in range(max_retries):
            try:
                response = requests.head(image_url, timeout=10)
                if response.status_code == 200:
                    content_type = response.headers.get('content-type', '')
                    if content_type.startswith('image/'):
                        if attempt > 0:
                            self.logger.info(f"✅ Image URL became accessible on retry #{attempt}")
                        return True
                    else:
                        self.logger.warning(f"URL does not point to an image: {content_type}")
                        return False
                else:
                    self.logger.warning(f"Image URL not accessible: {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Failed to validate image URL (attempt {attempt + 1}): {e}")
            
            # If this wasn't the last attempt, wait and retry
            if attempt < max_retries - 1:
                self.logger.info(f"⏳ Waiting {retry_delay} seconds before retrying image URL validation...")
                time.sleep(retry_delay)
                continue
                
        self.logger.error(f"❌ Image URL validation failed after {max_retries} attempts")
        return False