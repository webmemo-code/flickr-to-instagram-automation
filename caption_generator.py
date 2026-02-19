"""
Anthropic Claude Vision integration for generating Instagram captions.
"""
import time
import logging
import requests
import anthropic
from typing import Optional, Dict, List, Tuple
from config import Config
from blog_content_extractor import BlogContentExtractor, BlogContextMatch
from account_config import is_secondary_account, get_account_config


class CaptionGenerator:
    """Generate Instagram captions using Anthropic Claude Vision."""

    def __init__(self, config: Config):
        self.config = config
        self.client = anthropic.Anthropic(api_key=config.anthropic_api_key)
        self.logger = logging.getLogger(__name__)
        self.blog_extractor = BlogContentExtractor(config)
        self._blog_content_cache: Dict[str, Optional[Dict[str, any]]] = {}  # Cache blog content per blog URL
    
    def generate_caption(self, photo_data: dict) -> Optional[str]:
        """Generate an Instagram caption for the given image with enhanced context."""
        try:
            # Build enhanced context from available data
            context_parts = []

            # Add title and description
            if photo_data.get('title'):
                context_parts.append(f"Photo title: {photo_data['title']}")
            if photo_data.get('description'):
                context_parts.append(f"Photo description: {photo_data['description']}")

            # Add source/blog URL context
            if photo_data.get('source_url'):
                context_parts.append(f"This photo appears in a blog post at: {photo_data['source_url']}")

            # Add location context
            if photo_data.get('location_data'):
                location = photo_data['location_data'].get('photo', {}).get('location', {})
                location_parts = []
                for field in ['locality', 'region', 'country']:
                    if field in location and '_content' in location[field]:
                        location_parts.append(location[field]['_content'])
                if location_parts:
                    context_parts.append(f"Location: {', '.join(location_parts)}")

            # Add EXIF context (camera info)
            if photo_data.get('exif_data'):
                exif = photo_data['exif_data'].get('photo', {}).get('exif', [])
                camera_info = []
                for tag in exif:
                    if tag.get('tag') in ['Make', 'Model']:
                        camera_info.append(tag.get('raw', {}).get('_content', ''))
                if camera_info:
                    context_parts.append(f"Camera: {' '.join(camera_info)}")

            # Add EXIF hints (phrases, keywords, source URLs)
            exif_hints = photo_data.get('exif_hints', {})
            if exif_hints:
                if exif_hints.get('phrases'):
                    context_parts.append(f"EXIF phrases: {', '.join(exif_hints['phrases'][:10])}")
                if exif_hints.get('keywords'):
                    context_parts.append(f"EXIF keywords: {', '.join(exif_hints['keywords'][:10])}")

            # Add blog post content context (ENHANCED FEATURE)
            blog_match = self._get_blog_content_context(photo_data)
            blog_content = None
            if blog_match and blog_match.url:
                # Try to load full blog content
                blog_content = self._load_blog_content(blog_match.url)

            if blog_match:
                # Build structured blog context with headings and paragraphs
                blog_context_parts = []

                # Start with match context for backward compatibility
                blog_context_parts.append(f"Blog context: {blog_match.context}")

                # Add full blog content if available
                if blog_content:
                    blog_context_parts.append(f"\n=== Full Blog Post: {blog_content.get('title', 'Untitled')} ===")
                    blog_context_parts.append(f"URL: {blog_content.get('url', '')}")

                    # Add headings for structure
                    if blog_content.get('headings'):
                        heading_texts = [h['text'] for h in blog_content['headings'][:5]]
                        blog_context_parts.append(f"Sections: {' | '.join(heading_texts)}")

                    # Add paragraphs (limited to fit in context window)
                    if blog_content.get('paragraphs'):
                        # Limit total blog content to ~4000 chars to leave room for other context
                        paragraphs = blog_content['paragraphs'][:15]  # First 15 paragraphs
                        blog_text = '\n\n'.join(paragraphs)
                        if len(blog_text) > 4000:
                            blog_text = blog_text[:4000] + "..."
                        blog_context_parts.append(f"Content:\n{blog_text}")

                    self.logger.info(
                        f"Added full blog content context for photo {photo_data.get('id')} from {blog_content.get('url')} "
                        f"({len(blog_content.get('paragraphs', []))} paragraphs, {len(blog_content.get('headings', []))} headings)"
                    )
                else:
                    self.logger.info(
                        f"Added blog context snippet for photo {photo_data.get('id')} from {blog_match.url}"
                    )

                blog_context_full = '\n'.join(blog_context_parts)
                context_parts.append(blog_context_full)
            
            # Build the enhanced prompt
            context_text = "\n".join(context_parts) if context_parts else ""

            account_config = get_account_config(self.config.account)
            if context_text:
                # Enhanced prompt with context - use account language configuration
                if account_config and account_config.language == 'de':
                    # German prompts for German-language accounts
                    prompt_base = ("Du bist eine Schweizer Instagram Influencerin, die Reisefotos veröffentlicht. Erstelle eine Instagram Caption "
                                  "in fünf kurzen Sätzen auf Deutsch. Verwende für jeden Satz einen neuen Absatz. "
                                  "Schreibe sachlich, authentisch, persönlich und duze deine Follower. "
                                  "Verwende kein scharfes 'ß', sondern 'ss' wie in der Schweiz. "
                                  "Nutze Emojis nur sparsam und passend.\n\n"
                                  "WICHTIG: Nutze die bereitgestellten Blog-Inhalte, um KONKRETE Details zu erwähnen:\n"
                                  "- Zitiere spezifische Orte, Namen, Ereignisse oder Fakten aus dem Blog-Post\n"
                                  "- Erzähle eine kurze Geschichte oder Anekdote, die im Blog beschrieben wird\n"
                                  "- Vermeide generische Reisebeschreibungen - sei spezifisch!\n"
                                  "- Wenn das Foto eine bestimmte Sehenswürdigkeit, Restaurant, oder Aktivität zeigt, verwende den exakten Namen aus dem Blog\n"
                                  "- Beziehe dich auf konkrete Erlebnisse oder Eindrücke, die im Blog-Post erwähnt werden")

                else:
                    # English prompts for English-language accounts
                    prompt_base = ("You are an Instagram influencer who publishes travel photos. Create an Instagram caption "
                                  "in five short sentences. Add a new paragraph for each sentence. "
                                  "Make it factual, authentic and personal. "
                                  "Do not use the terms 'I can\'t wait to share more...' or 'Stay tuned for more...'. "
                                  "Use emojis sparingly and appropriately.\n\n"
                                  "CRITICAL: Use the provided blog post context to include SPECIFIC details:\n"
                                  "- Reference specific places, names, events, or facts from the blog post\n"
                                  "- Tell a brief story or anecdote that's described in the blog content\n"
                                  "- Avoid generic travel descriptions—be specific and concrete!\n"
                                  "- If the photo shows a particular landmark, restaurant, or activity, use the exact name from the blog\n"
                                  "- Reference concrete experiences or impressions mentioned in the blog post\n"
                                  "- Mine the blog content for unique details that make this photo's story stand out")

                prompt = prompt_base + f"\n\nContext about this photo:\n{context_text}"
                self.logger.debug(f"Using enhanced prompt with context for photo {photo_data.get('id')} (account: {self.config.account})")
            else:
                # Fallback to original prompt style when no context available - use account language configuration
                if account_config and account_config.language == 'de':
                    # German fallback prompt for German-language accounts
                    prompt = ("Du bist eine Schweizer Instagram Influencerin, die Reisefotos veröffentlicht. Beschreibe dieses Bild in zwei sehr kurzen Absätzen "
                             "mit jeweils zwei Sätzen auf Deutsch. Sie dienen als Instagram Captions. Nummeriere weder die Absätze noch die Sätze. "
                             "Verwende keine Anführungszeichen. Halte es persönlich und authentisch. "
                             "Verwende kein scharfes 'ß', sondern 'ss' wie in der Schweiz. "
                             "Nutze Emojis nur sparsam und passend.")
                else:
                    # English fallback prompt for English-language accounts
                    prompt = ("You are an Instagram influencer. Describe this image in two very short paragraphs "
                             "with two sentences each. They serve as Instagram captions. Do not number the paragraphs nor the sentences. "
                             "Do not use quotation marks. Keep it personal and authentic. "
                             "Use emojis sparingly and appropriately.")
                self.logger.debug(f"Using basic prompt (no context available) for photo {photo_data.get('id')} (account: {self.config.account})")
            
            response = self.client.messages.create(
                model=self.config.anthropic_model,
                max_tokens=600,
                temperature=0.4,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "url",
                                    "url": photo_data['url']
                                }
                            },
                            {"type": "text", "text": prompt}
                        ]
                    }
                ]
            )

            generated_text = response.content[0].text
            self.logger.info(f"Generated enhanced caption for photo {photo_data['id']}")
            
            return generated_text
            
        except Exception as e:
            self.logger.error(f"Failed to generate caption for photo {photo_data.get('id', 'unknown')}: {e}")
            return None
    
    def build_full_caption(self, photo_data: dict, generated_caption: str) -> str:
        """Build the complete Instagram caption with title, generated content, and hashtags."""
        caption_parts = []

        # Add title and description
        if photo_data.get('title'):
            title_desc = f"{photo_data['title']}"
            if photo_data.get('description'):
                title_desc += f": {photo_data['description']}"
            caption_parts.append(title_desc)
        
        # Add generated caption
        if generated_caption:
            caption_parts.append(generated_caption)
        
        # Add account-specific footer branding
        account_config = get_account_config(self.config.account)
        if account_config and account_config.brand_signature:
            caption_parts.append(account_config.brand_signature)
        elif account_config and account_config.language == 'de':
            caption_parts.append(f"{account_config.display_name} des Schweizer Reiseblogs über Erlebnisreisen.")
        else:
            caption_parts.append("Travelmemo from a one-of-a-kind travel experience.")

        # Add blog post URL if available
        selected_blog = photo_data.get('selected_blog', {})
        blog_url = selected_blog.get('url') or self.config.get_default_blog_post_url()

        # If no URL is found through blog context or config, try to use a fallback from account config
        if not blog_url:
            if account_config and account_config.blog_domains:
                # Use the first preferred domain as a fallback
                primary_domain = account_config.blog_domains[0]
                if primary_domain:
                    blog_url = f"https://{primary_domain}"
                    self.logger.debug(f"Using fallback URL from account domain preference: {blog_url}")

        if blog_url:
            # Add travel tip text before URL based on account language
            if account_config and account_config.language == 'de':
                caption_parts.append("Lies den Reisetipp unter")
            else:
                caption_parts.append("Read the travel tip at")
            caption_parts.append(blog_url)
        
        # Add hashtags
        if photo_data.get('hashtags'):
            caption_parts.append(photo_data['hashtags'])
        
        return "\n\n".join(caption_parts)
    
    def generate_with_retry(self, photo_data: dict, max_retries: int = 3) -> Optional[str]:
        """Generate caption with retry logic for rate limiting."""
        for attempt in range(max_retries):
            try:
                caption = self.generate_caption(photo_data)
                if caption:
                    return caption
                    
            except Exception as e:
                if "rate_limit" in str(e).lower() and attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    self.logger.warning(f"Rate limit hit, waiting {wait_time} seconds before retry {attempt + 1}")
                    time.sleep(wait_time)
                    continue
                else:
                    self.logger.error(f"Failed to generate caption after {attempt + 1} attempts: {e}")
                    break
        
        return None
    
    def _ensure_longest_source_url(self, photo_data: dict, candidate_url: Optional[str]) -> None:
        """Update photo_data['source_url'] when a longer canonical URL is found."""
        if not candidate_url:
            return

        existing = photo_data.get('source_url')
        if not existing or len(candidate_url) > len(existing):
            photo_data['source_url'] = candidate_url


    def _sort_urls_by_domain_preference(self, urls: List[str], preferred_domains: List[str]) -> List[str]:
        """Sort URLs so account-preferred domains are evaluated first."""
        if not urls or not preferred_domains:
            return urls

        def priority(url: str):
            lower_url = url.lower()
            for idx, domain in enumerate(preferred_domains):
                if domain and domain.lower() in lower_url:
                    return (0, idx, -len(url))
            return (1, len(preferred_domains), -len(url))

        return sorted(urls, key=priority)

    def _validate_url_accessibility(self, url: str) -> bool:
        """Check if a URL is accessible by making a HEAD request, falling back to GET if needed."""
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; TravelmemoBot/1.0)'}
        try:
            # Try HEAD request first (faster)
            response = requests.head(url, timeout=5, allow_redirects=True, headers=headers)
            # Consider 2xx and 3xx status codes as accessible
            is_accessible = 200 <= response.status_code < 400

            # If HEAD fails with 405 (Method Not Allowed) or 403, try GET
            if response.status_code in [403, 405]:
                self.logger.debug(f"HEAD request returned {response.status_code} for {url}, trying GET")
                response = requests.get(url, timeout=5, allow_redirects=True, stream=True, headers=headers)
                # Only read headers, don't download body
                response.close()
                is_accessible = 200 <= response.status_code < 400

            self.logger.debug(f"URL accessibility check for {url}: {response.status_code} ({'accessible' if is_accessible else 'not accessible'})")
            return is_accessible
        except requests.exceptions.RequestException as e:
            self.logger.debug(f"URL accessibility check failed for {url}: {e}")
            # If validation fails, assume URL is accessible and let _load_blog_content handle errors
            # This prevents false negatives from overly restrictive servers
            return True



    def _load_blog_content(self, blog_url: str) -> Optional[Dict[str, any]]:
        """Fetch blog content with caching."""
        if not blog_url:
            return None

        if blog_url in self._blog_content_cache:
            return self._blog_content_cache[blog_url]

        content = self.blog_extractor.get_blog_content(blog_url)
        self._blog_content_cache[blog_url] = content
        return content



    def _get_blog_content_context(self, photo_data: dict) -> Optional[BlogContextMatch]:
        """Select the most relevant blog context for the given photo."""
        raw_candidate_urls = getattr(self.config, "blog_post_urls", [])
        candidate_urls = list(raw_candidate_urls or [])
        if not candidate_urls:
            default_url = self.config.get_default_blog_post_url()
            if default_url:
                candidate_urls = [default_url]

        exif_hints = photo_data.get('exif_hints') or {}
        source_urls = exif_hints.get('source_urls', [])

        prioritized_urls: List[str] = []

        def append_url(url: Optional[str]) -> None:
            if url and url not in prioritized_urls:
                prioritized_urls.append(url)

        if source_urls:
            # Apply domain preferences to EXIF URLs first, then sort by length within same domain preference
            account_config = get_account_config(self.config.account)
            preferred_domains = account_config.blog_domains if account_config else []

            # Sort EXIF URLs by domain preference first, then by length
            sorted_source_urls = self._sort_urls_by_domain_preference(source_urls, preferred_domains)

            # Log the URL selection decision for debugging
            self.logger.debug(f"EXIF URLs before domain sorting: {source_urls}")
            self.logger.debug(f"EXIF URLs after domain sorting: {sorted_source_urls}")
            self.logger.debug(f"Account '{self.config.account}' preferred domains: {preferred_domains}")

            for url in sorted_source_urls:
                if any(existing.startswith(url) and len(existing) > len(url) for existing in prioritized_urls):
                    continue
                append_url(url)
        for url in candidate_urls:
            append_url(url)

        candidate_urls = prioritized_urls

        if not candidate_urls:
            return None

        # Strict domain filter: only evaluate URLs matching the account's primary domain
        account_config = get_account_config(self.config.account)
        primary_domain = (account_config.blog_domains[0]
                          if account_config and account_config.blog_domains
                          else None)
        if primary_domain:
            domain_filtered = [u for u in candidate_urls if primary_domain.lower() in u.lower()]
            if domain_filtered:
                self.logger.debug(f"Strict domain filter: kept {len(domain_filtered)}/{len(candidate_urls)} URLs matching '{primary_domain}'")
                candidate_urls = domain_filtered

        best_match: Optional[BlogContextMatch] = None

        for url in candidate_urls:
            # Validate URL accessibility first
            if not self._validate_url_accessibility(url):
                self.logger.debug(f"Skipping inaccessible URL: {url}")
                continue

            content = self._load_blog_content(url)
            if not content:
                continue

            match = self.blog_extractor.find_relevant_content(content, photo_data)

            # Keep track of best match
            if match and (not best_match or match.score > best_match.score):
                best_match = match

        if best_match:
            photo_data['selected_blog'] = {
                'url': best_match.url,
                'context_snippet': best_match.context,
                'matched_terms': list(best_match.matched_terms),
                'derived_from_exif': best_match.url in source_urls
            }
            self._ensure_longest_source_url(photo_data, best_match.url)
            return best_match

        # Find the first accessible URL as fallback
        fallback_url = None
        for url in candidate_urls:
            if self._validate_url_accessibility(url):
                fallback_url = url
                break

        if fallback_url:
            photo_data['selected_blog'] = {
                'url': fallback_url,
                'context_snippet': None,
                'matched_terms': [],
                'derived_from_exif': fallback_url in source_urls
            }
            self._ensure_longest_source_url(photo_data, fallback_url)
            self.logger.debug("No relevant blog context match found; using accessible fallback URL %s", fallback_url)
            # Return a minimal match object for the fallback
            return BlogContextMatch(
                url=fallback_url,
                context="",
                score=0,
                matched_terms=tuple()
            )
        else:
            self.logger.warning("No accessible URLs found in candidate list: %s", candidate_urls)

        return None




