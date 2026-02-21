"""
Facebook Page API integration for cross-posting photos.
"""
import requests
import time
import logging
from typing import Optional, Dict
from config import Config


class FacebookPageAPI:
    """Facebook Graph API client for posting photos to a Facebook Page."""

    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)

    def _validate_credentials(self) -> bool:
        """Validate that Facebook Page credentials are configured."""
        if not self.config.facebook_page_id:
            self.logger.error(
                "Facebook Page ID is not configured. "
                "Set FACEBOOK_PAGE_ID in the GitHub environment secrets."
            )
            return False
        if not self.config.facebook_page_access_token:
            self.logger.error(
                "Facebook Page access token is not configured. "
                "Set FACEBOOK_PAGE_ACCESS_TOKEN in the GitHub environment secrets."
            )
            return False
        return True

    def post_photo(self, image_url: str, caption: str) -> Optional[str]:
        """Post a photo to the Facebook Page.

        Uses the /{page-id}/photos endpoint which accepts a remote image URL
        and publishes it as a Page photo post.

        Returns the photo post ID on success, None on failure.
        """
        if not self._validate_credentials():
            return None

        endpoint = (
            f"https://graph.facebook.com/{self.config.graph_api_version}/"
            f"{self.config.facebook_page_id}/photos"
        )

        params = {
            'url': image_url,
            'message': caption,
            'access_token': self.config.facebook_page_access_token
        }

        try:
            self.logger.debug(f"Posting photo to Facebook Page at: {endpoint}")

            response = requests.post(endpoint, data=params, timeout=60)

            if response.status_code != 200:
                try:
                    error_data = response.json()
                    error_msg = error_data.get('error', {}).get('message', 'Unknown error')
                    error_code = error_data.get('error', {}).get('code', 'Unknown code')
                    self.logger.error(f"Facebook API Error {response.status_code}: {error_code} - {error_msg}")
                    self.logger.error(f"Full error response: {error_data}")
                    if error_code == 190 or 'access token' in str(error_msg).lower():
                        self.logger.error(
                            "OAuth token error: The Facebook Page access token is invalid or expired. "
                            "Renew the token and update FACEBOOK_PAGE_ACCESS_TOKEN in the GitHub environment secrets."
                        )
                except Exception:
                    self.logger.error(f"Facebook API Error {response.status_code}: {response.text}")
                return None

            data = response.json()
            if 'id' in data:
                self.logger.info(f"Posted photo to Facebook Page: {data['id']}")
                return data['id']
            else:
                self.logger.error(f"Failed to post photo to Facebook Page: {data}")
                return None

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to post photo to Facebook Page: {e}")
            return None

    def post_with_retry(self, image_url: str, caption: str,
                        max_retries: int = 3, initial_wait: int = 30) -> Optional[str]:
        """Post to Facebook Page with retry logic and exponential backoff."""
        for attempt in range(max_retries):
            if attempt > 0:
                wait_time = initial_wait * (2 ** (attempt - 1))  # 30s, 60s
                self.logger.info(f"Waiting {wait_time}s before Facebook retry {attempt + 1}/{max_retries}")
                time.sleep(wait_time)

            try:
                post_id = self.post_photo(image_url, caption)
                if post_id:
                    return post_id
                self.logger.warning(f"Facebook post attempt {attempt + 1}/{max_retries} failed")
            except Exception as e:
                self.logger.warning(f"Facebook post attempt {attempt + 1}/{max_retries} raised exception: {e}")

        self.logger.error(f"Failed to post to Facebook Page after {max_retries} attempts")
        return None
