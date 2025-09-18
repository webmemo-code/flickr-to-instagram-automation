"""
Blog content extraction for enhanced caption generation.
Fetches and processes blog post content to provide context for photo captions.
"""
import requests
import logging
import re
import time
import random
import xml.etree.ElementTree as ET
from typing import Optional, List, Dict
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse


class BlogContentExtractor:
    """Extracts and processes blog post content for caption enhancement."""
    
    def __init__(self, config):
        """Initialize the blog content extractor."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()

        # Rotate through multiple realistic User-Agent strings
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15'
        ]

        self._update_headers()
    
    def _update_headers(self):
        """Update session headers with browser-like values."""
        user_agent = random.choice(self.user_agents)

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
        Extract content using WordPress REST API.

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

            # Search for post by slug
            response = self.session.get(api_url, params={'slug': slug}, timeout=30)
            response.raise_for_status()

            posts = response.json()
            if not posts or len(posts) == 0:
                self.logger.debug(f"No posts found for slug: {slug}")
                return None

            post = posts[0]  # Take the first matching post

            # Extract content from WordPress API response
            raw_content = post.get('content', {}).get('rendered', '')
            title = post.get('title', {}).get('rendered', 'Unknown Title')
            excerpt = post.get('excerpt', {}).get('rendered', '')

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

    def _extract_via_rss_feed(self, blog_url: str) -> Optional[Dict[str, any]]:
        """
        Extract content using RSS feed.

        Args:
            blog_url: URL of the blog post

        Returns:
            Dict containing extracted content or None if extraction fails
        """
        try:
            # Try common RSS feed URLs
            parsed_url = urlparse(blog_url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

            rss_urls = [
                f"{base_url}/feed/",
                f"{base_url}/feed",
                f"{base_url}/rss/",
                f"{base_url}/rss",
                f"{base_url}/index.xml"
            ]

            for rss_url in rss_urls:
                try:
                    self.logger.debug(f"Trying RSS feed: {rss_url}")
                    response = self.session.get(rss_url, timeout=30)
                    response.raise_for_status()

                    # Parse RSS XML
                    root = ET.fromstring(response.content)

                    # Find the channel
                    channel = root.find('channel')
                    if not channel:
                        continue

                    # Find items
                    items = channel.findall('item')
                    if not items:
                        continue

                    # Look for our specific post by URL
                    for item in items:
                        link_elem = item.find('link')
                        if link_elem is not None and link_elem.text:
                            if blog_url.rstrip('/') in link_elem.text.rstrip('/'):
                                # Found our post!
                                title_elem = item.find('title')
                                description_elem = item.find('description')

                                # Look for full content in content:encoded or other namespaces
                                content_elem = None
                                for child in item:
                                    if 'content' in child.tag.lower():
                                        content_elem = child
                                        break

                                # Extract content
                                title = title_elem.text if title_elem is not None else 'Unknown Title'
                                description = description_elem.text if description_elem is not None else ''
                                full_content = content_elem.text if content_elem is not None else ''

                                # Use full content if available, otherwise description
                                content_text = full_content if full_content else description

                                if content_text:
                                    # Parse HTML content
                                    soup = BeautifulSoup(content_text, 'html.parser')

                                    # Extract paragraphs
                                    paragraphs = []
                                    for p in soup.find_all('p'):
                                        text = p.get_text().strip()
                                        if len(text) > 50:
                                            text = re.sub(r'\s+', ' ', text)
                                            paragraphs.append(text)

                                    # If no paragraphs found, use the whole text
                                    if not paragraphs and content_text:
                                        clean_text = soup.get_text().strip()
                                        if len(clean_text) > 50:
                                            paragraphs = [clean_text]

                                    # Extract other elements
                                    headings = self._extract_headings(soup)
                                    images = self._extract_image_references(soup, blog_url)

                                    content_data = {
                                        'url': blog_url,
                                        'title': title,
                                        'paragraphs': paragraphs,
                                        'images': images,
                                        'headings': headings,
                                        'meta_description': description,
                                        'source': 'rss_feed'
                                    }

                                    self.logger.info(f"Successfully extracted RSS content: {len(paragraphs)} paragraphs, "
                                                   f"{len(images)} image references")
                                    return content_data

                    # Post not found in this feed, try next RSS URL
                    continue

                except ET.ParseError as e:
                    self.logger.debug(f"Failed to parse RSS XML from {rss_url}: {e}")
                    continue
                except requests.exceptions.RequestException as e:
                    self.logger.debug(f"Failed to fetch RSS from {rss_url}: {e}")
                    continue

        except Exception as e:
            self.logger.debug(f"RSS extraction failed for {blog_url}: {e}")

        return None

    def extract_blog_content(self, blog_url: str) -> Optional[Dict[str, any]]:
        """
        Extract structured content from a blog post URL with WordPress API, RSS, and HTML fallbacks.

        Args:
            blog_url: URL of the blog post to analyze

        Returns:
            Dict containing extracted content or None if extraction fails
        """
        # First, try WordPress REST API if this looks like a WordPress site
        if 'travelmemo.com' in blog_url or 'reisememo.ch' in blog_url:
            self.logger.info(f"Attempting WordPress API extraction for: {blog_url}")
            wordpress_content = self._extract_via_wordpress_api(blog_url)
            if wordpress_content:
                return wordpress_content

            self.logger.info("WordPress API extraction failed, trying RSS feed")

            # Try RSS feed as second option
            rss_content = self._extract_via_rss_feed(blog_url)
            if rss_content:
                return rss_content

            self.logger.info("RSS extraction failed, falling back to HTML scraping")

        # Fallback to HTML scraping with bot detection bypass
        return self._extract_via_html_scraping(blog_url)

    def _extract_via_html_scraping(self, blog_url: str) -> Optional[Dict[str, any]]:
        """
        Extract content via HTML scraping with bot detection bypass.

        Args:
            blog_url: URL of the blog post to analyze

        Returns:
            Dict containing extracted content or None if extraction fails
        """
        max_retries = 3

        for attempt in range(max_retries):
            try:
                self.logger.info(f"Extracting content from blog URL: {blog_url} (attempt {attempt + 1}/{max_retries})")

                # Update headers with random user agent for each attempt
                self._update_headers()

                # Add human-like delay between requests
                if attempt > 0:
                    delay = random.uniform(2, 5)  # 2-5 second delay
                    self.logger.debug(f"Waiting {delay:.1f} seconds before retry...")
                    time.sleep(delay)

                # Store URL for referrer header
                self._last_url = blog_url

                # Fetch the blog post content with extended timeout
                response = self.session.get(blog_url, timeout=45)
                response.raise_for_status()

                # Parse HTML content
                soup = BeautifulSoup(response.content, 'html.parser')

                # Extract structured content
                content_data = {
                    'url': blog_url,
                    'title': self._extract_title(soup),
                    'paragraphs': self._extract_paragraphs(soup),
                    'images': self._extract_image_references(soup, blog_url),
                    'headings': self._extract_headings(soup),
                    'meta_description': self._extract_meta_description(soup),
                    'source': 'html_scraping'
                }

                self.logger.info(f"Successfully extracted HTML content: {len(content_data['paragraphs'])} paragraphs, "
                               f"{len(content_data['images'])} image references")

                return content_data
            
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 403:
                    if attempt < max_retries - 1:
                        self.logger.warning(f"Blog content blocked (403 Forbidden) from {blog_url} on attempt {attempt + 1}. "
                                          f"Retrying with different headers...")
                        continue
                    else:
                        self.logger.warning(f"Blog content blocked (403 Forbidden) from {blog_url} after {max_retries} attempts. "
                                          f"This may be due to bot detection, cookie consent, or Cloudflare protection. "
                                          f"Caption generation will proceed without blog context.")
                elif e.response.status_code == 404:
                    self.logger.warning(f"Blog post not found (404) at {blog_url}")
                    break  # Don't retry 404s
                elif e.response.status_code in [429, 503]:  # Rate limiting or service unavailable
                    if attempt < max_retries - 1:
                        delay = (2 ** attempt) + random.uniform(1, 3)  # Exponential backoff
                        self.logger.warning(f"Rate limited or service unavailable ({e.response.status_code}) from {blog_url}. "
                                          f"Waiting {delay:.1f} seconds before retry...")
                        time.sleep(delay)
                        continue
                    else:
                        self.logger.error(f"HTTP error fetching blog content from {blog_url} after {max_retries} attempts: {e}")
                else:
                    self.logger.error(f"HTTP error fetching blog content from {blog_url}: {e}")
                    break  # Don't retry other HTTP errors
                return None
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    self.logger.warning(f"Network error fetching blog content from {blog_url} on attempt {attempt + 1}: {e}. Retrying...")
                    continue
                else:
                    self.logger.error(f"Failed to fetch blog content from {blog_url} after {max_retries} attempts: {e}")
                return None
            except Exception as e:
                self.logger.error(f"Error processing blog content: {e}")
                return None

        # If we get here, all retries failed
        return None
    
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
    
    def find_relevant_content(self, blog_content: Dict[str, any], photo_context: Dict[str, any]) -> Optional[str]:
        """
        Find blog content sections most relevant to the photo being processed.
        
        Args:
            blog_content: Extracted blog content structure
            photo_context: Photo metadata (title, description, location, etc.)
            
        Returns:
            Most relevant text content for caption generation
        """
        if not blog_content or not photo_context:
            return None
        
        try:
            # Extract searchable terms from photo context
            search_terms = self._extract_photo_keywords(photo_context)
            
            if not search_terms:
                self.logger.debug("No search terms extracted from photo context")
                return None
            
            self.logger.debug(f"Searching blog content for terms: {search_terms}")
            
            # Score paragraphs based on keyword matches
            scored_content = []
            
            for paragraph in blog_content.get('paragraphs', []):
                score = self._score_text_relevance(paragraph, search_terms)
                if score > 0:
                    scored_content.append((score, paragraph))
            
            # Also check image captions and context
            for img in blog_content.get('images', []):
                for field in ['alt', 'caption', 'context']:
                    text = img.get(field, '')
                    if text:
                        score = self._score_text_relevance(text, search_terms)
                        if score > 0:
                            scored_content.append((score, text))
            
            if not scored_content:
                self.logger.debug("No relevant content found in blog post")
                return None
            
            # Sort by relevance score and combine top matches
            scored_content.sort(reverse=True, key=lambda x: x[0])
            
            # Take top 3 most relevant pieces of content
            relevant_texts = [content for score, content in scored_content[:3]]
            
            # Combine and clean up
            combined_content = " ".join(relevant_texts)
            combined_content = re.sub(r'\s+', ' ', combined_content).strip()
            
            # Limit length for prompt efficiency
            max_length = 1000
            if len(combined_content) > max_length:
                combined_content = combined_content[:max_length] + "..."
            
            self.logger.info(f"Found relevant blog content ({len(combined_content)} chars)")
            return combined_content
            
        except Exception as e:
            self.logger.error(f"Error finding relevant content: {e}")
            return None
    
    def _extract_photo_keywords(self, photo_context: Dict[str, any]) -> List[str]:
        """Extract searchable keywords from photo metadata."""
        keywords = []
        
        # Extract from title
        title = photo_context.get('title', '')
        if title:
            # Clean and split title
            title_words = re.findall(r'\b[a-zA-Z]+\b', title.lower())
            keywords.extend([word for word in title_words if len(word) > 3])
        
        # Extract from description
        description = photo_context.get('description', '')
        if description:
            desc_words = re.findall(r'\b[a-zA-Z]+\b', description.lower())
            keywords.extend([word for word in desc_words if len(word) > 3])
        
        # Extract from location
        location_data = photo_context.get('location_data', {})
        for field in ['city', 'region', 'country']:
            value = location_data.get(field, '')
            if value and len(value) > 2:
                keywords.append(value.lower())
        
        # Remove duplicates and very common words
        stop_words = {'photo', 'image', 'picture', 'with', 'from', 'this', 'that', 'have', 'been', 'were', 'they'}
        keywords = list(set(keywords))
        keywords = [k for k in keywords if k not in stop_words]
        
        return keywords
    
    def _score_text_relevance(self, text: str, search_terms: List[str]) -> int:
        """Score text relevance based on keyword matches."""
        if not text or not search_terms:
            return 0
        
        text_lower = text.lower()
        score = 0
        
        for term in search_terms:
            # Exact matches get higher score
            exact_matches = text_lower.count(term)
            score += exact_matches * 3
            
            # Partial matches get lower score
            if term in text_lower and exact_matches == 0:
                score += 1
        
        # Bonus for longer, more descriptive text
        if len(text) > 200:
            score += 1
        
        return score