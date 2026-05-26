"""
Threads API integration for delayed cross-posting of Instagram photos.

Threads (Meta's microblogging service) exposes a Graph-style API at
graph.threads.net. Posts use a two-step container-then-publish flow
analogous to the Instagram Graph API, but on a separate domain and
with a 500-character text limit.

Docs: https://developers.facebook.com/docs/threads/posts
"""
import logging
import time
from typing import Optional

import requests

from config import Config


# Threads recommends waiting at least 30 seconds between container creation
# and publish so server-side processing completes before publish is attempted.
_PUBLISH_DELAY_SECONDS = 30


class ThreadsAPI:
    """Threads Graph API client for posting a single image thread."""

    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)

    def _validate_credentials(self) -> bool:
        if not self.config.threads_user_id:
            self.logger.error(
                "Threads user ID is not configured. "
                "Set THREADS_USER_ID in the GitHub environment secrets."
            )
            return False
        if not self.config.threads_access_token:
            self.logger.error(
                "Threads access token is not configured. "
                "Set THREADS_ACCESS_TOKEN in the GitHub environment secrets."
            )
            return False
        return True

    def _log_api_error(self, phase: str, response: requests.Response) -> None:
        """Log a Threads API error with actionable guidance for common cases."""
        try:
            error_data = response.json()
            error = error_data.get('error', {}) if isinstance(error_data, dict) else {}
            error_msg = error.get('message', 'Unknown error')
            error_code = error.get('code', 'Unknown code')
            self.logger.error(
                f"Threads API {phase} error {response.status_code}: {error_code} - {error_msg}"
            )
            self.logger.error(f"Full error response: {error_data}")
            if error_code == 190 or 'access token' in str(error_msg).lower():
                self.logger.error(
                    "OAuth token error: The Threads access token is invalid or expired. "
                    "Renew it and update THREADS_ACCESS_TOKEN in the GitHub environment secrets."
                )
        except Exception:
            self.logger.error(
                f"Threads API {phase} error {response.status_code}: {response.text}"
            )

    def create_media_container(self, image_url: str, text: str) -> Optional[str]:
        """Create a Threads media container for an image post.

        Returns the container ID on success, None on failure.
        """
        if not self._validate_credentials():
            return None

        endpoint = f"{self.config.threads_endpoint_base}{self.config.threads_user_id}/threads"
        params = {
            'media_type': 'IMAGE',
            'image_url': image_url,
            'text': text,
            'access_token': self.config.threads_access_token,
        }

        try:
            self.logger.debug(f"Creating Threads media container at: {endpoint}")
            self.logger.debug(
                f"Request: image_url={image_url[:100]}..., text length={len(text)}"
            )
            response = requests.post(endpoint, data=params, timeout=60)

            if response.status_code != 200:
                self._log_api_error('container', response)
                return None

            data = response.json()
            container_id = data.get('id') if isinstance(data, dict) else None
            if container_id:
                self.logger.info(f"Created Threads media container: {container_id}")
                return container_id

            self.logger.error(f"Failed to create Threads media container: {data}")
            return None

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to create Threads media container: {e}")
            return None

    def publish_media_container(self, creation_id: str) -> Optional[str]:
        """Publish a previously-created Threads media container."""
        endpoint = (
            f"{self.config.threads_endpoint_base}"
            f"{self.config.threads_user_id}/threads_publish"
        )
        params = {
            'creation_id': creation_id,
            'access_token': self.config.threads_access_token,
        }

        try:
            self.logger.debug(f"Publishing Threads container {creation_id} at: {endpoint}")
            response = requests.post(endpoint, data=params, timeout=60)

            if response.status_code != 200:
                self._log_api_error('publish', response)
                return None

            data = response.json()
            post_id = data.get('id') if isinstance(data, dict) else None
            if post_id:
                self.logger.info(f"Published Threads post: {post_id}")
                return post_id

            self.logger.error(f"Failed to publish Threads container: {data}")
            return None

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to publish Threads container: {e}")
            return None

    def post_photo(self, image_url: str, text: str,
                   publish_delay_seconds: int = _PUBLISH_DELAY_SECONDS) -> Optional[str]:
        """Post a photo to Threads (create container, wait, publish)."""
        container_id = self.create_media_container(image_url, text)
        if not container_id:
            return None

        if publish_delay_seconds > 0:
            self.logger.info(
                f"Waiting {publish_delay_seconds}s for Threads to process media container"
            )
            time.sleep(publish_delay_seconds)

        post_id = self.publish_media_container(container_id)
        if post_id:
            self.logger.info(f"Successfully posted to Threads: {post_id}")
        else:
            self.logger.error("Failed to publish to Threads")
        return post_id

    def post_with_retry(self, image_url: str, text: str,
                        max_retries: int = 3, initial_wait: int = 30,
                        publish_delay_seconds: int = _PUBLISH_DELAY_SECONDS) -> Optional[str]:
        """Post to Threads with retry logic on the publish step.

        Creates the container once (container creation failures usually indicate a
        bad image URL or bad credentials and shouldn't be retried blindly), then
        retries the publish step with exponential backoff to absorb transient
        "media still processing" errors.
        """
        if not self._validate_credentials():
            return None

        container_id = self.create_media_container(image_url, text)
        if not container_id:
            self.logger.error("Failed to create Threads media container - aborting")
            return None

        for attempt in range(max_retries):
            if attempt == 0:
                if publish_delay_seconds > 0:
                    self.logger.info(
                        f"Waiting {publish_delay_seconds}s for Threads to process container"
                    )
                    time.sleep(publish_delay_seconds)
            else:
                wait_time = initial_wait * (2 ** (attempt - 1))  # 30s, 60s, 120s
                self.logger.info(
                    f"Waiting {wait_time}s before Threads publish retry "
                    f"{attempt + 1}/{max_retries}"
                )
                time.sleep(wait_time)

            try:
                post_id = self.publish_media_container(container_id)
                if post_id:
                    return post_id
                self.logger.warning(
                    f"Threads publish attempt {attempt + 1}/{max_retries} failed"
                )
            except Exception as e:
                self.logger.warning(
                    f"Threads publish attempt {attempt + 1}/{max_retries} raised: {e}"
                )

        self.logger.error(
            f"Failed to publish Threads container {container_id} after {max_retries} attempts"
        )
        return None
