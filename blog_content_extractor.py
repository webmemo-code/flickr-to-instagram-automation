"""
Blog content extraction for enhanced caption generation.
Fetches and processes blog post content to provide context for photo captions.
"""
import requests
import logging
import re
from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import base64
from custom_endpoint_extractor import CustomEndpointExtractor




@dataclass(frozen=True)
class BlogContextMatch:
    """Container for the best matching blog context snippet."""

    url: str
    context: str
    score: int
    matched_terms: Tuple[str, ...]


class BlogContentExtractor:
    """Extracts and processes blog post content for caption enhancement."""
    
    def __init__(self, config):
        """Initialize the blog content extractor."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        self.custom_extractor = CustomEndpointExtractor(config)
        self._content_cache: Dict[str, Optional[Dict[str, any]]] = {}

        # Initialize email notifier for API failure alerts
        self.email_notifier = None
        try:
            from email_notifier import EmailNotifier
            self.email_notifier = EmailNotifier(config)
        except ImportError:
            self.logger.debug("Email notifier not available")

        # Use consistent User-Agent to avoid Cloudflare bot detection
        self.user_agent = 'TravelMemo-ContentFetcher/1.0'

        self._update_headers()
    
    def _update_headers(self):
        """Update session headers with consistent user-agent."""
        user_agent = self.user_agent

        self.session.headers.update({
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9,de;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'DNT': '1'
        })

        # Add referrer if this looks like travelmemo.com
        if hasattr(self, '_last_url') and 'travelmemo.com' in self._last_url:
            self.session.headers['Referer'] = 'https://www.google.com/'

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

    def _extract_via_wordpress_api(self, blog_url: str) -> Optional[Dict[str, any]]:
        """
        Extract content using WordPress REST API with optional authentication.

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

            # Try WordPress REST API endpoint
            parsed_url = urlparse(blog_url)
            api_url = f"{parsed_url.scheme}://{parsed_url.netloc}/wp-json/wp/v2/posts"

            self.logger.info(f"Trying WordPress API for slug: {slug}")

            # Prepare authentication if available
            auth_headers = {}
            use_auth = False
            if self.config.wordpress_username and self.config.wordpress_app_password:
                # Create Basic Authentication header
                credentials = f"{self.config.wordpress_username}:{self.config.wordpress_app_password}"
                encoded_credentials = base64.b64encode(credentials.encode()).decode()
                auth_headers['Authorization'] = f'Basic {encoded_credentials}'
                use_auth = True
                self.logger.info("WordPress credentials available - will try with authentication")

            # First try with authentication if available, then without if it fails
            response = None
            success = False

            for attempt in ['with_auth', 'without_auth']:
                if attempt == 'with_auth' and not use_auth:
                    self.logger.debug("Skipping auth attempt - no credentials available")
                    continue  # Skip if no auth available
                if attempt == 'without_auth' and not use_auth:
                    self.logger.debug("No auth available, trying without authentication")
                    pass  # Continue with no-auth attempt

                # Use consistent user-agent to avoid Cloudflare blocking
                api_headers = {
                    'User-Agent': 'TravelMemo-ContentFetcher/1.0',
                    'Accept': 'application/json, text/plain, */*',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Referer': blog_url,
                    'Sec-Fetch-Dest': 'empty',
                    'Sec-Fetch-Mode': 'cors',
                    'Sec-Fetch-Site': 'same-origin'
                }

                # Add auth headers only on first attempt
                if attempt == 'with_auth':
                    api_headers.update(auth_headers)
                    self.logger.info("Trying WordPress API with authentication")
                else:
                    self.logger.info("Trying WordPress API without authentication")

                self.logger.debug(f"WordPress API request URL: {api_url}?slug={slug}")

                try:
                    response = self.session.get(api_url, params={'slug': slug}, headers=api_headers, timeout=30)

                    self.logger.debug(f"WordPress API response status: {response.status_code}")

                    if response.status_code == 200:
                        self.logger.info(f"WordPress API successful ({attempt})")
                        success = True
                        break
                    elif response.status_code == 403 and attempt == 'with_auth':
                        self.logger.warning(f"WordPress API authentication failed (403), trying without authentication")
                        continue
                    else:
                        self.logger.error(f"WordPress API returned status {response.status_code}: {response.text[:200]}")
                        if attempt == 'without_auth' or not use_auth:
                            return None
                        continue

                except Exception as e:
                    self.logger.warning(f"WordPress API error ({attempt}): {e}")
                    if attempt == 'without_auth' or not use_auth:
                        return None
                    continue

            # Check if we have a successful response
            if not success or not response or response.status_code != 200:
                self.logger.warning("WordPress API completely failed - attempting direct page scraping as fallback")
                # Try direct page scraping when API completely fails
                fallback_data = self._try_direct_page_scraping_structured(blog_url)
                if fallback_data and fallback_data.get('paragraphs'):
                    self.logger.info(f"Direct page scraping successful as API fallback - got {len(fallback_data['paragraphs'])} paragraphs")
                    content_data = {
                        'url': blog_url,
                        'title': fallback_data.get('title', 'Unknown Title'),
                        'paragraphs': fallback_data['paragraphs'],
                        'images': fallback_data.get('images', []),
                        'headings': fallback_data.get('headings', []),
                        'meta_description': '',
                        'source': 'direct_scraping_api_fallback'
                    }
                    self.logger.info(f"Successfully extracted content via direct scraping API fallback: {len(content_data['paragraphs'])} paragraphs")
                    return content_data
                return None

            posts = response.json()
            if not posts or len(posts) == 0:
                self.logger.debug(f"No posts found for slug: {slug}")
                return None

            post = posts[0]  # Take the first matching post

            # Extract content from WordPress API response
            raw_content = post.get('content', {}).get('rendered', '')
            title = post.get('title', {}).get('rendered', 'Unknown Title')
            excerpt = post.get('excerpt', {}).get('rendered', '')

            # Check for Elementor read-more truncation
            is_truncated = 'elementor-widget-read-more' in raw_content and len(raw_content) < 2000
            if is_truncated:
                self.logger.warning(f"Detected Elementor read-more widget - content appears truncated ({len(raw_content)} chars)")
                self.logger.info("Attempting direct page scraping as fallback for truncated content")

                # Try direct page scraping as fallback
                fallback_data = self._try_direct_page_scraping_structured(blog_url)
                if fallback_data and fallback_data.get('paragraphs'):
                    total_fallback_chars = sum(len(p) for p in fallback_data['paragraphs'])
                    if total_fallback_chars > len(raw_content):
                        self.logger.info(f"Direct page scraping successful - got {total_fallback_chars} chars vs {len(raw_content)} from API")
                        # Use the structured data directly instead of processing HTML again
                        # Clean excerpt text
                        excerpt_text = ''
                        if excerpt:
                            excerpt_soup = BeautifulSoup(excerpt, 'html.parser')
                            excerpt_text = excerpt_soup.get_text().strip()

                        content_data = {
                            'url': blog_url,
                            'title': title,
                            'paragraphs': fallback_data['paragraphs'],
                            'images': fallback_data.get('images', []),
                            'headings': fallback_data.get('headings', []),
                            'meta_description': excerpt_text,
                            'source': 'direct_scraping'
                        }
                        self.logger.info(f"Successfully extracted content via direct scraping: {len(content_data['paragraphs'])} paragraphs")
                        return content_data
                else:
                    # Fall back to excerpt if available and longer
                    if excerpt and len(excerpt.strip()) > len(raw_content.strip()):
                        self.logger.info("Using excerpt content as it's longer than truncated main content")
                        raw_content = excerpt
                    else:
                        self.logger.warning("No better content source available - proceeding with truncated API content")

            # Clean HTML content
            if raw_content:
                soup = BeautifulSoup(raw_content, 'html.parser')

                # Extract paragraphs from cleaned content (enhanced for Elementor)
                paragraphs = []

                # Handle Elementor content - look for text in various containers
                elementor_text_selectors = [
                    '.elementor-widget-text-editor .elementor-widget-container',
                    '.elementor-text-editor',
                    '.post-content',
                    'p'
                ]

                found_content = False
                for selector in elementor_text_selectors:
                    elements = soup.select(selector)
                    for element in elements:
                        # Get all text content, including from nested elements
                        text = element.get_text().strip()
                        if len(text) > 30:  # Substantial content
                            # Clean up text
                            text = re.sub(r'\s+', ' ', text)
                            # Split into sentences/paragraphs if it's a long block
                            if len(text) > 500:
                                # Split on sentence endings
                                sentences = re.split(r'[.!?]\s+', text)
                                for sentence in sentences:
                                    if len(sentence.strip()) > 50:
                                        paragraphs.append(sentence.strip() + '.')
                                        found_content = True
                            else:
                                paragraphs.append(text)
                                found_content = True

                # Fallback: extract all paragraphs if Elementor extraction didn't work
                if not found_content:
                    for p in soup.find_all('p'):
                        text = p.get_text().strip()
                        if len(text) > 50:
                            text = re.sub(r'\s+', ' ', text)
                            paragraphs.append(text)

                # Remove duplicates while preserving order
                seen = set()
                unique_paragraphs = []
                for para in paragraphs:
                    if para not in seen:
                        seen.add(para)
                        unique_paragraphs.append(para)
                paragraphs = unique_paragraphs

                # Extract headings
                headings = []
                for level in range(1, 7):
                    for heading in soup.find_all(f'h{level}'):
                        text = heading.get_text().strip()
                        if text:
                            headings.append({
                                'level': level,
                                'text': text
                            })

                # Extract images
                images = self._extract_image_references(soup, blog_url)

                # Clean excerpt
                excerpt_text = ''
                if excerpt:
                    excerpt_soup = BeautifulSoup(excerpt, 'html.parser')
                    excerpt_text = excerpt_soup.get_text().strip()

                content_data = {
                    'url': blog_url,
                    'title': title,
                    'paragraphs': paragraphs,
                    'images': images,
                    'headings': headings,
                    'meta_description': excerpt_text,
                    'source': 'wordpress_api'
                }

                self.logger.info(f"Successfully extracted WordPress content: {len(paragraphs)} paragraphs, "
                               f"{len(images)} image references")
                return content_data

        except requests.exceptions.RequestException as e:
            self.logger.debug(f"WordPress API request failed for {blog_url}: {e}")
        except Exception as e:
            self.logger.debug(f"WordPress API extraction failed for {blog_url}: {e}")

        return None

    def _try_direct_page_scraping(self, blog_url: str) -> Optional[str]:
        """
        Try to scrape content directly from the blog page as fallback for Elementor read-more limitation.

        Args:
            blog_url: URL of the blog post

        Returns:
            Extracted text content or None if scraping fails
        """
        try:
            self.logger.debug(f"Attempting direct page scraping for: {blog_url}")

            # Use consistent user-agent with cookie consent
            scraping_headers = {
                'User-Agent': 'TravelMemo-ContentFetcher/1.0',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0',
                # Add cookies to bypass consent banners
                'Cookie': 'cmplz_marketing=allow; cmplz_statistics=allow; cmplz_functional=allow; wp_has_consent=1'
            }

            response = self.session.get(blog_url, headers=scraping_headers, timeout=30)

            if response.status_code != 200:
                self.logger.debug(f"Direct page scraping failed with status {response.status_code}")
                return None

            soup = BeautifulSoup(response.content, 'html.parser')

            # Try to find main content area with Elementor-specific selectors
            content_selectors = [
                '.elementor-widget-text-editor .elementor-widget-container',
                '.elementor-text-editor',
                '.entry-content',
                '.post-content',
                '.content',
                'article',
                'main'
            ]

            extracted_text = []

            for selector in content_selectors:
                elements = soup.select(selector)
                for element in elements:
                    # Skip read-more widgets and other navigation elements
                    if any(cls in element.get('class', []) for cls in ['read-more', 'navigation', 'menu']):
                        continue

                    text = element.get_text().strip()
                    if len(text) > 50:  # Only substantial content
                        # Clean up text
                        text = re.sub(r'\s+', ' ', text)
                        extracted_text.append(text)

                # If we found content with this selector, no need to try others
                if extracted_text:
                    break

            if extracted_text:
                combined_text = ' '.join(extracted_text)
                # Remove duplicates and clean up
                combined_text = re.sub(r'\s+', ' ', combined_text).strip()

                if len(combined_text) > 200:  # Minimum useful content length
                    self.logger.debug(f"Direct scraping extracted {len(combined_text)} characters")
                    return combined_text

        except Exception as e:
            self.logger.debug(f"Direct page scraping failed for {blog_url}: {e}")

        return None

    def _try_direct_page_scraping_structured(self, blog_url: str) -> Optional[Dict[str, any]]:
        """
        Try to scrape and structure content directly from the blog page.

        Args:
            blog_url: URL of the blog post

        Returns:
            Structured content dict or None if scraping fails
        """
        try:
            self.logger.debug(f"Attempting structured direct page scraping for: {blog_url}")

            # Use consistent user-agent with cookie consent
            scraping_headers = {
                'User-Agent': 'TravelMemo-ContentFetcher/1.0',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0',
                # Add cookies to bypass consent banners
                'Cookie': 'cmplz_marketing=allow; cmplz_statistics=allow; cmplz_functional=allow; wp_has_consent=1'
            }

            response = self.session.get(blog_url, headers=scraping_headers, timeout=30)

            if response.status_code != 200:
                self.logger.debug(f"Direct page scraping failed with status {response.status_code}")
                return None

            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract paragraphs using Elementor-specific selectors
            paragraphs = []
            content_selectors = [
                '.elementor-widget-text-editor .elementor-widget-container p',
                '.elementor-text-editor p',
                '.entry-content p',
                '.post-content p',
                '.content p',
                'article p',
                'main p'
            ]

            for selector in content_selectors:
                elements = soup.select(selector)
                for element in elements:
                    text = element.get_text().strip()
                    if len(text) > 50:  # Only substantial paragraphs
                        # Clean up text
                        text = re.sub(r'\s+', ' ', text)
                        if text not in paragraphs:  # Avoid duplicates
                            paragraphs.append(text)

                # If we found content with this selector, use it
                if paragraphs:
                    break

            # Extract headings
            headings = []
            for level in range(1, 7):
                for heading in soup.find_all(f'h{level}'):
                    text = heading.get_text().strip()
                    if text:
                        headings.append({
                            'level': level,
                            'text': text
                        })

            # Extract images
            images = self._extract_image_references(soup, blog_url)

            # Extract title from page
            title = 'Unknown Title'
            title_selectors = ['h1', 'title', '.entry-title', '.post-title', 'h1.title']
            for selector in title_selectors:
                element = soup.select_one(selector)
                if element:
                    title = element.get_text().strip()
                    break

            if paragraphs:
                self.logger.debug(f"Structured scraping extracted {len(paragraphs)} paragraphs, {len(headings)} headings, {len(images)} images")
                return {
                    'title': title,
                    'paragraphs': paragraphs,
                    'headings': headings,
                    'images': images
                }

        except Exception as e:
            self.logger.debug(f"Structured direct page scraping failed for {blog_url}: {e}")

        return None

    def extract_blog_content(self, blog_url: str) -> Optional[Dict[str, any]]:
        """
        Extract structured content from a blog post URL using WordPress API.

        Args:
            blog_url: URL of the blog post to analyze

        Returns:
            Dict containing extracted content or None if extraction fails
        """
        # Track attempted methods and errors for notification
        attempted_methods = []
        last_error = None
        last_http_status = None

        # Try WordPress REST API if this looks like a WordPress site
        if 'travelmemo.com' in blog_url or 'reisememo.ch' in blog_url:
            # First try custom endpoint (most reliable)
            self.logger.info(f"Attempting custom endpoint extraction for: {blog_url}")
            attempted_methods.append("Custom WordPress API Endpoint")

            custom_content = self.custom_extractor.extract_via_custom_endpoint(blog_url)
            if custom_content:
                return custom_content

            # Fallback to standard WordPress API
            self.logger.info(f"Custom endpoint failed, trying standard WordPress API for: {blog_url}")
            attempted_methods.append("Standard WordPress REST API")

            wordpress_content = self._extract_via_wordpress_api(blog_url)
            if wordpress_content:
                return wordpress_content

            # If both APIs failed, try direct page scraping as final fallback
            self.logger.warning("All API methods failed - attempting direct page scraping as final fallback")
            attempted_methods.append("Direct Page Scraping")

            fallback_data = self._try_direct_page_scraping_structured(blog_url)
            if fallback_data and fallback_data.get('paragraphs'):
                self.logger.info(f"Final fallback successful - got {len(fallback_data['paragraphs'])} paragraphs via direct scraping")
                content_data = {
                    'url': blog_url,
                    'title': fallback_data.get('title', 'Unknown Title'),
                    'paragraphs': fallback_data['paragraphs'],
                    'images': fallback_data.get('images', []),
                    'headings': fallback_data.get('headings', []),
                    'meta_description': '',
                    'source': 'direct_scraping_final_fallback'
                }
                self.logger.info(f"Successfully extracted content via final fallback: {len(content_data['paragraphs'])} paragraphs")

                # Even though we got content via fallback, this indicates API access issues
                # Send a notification if all API methods failed
                self._send_api_failure_notification(
                    blog_url,
                    attempted_methods,
                    last_error or "All WordPress API methods failed",
                    last_http_status,
                    fallback_used=True
                )

                return content_data

            # Complete failure - send notification
            self.logger.warning("All extraction methods failed. Caption generation will proceed without blog context.")
            self._send_api_failure_notification(
                blog_url,
                attempted_methods,
                last_error or "All extraction methods (API and scraping) failed",
                last_http_status,
                fallback_used=False
            )

        return None

    def _send_api_failure_notification(self,
                                     blog_url: str,
                                     attempted_methods: List[str],
                                     error_message: str,
                                     http_status: Optional[int],
                                     fallback_used: bool) -> None:
        """Send email notification about API access failure."""
        if not self.email_notifier:
            self.logger.debug("Email notifier not available - skipping API failure notification")
            return

        # Determine account name from URL
        account_name = "Primary"
        if 'reisememo.ch' in blog_url:
            account_name = "Secondary (Reisememo)"
        elif 'travelmemo.com' in blog_url:
            account_name = "Primary (TravelMemo)"

        # Prepare error details
        error_details = {
            'http_status': http_status or 'Unknown',
            'error_message': error_message,
            'attempted_methods': attempted_methods,
            'fallback_used': fallback_used
        }

        try:
            success = self.email_notifier.send_api_failure_alert(blog_url, error_details, account_name)
            if success:
                self.logger.info("API failure notification sent successfully")
            else:
                self.logger.warning("API failure notification could not be sent")
        except Exception as e:
            self.logger.error(f"Failed to send API failure notification: {e}")

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract the blog post title."""
        # Try multiple selectors for title
        selectors = ['h1', 'title', '.entry-title', '.post-title', 'h1.title']
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text().strip()
        
        return "Unknown Title"
    
    def _extract_paragraphs(self, soup: BeautifulSoup) -> List[str]:
        """Extract text paragraphs from the blog post."""
        paragraphs = []
        
        # Look for main content areas first
        content_areas = soup.select('.entry-content, .post-content, .content, article, main')
        
        if content_areas:
            # Use the first found content area
            content_soup = content_areas[0]
        else:
            # Fallback to entire document
            content_soup = soup
        
        # Extract paragraphs from content area
        for p in content_soup.find_all('p'):
            text = p.get_text().strip()
            if len(text) > 50:  # Only include substantial paragraphs
                # Clean up text
                text = re.sub(r'\s+', ' ', text)
                paragraphs.append(text)
        
        return paragraphs
    
    def _extract_headings(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract headings from the blog post."""
        headings = []
        
        for level in range(1, 7):  # h1 to h6
            for heading in soup.find_all(f'h{level}'):
                text = heading.get_text().strip()
                if text:
                    headings.append({
                        'level': level,
                        'text': text
                    })
        
        return headings
    
    def _extract_image_references(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        """Extract image references and their context."""
        images = []
        
        for img in soup.find_all('img'):
            img_data = {}
            
            # Get image source
            src = img.get('src')
            if src:
                img_data['src'] = urljoin(base_url, src)
            
            # Get alt text
            alt = img.get('alt', '').strip()
            if alt:
                img_data['alt'] = alt
            
            # Get caption from surrounding elements
            caption = self._find_image_caption(img)
            if caption:
                img_data['caption'] = caption
            
            # Get surrounding text context
            context = self._get_surrounding_text(img)
            if context:
                img_data['context'] = context
            
            if img_data:  # Only add if we found useful information
                images.append(img_data)
        
        return images
    
    def _find_image_caption(self, img_element) -> Optional[str]:
        """Find caption text associated with an image."""
        # Look for common caption patterns
        parent = img_element.parent
        
        # Check for figcaption
        figcaption = None
        if parent and parent.name == 'figure':
            figcaption = parent.find('figcaption')
        
        if figcaption:
            return figcaption.get_text().strip()
        
        # Check for caption class in siblings or parent
        caption_selectors = ['.caption', '.wp-caption-text', '.img-caption']
        for selector in caption_selectors:
            caption = parent.select_one(selector) if parent else None
            if caption:
                return caption.get_text().strip()
        
        return None
    
    def _get_surrounding_text(self, img_element, max_chars=500) -> Optional[str]:
        """Get text content surrounding an image."""
        try:
            # Get the paragraph or div containing the image
            container = img_element.find_parent(['p', 'div', 'section', 'article'])
            if not container:
                return None
            
            # Extract text from the container
            text = container.get_text().strip()
            
            # Clean up and limit length
            text = re.sub(r'\s+', ' ', text)
            if len(text) > max_chars:
                text = text[:max_chars] + "..."
            
            return text if len(text) > 20 else None
            
        except Exception:
            return None
    
    def _extract_meta_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract meta description from the page."""
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            return meta_desc.get('content', '').strip()
        
        # Try Open Graph description
        og_desc = soup.find('meta', attrs={'property': 'og:description'})
        if og_desc:
            return og_desc.get('content', '').strip()
        
        return None
    
    def get_blog_content(self, blog_url: str) -> Optional[Dict[str, any]]:
        """Retrieve blog content with caching to avoid duplicate fetches."""
        if not blog_url:
            return None

        if blog_url in self._content_cache:
            return self._content_cache[blog_url]

        content = self.extract_blog_content(blog_url)
        self._content_cache[blog_url] = content
        return content

    def find_relevant_content(self, blog_content: Dict[str, any], photo_context: Dict[str, any]) -> Optional[BlogContextMatch]:
        """Find the best matching blog content snippet for a given photo."""
        if not blog_content or not photo_context:
            return None

        try:
            search_terms = self._extract_photo_keywords(photo_context)

            if not search_terms:
                self.logger.debug("No search terms extracted from photo context")
                return None

            self.logger.debug(f"Searching blog content for terms: {search_terms}")

            scored_content = []

            for paragraph in blog_content.get('paragraphs', []):
                score, matched_terms = self._score_text_relevance(paragraph, search_terms)
                if score > 0:
                    scored_content.append((score, paragraph, matched_terms))

            for img in blog_content.get('images', []):
                for field in ['alt', 'caption', 'context']:
                    text_value = img.get(field, '')
                    if text_value:
                        score, matched_terms = self._score_text_relevance(text_value, search_terms)
                        if score > 0:
                            scored_content.append((score, text_value, matched_terms))

            if not scored_content:
                self.logger.debug("No relevant content found in blog post")
                return None

            scored_content.sort(reverse=True, key=lambda x: x[0])
            top_entries = scored_content[:3]
            relevant_texts = [content for score, content, _ in top_entries]

            combined_content = " ".join(relevant_texts)
            combined_content = re.sub(r'\s+', ' ', combined_content).strip()

            max_length = 1000
            if len(combined_content) > max_length:
                combined_content = combined_content[:max_length] + "..."

            total_score = sum(score for score, _, __ in top_entries)
            matched_terms = sorted({term for _, __, terms in top_entries for term in terms})

            self.logger.info(f"Found relevant blog content ({len(combined_content)} chars) with score {total_score}")
            return BlogContextMatch(
                url=blog_content.get('url', ''),
                context=combined_content,
                score=total_score,
                matched_terms=tuple(matched_terms)
            )

        except Exception as e:
            self.logger.error(f"Error finding relevant content: {e}")
            return None






    def _extract_photo_keywords(self, photo_context: Dict[str, any]) -> List[Dict[str, any]]:
        """Extract searchable keywords and phrases from photo metadata."""
        keywords: List[Dict[str, any]] = []
        seen = set()

        def add_term(term: str, *, weight: int = 1, is_phrase: bool = False, source: str = 'generic') -> None:
            if not term:
                return
            normalized = re.sub(r"\s+", " ", term.strip().lower())
            if not normalized:
                return
            key = (normalized, is_phrase, source)
            if key in seen:
                return
            keywords.append({
                'term': normalized,
                'weight': weight,
                'is_phrase': is_phrase or ' ' in normalized,
                'source': source
            })
            seen.add(key)

        stop_words = {'photo', 'image', 'picture', 'with', 'from', 'this', 'that', 'have', 'been', 'were', 'they'}

        title = photo_context.get('title') or ''
        if title:
            add_term(title, weight=2, is_phrase=True, source='title')
            title_words = re.findall(r"[A-Za-z'-]+", title)
            normalized_words = [w.lower() for w in title_words if len(w) > 1]
            for word in normalized_words:
                if word in stop_words:
                    continue
                add_term(word, weight=1, source='title_word')
            for size in range(2, min(4, len(normalized_words) + 1)):
                for idx in range(len(normalized_words) - size + 1):
                    phrase = ' '.join(normalized_words[idx:idx + size])
                    if phrase in stop_words:
                        continue
                    add_term(phrase, weight=3, is_phrase=True, source='title_phrase')

        description = photo_context.get('description') or ''
        if description:
            desc_words = re.findall(r"[A-Za-z'-]+", description)
            for word in desc_words:
                word_lower = word.lower()
                if len(word_lower) <= 2 or word_lower in stop_words:
                    continue
                add_term(word_lower, weight=1, source='description')

        location_data = photo_context.get('location_data', {}) or {}
        possible_locations = []
        if isinstance(location_data, dict):
            for key in ['city', 'region', 'country', 'locality']:
                value = location_data.get(key) or ''
                if isinstance(value, dict):
                    value = value.get('_content', '')
                if value:
                    possible_locations.append(value)
            photo_location = location_data.get('photo') or {}
            if isinstance(photo_location, dict):
                location = photo_location.get('location') or {}
                if isinstance(location, dict):
                    for key in ['locality', 'region', 'country']:
                        value = location.get(key) or {}
                        if isinstance(value, dict):
                            value = value.get('_content', '')
                        if value:
                            possible_locations.append(value)
        for value in possible_locations:
            add_term(value, weight=2, is_phrase=True, source='location')

        tag_sources = []
        for key in ['tags', 'meta_keywords', 'keywords']:
            if key in photo_context and photo_context[key]:
                tag_sources.append(photo_context[key])
        for source_entries in tag_sources:
            if isinstance(source_entries, str):
                entries = re.split(r'[;,]', source_entries)
            else:
                entries = source_entries if isinstance(source_entries, (list, tuple, set)) else []
            for entry in entries:
                if not isinstance(entry, str):
                    continue
                cleaned = entry.strip()
                if not cleaned:
                    continue
                cleaned_normalized = cleaned.replace('-', ' ')
                add_term(cleaned_normalized, weight=5, is_phrase=True, source='meta')
                tag_words = re.findall(r"[A-Za-z'-]+", cleaned_normalized)
                for word in tag_words:
                    word_lower = word.lower()
                    if len(word_lower) <= 2 or word_lower in stop_words:
                        continue
                    add_term(word_lower, weight=3, source='meta_word')

        exif_hints = photo_context.get('exif_hints') or {}
        for url in exif_hints.get('source_urls', []):
            add_term(url, weight=10, is_phrase=True, source='exif_source')
        for phrase in exif_hints.get('phrases', []):
            add_term(phrase, weight=6, is_phrase=True, source='exif_phrase')
            phrase_words = re.findall(r"[A-Za-z'-]+", phrase)
            for word in phrase_words:
                word_lower = word.lower()
                if len(word_lower) <= 2 or word_lower in stop_words:
                    continue
                add_term(word_lower, weight=2, source='exif_phrase_word')
        for keyword in exif_hints.get('keywords', []):
            add_term(keyword, weight=4, source='exif_keyword')

        return keywords

    def _score_text_relevance(self, text: str, search_terms: List[Dict[str, any]]) -> Tuple[int, List[str]]:
        """Score text relevance, heavily rewarding exact matches for meta tags."""
        if not text or not search_terms:
            return 0, []

        text_lower = text.lower()
        score = 0
        matched_terms: List[str] = []

        for term_info in search_terms:
            term = term_info.get("term")
            if not term:
                continue
            weight = term_info.get("weight", 1)
            is_phrase = term_info.get("is_phrase", False)
            source = term_info.get("source", "generic")

            if " " in term:
                parts = [re.escape(p) for p in term.split()]
                pattern = r"\b" + r"\s+".join(parts) + r"\b"
            else:
                pattern = r"\b" + re.escape(term) + r"\b"

            exact_matches = len(re.findall(pattern, text_lower))

            if exact_matches > 0:
                if source == "meta":
                    base_score = 8
                elif is_phrase:
                    base_score = 6
                else:
                    base_score = 4
                score += exact_matches * base_score * weight
                if term not in matched_terms:
                    matched_terms.append(term)
            elif term in text_lower:
                score += weight

        if len(text) > 200:
            score += 1

        return score, matched_terms


