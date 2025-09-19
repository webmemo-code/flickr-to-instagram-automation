"""
Custom WordPress endpoint integration for bypassing Cloudflare bot protection.
"""
import requests
import logging
from typing import Optional, Dict
from urllib.parse import urlparse


class CustomEndpointExtractor:
    """Extract blog content using custom WordPress endpoint."""

    def __init__(self, config):
        """Initialize the custom endpoint extractor."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()

        # Use different User-Agent that doesn't trigger bot detection
        self.session.headers.update({
            'User-Agent': 'TravelMemo-ContentFetcher/1.0',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'no-cache'
        })

    def extract_via_custom_endpoint(self, blog_url: str) -> Optional[Dict[str, any]]:
        """
        Extract content using custom WordPress endpoint.

        Args:
            blog_url: URL of the blog post

        Returns:
            Dict containing extracted content or None if extraction fails
        """
        try:
            # Extract slug from URL
            slug = self._extract_url_slug(blog_url)
            if not slug:
                self.logger.debug(f"Could not extract slug from URL: {blog_url}")
                return None

            # Build custom endpoint URL using travelmemo-content namespace
            parsed_url = urlparse(blog_url)
            custom_api_url = f"{parsed_url.scheme}://{parsed_url.netloc}/wp-json/travelmemo-content/v1/extract/{slug}"

            self.logger.info(f"Trying custom endpoint for slug: {slug}")
            self.logger.debug(f"Custom endpoint URL: {custom_api_url}")

            # Add optional authentication key
            params = {
                'auth_key': 'tm-post-retrieval'
            }

            response = self.session.get(custom_api_url, params=params, timeout=30)

            self.logger.debug(f"Custom endpoint response status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()

                if data.get('success') and data.get('data'):
                    content_data = data['data']

                    # Transform to expected format
                    result = {
                        'url': blog_url,
                        'title': content_data.get('title', ''),
                        'paragraphs': content_data.get('paragraphs', []),
                        'images': content_data.get('images', []),  # Now includes extracted images
                        'headings': content_data.get('headings', []),  # Now includes extracted headings
                        'meta_description': content_data.get('excerpt', ''),
                        'source': 'travelmemo_content_api',
                        'word_count': content_data.get('word_count', 0),
                        'categories': content_data.get('categories', []),
                        'tags': content_data.get('tags', [])
                    }

                    self.logger.info(f"Custom endpoint successful: {len(result['paragraphs'])} paragraphs, {result['word_count']} words")
                    return result
                else:
                    self.logger.error(f"Custom endpoint returned invalid data structure: {data}")
                    return None
            else:
                self.logger.error(f"Custom endpoint returned status {response.status_code}: {response.text[:200]}")
                return None

        except requests.exceptions.RequestException as e:
            self.logger.debug(f"Custom endpoint request failed for {blog_url}: {e}")
        except Exception as e:
            self.logger.debug(f"Custom endpoint extraction failed for {blog_url}: {e}")

        return None

    def _extract_url_slug(self, url: str) -> Optional[str]:
        """Extract the post slug from a URL."""
        try:
            parsed = urlparse(url)
            # Get the last part of the path as the slug
            path_parts = parsed.path.strip('/').split('/')
            if path_parts:
                return path_parts[-1]
        except Exception as e:
            self.logger.debug(f"Error extracting slug from URL {url}: {e}")
        return None

    def test_custom_endpoint(self, blog_url: str) -> bool:
        """
        Test if the custom endpoint is working.

        Args:
            blog_url: URL to test

        Returns:
            True if endpoint is working, False otherwise
        """
        result = self.extract_via_custom_endpoint(blog_url)
        return result is not None and len(result.get('paragraphs', [])) > 0