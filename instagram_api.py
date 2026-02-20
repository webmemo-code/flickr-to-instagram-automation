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
    
    def _validate_credentials(self) -> bool:
        """Validate that Instagram credentials are configured before making API calls."""
        if not self.config.instagram_access_token:
            self.logger.error(
                "Instagram access token is not configured. "
                "Check that INSTAGRAM_ACCESS_TOKEN is set in the GitHub environment secrets."
            )
            return False
        if not self.config.instagram_account_id:
            self.logger.error(
                "Instagram account ID is not configured. "
                "Check that INSTAGRAM_ACCOUNT_ID is set in the GitHub environment secrets."
            )
            return False
        return True

    def create_media_container(self, image_url: str, caption: str) -> Optional[str]:
        """Create a media container for the image."""
        if not self._validate_credentials():
            return None

        endpoint = f"{self.config.graph_endpoint_base}{self.config.instagram_account_id}/media"

        params = {
            'image_url': image_url,
            'caption': caption,
            'access_token': self.config.instagram_access_token
        }

        try:
            self.logger.debug(f"Creating media container at: {endpoint}")
            self.logger.debug(f"Request params: image_url={image_url[:100]}..., caption length={len(caption)}")

            response = requests.post(endpoint, data=params, timeout=60)

            # Enhanced error handling for bad requests
            if response.status_code != 200:
                try:
                    error_data = response.json()
                    error_msg = error_data.get('error', {}).get('message', 'Unknown error')
                    error_code = error_data.get('error', {}).get('code', 'Unknown code')
                    error_subcode = error_data.get('error', {}).get('error_subcode', '')
                    self.logger.error(f"Instagram API Error {response.status_code}: {error_code} - {error_msg}")
                    self.logger.error(f"Full error response: {error_data}")
                    # Provide actionable guidance for OAuth token errors
                    if error_code == 190 or 'access token' in str(error_msg).lower():
                        self.logger.error(
                            "OAuth token error: The Instagram access token is invalid or expired. "
                            "Renew the token and update INSTAGRAM_ACCESS_TOKEN in the GitHub environment secrets."
                        )
                except Exception:
                    self.logger.error(f"Instagram API Error {response.status_code}: {response.text}")
                return None

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
            self.logger.debug(f"Publishing media container at: {endpoint}")
            self.logger.debug(f"Publishing creation_id: {creation_id}")

            response = requests.post(endpoint, data=params, timeout=60)

            # Enhanced error handling for bad requests
            if response.status_code != 200:
                try:
                    error_data = response.json()
                    error_msg = error_data.get('error', {}).get('message', 'Unknown error')
                    error_code = error_data.get('error', {}).get('code', 'Unknown code')
                    self.logger.error(f"Instagram API Publish Error {response.status_code}: {error_code} - {error_msg}")
                    self.logger.error(f"Full publish error response: {error_data}")
                except:
                    self.logger.error(f"Instagram API Publish Error {response.status_code}: {response.text}")
                return None

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
    
    def post_with_retry(self, image_url: str, caption: str,
                        max_retries: int = 3, initial_wait: int = 30) -> Optional[str]:
        """Post to Instagram with retry logic.

        Creates the media container once, then retries only the publish step
        with exponential backoff if publishing fails (e.g., error 9007 - media not ready).
        """
        # Phase 1: Create container (if this fails, the image URL is likely bad)
        container_id = self.create_media_container(image_url, caption)
        if not container_id:
            self.logger.error("Failed to create media container - aborting")
            return None

        # Phase 2: Publish with retry (container may need time to process)
        for attempt in range(max_retries):
            if attempt > 0:
                wait_time = initial_wait * (2 ** (attempt - 1))  # 30s, 60s
                self.logger.info(f"Waiting {wait_time}s before publish attempt {attempt + 1}/{max_retries}")
                time.sleep(wait_time)

            try:
                post_id = self.publish_media_container(container_id)
                if post_id:
                    return post_id
                self.logger.warning(f"Publish attempt {attempt + 1}/{max_retries} failed")
            except Exception as e:
                self.logger.warning(f"Publish attempt {attempt + 1}/{max_retries} raised exception: {e}")

        self.logger.error(f"Failed to publish container {container_id} after {max_retries} attempts")
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