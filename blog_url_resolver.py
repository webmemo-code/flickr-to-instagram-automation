"""
Centralized blog URL selection for the automation pipeline.

Consolidates the URL candidate building and domain filtering that was
previously duplicated across caption_generator.py (two locations).
"""
import re
import logging
from typing import Optional, List

from config import Config
from account_config import AccountConfig, get_account_config
from photo_models import EnrichedPhoto

logger = logging.getLogger(__name__)


def get_candidate_blog_urls(config: Config, photo: EnrichedPhoto) -> List[str]:
    """Build a domain-filtered, priority-ordered list of blog URLs for this photo.

    Priority order:
    1. EXIF source URLs (sorted by account domain preference, longer URLs preferred)
    2. Configured BLOG_POST_URL(S) from environment
    3. photo.source_url from Flickr description

    All results are strictly filtered to the account's primary domain.
    """
    account_config = get_account_config(config.account)
    primary_domain = (account_config.blog_domains[0]
                      if account_config and account_config.blog_domains
                      else None)
    preferred_domains = account_config.blog_domains if account_config else []

    # Collect all candidate URLs in priority order
    candidates: List[str] = []
    seen: set = set()

    def add(url: Optional[str]) -> None:
        if url and url not in seen:
            # Skip shorter prefixes when a longer version already exists
            if any(existing.startswith(url) and len(existing) > len(url) for existing in seen):
                return
            seen.add(url)
            candidates.append(url)

    # 1. EXIF source URLs (highest priority — most photo-specific)
    exif_hints = photo.exif_hints or {}
    source_urls = exif_hints.get('source_urls', [])
    if source_urls:
        sorted_urls = _sort_urls_by_domain_preference(source_urls, preferred_domains)
        for url in sorted_urls:
            add(url)

    # 2. Configured blog URLs from environment
    configured_urls = list(getattr(config, 'blog_post_urls', []) or [])
    if not configured_urls:
        default_url = config.get_default_blog_post_url()
        if default_url:
            configured_urls = [default_url]
    for url in configured_urls:
        add(url)

    # 3. Source URL from Flickr description (already domain-filtered by flickr_api)
    if photo.source_url:
        add(photo.source_url)

    # Strict domain filter
    if primary_domain:
        filtered = [u for u in candidates if primary_domain.lower() in u.lower()]
        logger.debug(f"Domain filter: kept {len(filtered)}/{len(candidates)} URLs matching '{primary_domain}'")
        return filtered

    return candidates


def resolve_blog_url(config: Config, photo: EnrichedPhoto) -> Optional[str]:
    """Resolve the single best blog URL for this photo.

    Returns the highest-priority URL that matches the account's primary domain,
    or None if no matching URL is found.
    """
    urls = get_candidate_blog_urls(config, photo)
    return urls[0] if urls else None


def _sort_urls_by_domain_preference(urls: List[str], preferred_domains: List[str]) -> List[str]:
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
