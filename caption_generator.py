"""
OpenAI GPT-4 Vision integration for generating Instagram captions.
"""
import time
import logging
from openai import OpenAI
from typing import Optional, Dict, List
from config import Config
from blog_content_extractor import BlogContentExtractor, BlogContextMatch
from account_config import is_secondary_account, get_account_config


class CaptionGenerator:
    """Generate Instagram captions using OpenAI GPT-4 Vision."""
    
    def __init__(self, config: Config):
        self.config = config
        self.client = OpenAI(api_key=config.openai_api_key)
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
            
            # Add blog post content context (NEW FEATURE)
            blog_match = self._get_blog_content_context(photo_data)
            if blog_match:
                context_parts.append(f"Blog context: {blog_match.context}")
                self.logger.info(
                    f"Added blog content context for photo {photo_data.get('id')} from {blog_match.url}"
                )
            
            # Build the enhanced prompt
            context_text = "\n".join(context_parts) if context_parts else ""

            account_config = get_account_config(self.config.account)
            if context_text:
                # Enhanced prompt with context - use account language configuration
                if account_config and account_config.language == 'de':
                    # German prompts for German-language accounts
                    prompt_base = ("Du bist eine Schweizer Instagram Influencerin, die Reisefotos veröffentlicht. Erstelle eine Instagram Caption "
                                  "in fünf kurzen Sätzen auf Deutsch. Verwende für jeden Satz einen neuen Absatz. "
                                  "Schreibe sachlich, authentisch, persönlich und duze deine Follower. Nutze den gegebenen Blog-Kontext, "
                                  "um eine spezifische Caption zu erstellen, die den Ort, die Geschichte oder den Kontext erwähnt." 
                                  "Verwende kein scharfes 'ß', sondern 'ss' wie in der Schweiz. "
                                  "Nutze Emojis nur sparsam und passend.")
                    
                    # Add special instructions for blog context in German
                    if blog_match:
                        prompt_base += (" Achte besonders auf die 'Blog context' Informationen, die redaktionelle Beschreibungen "
                                       "aus dem Reiseblog-Post enthalten, in dem dieses Foto erscheint. Nutze diesen umfangreichen Kontext, "
                                       "um eine informative Caption zu erstellen, die mehr über das Reiseziel erzählt.")
                else:
                    # English prompts for English-language accounts
                    prompt_base = ("You are an Instagram influencer who publishes travel photos. Create an Instagram caption "
                                  "in five short sentences. Add a new paragraph for each sentence. "
                                  "Make it factual, authentic and personal. Use the provided blog post context "
                                  "to create a specific caption that references the location, story, or context. "
                                  "Do not use the terms 'I can\'t wait to share more...' or 'Stay tuned for more...'."
                                  "Use emojis sparingly and appropriately.")
                    
                    # Add special instructions for blog context in English
                    if blog_match:
                        prompt_base += (" Pay special attention to the 'Blog context' information, which contains editorial descriptions "
                                       "from the travel blog post where this photo appears. Use this rich context to create a more "
                                       "informative caption that tells more about the destination the photo was taken.")
                
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
            
            response = self.client.chat.completions.create(
                model=self.config.openai_model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": photo_data['url']}
                            }
                        ]
                    }
                ],
                max_tokens=400,
                temperature=0.1
            )
            
            generated_text = response.choices[0].message.content
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
            indexed_sources = [
                (idx, url) for idx, url in enumerate(source_urls) if url
            ]
            for _, url in sorted(indexed_sources, key=lambda item: (-len(item[1]), item[0])):
                if any(existing.startswith(url) and len(existing) > len(url) for existing in prioritized_urls):
                    continue
                append_url(url)
        for url in candidate_urls:
            append_url(url)

        candidate_urls = prioritized_urls

        if not candidate_urls:
            return None

        best_match: Optional[BlogContextMatch] = None

        for url in candidate_urls:
            content = self._load_blog_content(url)
            if not content:
                continue

            match = self.blog_extractor.find_relevant_content(content, photo_data)
            if not match:
                continue

            normalized = match if match.url else BlogContextMatch(
                url=url,
                context=match.context,
                score=match.score,
                matched_terms=match.matched_terms
            )

            if not best_match or normalized.score > best_match.score:
                best_match = normalized

        if best_match:
            photo_data['selected_blog'] = {
                'url': best_match.url,
                'context_snippet': best_match.context,
                'matched_terms': list(best_match.matched_terms),
                'derived_from_exif': best_match.url in source_urls
            }
            self._ensure_longest_source_url(photo_data, best_match.url)
            return best_match

        fallback_url = candidate_urls[0]
        photo_data['selected_blog'] = {
            'url': fallback_url,
            'context_snippet': None,
            'matched_terms': [],
            'derived_from_exif': fallback_url in source_urls
        }
        self._ensure_longest_source_url(photo_data, fallback_url)
        self.logger.debug("No relevant blog context match found; using fallback URL %s", fallback_url)
        return None




