"""
Flickr API integration for photo retrieval and metadata extraction.
"""
import requests
import json
import logging
import re
from typing import Dict, List, Optional, Tuple
from config import Config
from account_config import get_account_config


class FlickrAPI:
    """Flickr API client for photo operations."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def get_photos_from_photoset(self, photoset_id: str) -> Optional[Dict]:
        """Retrieve photos from a Flickr photoset."""
        params = {
            'method': 'flickr.photosets.getPhotos',
            'api_key': self.config.flickr_api_key,
            'user_id': self.config.flickr_user_id,
            'photoset_id': photoset_id,
            'format': 'json',
            'nojsoncallback': '1',
            'extras': 'date_taken'  # Include date taken for proper chronological sorting
        }
        
        # Log the request details for debugging
        self.logger.debug(f"Flickr API request: {params['method']} for photoset {photoset_id}")
        
        try:
            response = requests.get(self.config.flickr_api_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            if data.get('stat') == 'ok':
                self.logger.info(f"Retrieved {len(data['photoset']['photo'])} photos from photoset {photoset_id}")
                return data
            else:
                self.logger.error(f"Flickr API error: {data.get('message', 'Unknown error')}")
                return None
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to retrieve photos from photoset {photoset_id}: {e}")
            return None
        except (KeyError, TypeError) as e:
            self.logger.error(f"Unexpected Flickr API response structure: {e}")
            self.logger.error(f"Response data: {data if 'data' in locals() else 'No data'}")
            return None
    
    def get_photo_info(self, photo_id: str) -> Tuple[Optional[Dict], str]:
        """Get detailed photo information including description and tags."""
        params = {
            'method': 'flickr.photos.getInfo',
            'api_key': self.config.flickr_api_key,
            'photo_id': photo_id,
            'format': 'json',
            'nojsoncallback': '1'
        }
        
        try:
            response = requests.get(self.config.flickr_api_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            if data.get('stat') == 'ok':
                description = data['photo']['description']['_content']
                self.logger.debug(f"Retrieved info for photo {photo_id}")
                return data, description
            else:
                self.logger.error(f"Flickr API error for photo {photo_id}: {data.get('message', 'Unknown error')}")
                return None, ""
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to get photo info for {photo_id}: {e}")
            return None, ""
    
    def get_photo_location(self, photo_id: str) -> Optional[Dict]:
        """Get geographical location data for a photo."""
        params = {
            'method': 'flickr.photos.geo.getLocation',
            'api_key': self.config.flickr_api_key,
            'photo_id': photo_id,
            'format': 'json',
            'nojsoncallback': '1'
        }
        
        try:
            response = requests.get(self.config.flickr_api_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            if data.get('stat') == 'ok':
                self.logger.debug(f"Retrieved location for photo {photo_id}")
                return data
            else:
                # Location data might not be available for all photos
                self.logger.debug(f"No location data for photo {photo_id}")
                return None
                
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"Failed to get location for photo {photo_id}: {e}")
            return None
    
    def get_photo_exif(self, photo_id: str) -> Optional[Dict]:
        """Get EXIF data for a photo."""
        params = {
            'method': 'flickr.photos.getExif',
            'api_key': self.config.flickr_api_key,
            'photo_id': photo_id,
            'format': 'json',
            'nojsoncallback': '1'
        }
        
        try:
            response = requests.get(self.config.flickr_api_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            if data.get('stat') == 'ok':
                self.logger.debug(f"Retrieved EXIF data for photo {photo_id}")
                return data
            else:
                self.logger.debug(f"No EXIF data available for photo {photo_id}")
                return None
                
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"Failed to get EXIF data for photo {photo_id}: {e}")
            return None
    
    def extract_exif_hints(self, exif_data: Optional[Dict]) -> Dict[str, List[str]]:
        """Extract structured hints from photo EXIF metadata."""
        hints = {
            'source_urls': [],
            'phrases': [],
            'keywords': []
        }

        if not exif_data:
            return hints

        exif_entries = exif_data.get('photo', {}).get('exif', [])
        if not exif_entries:
            return hints

        def normalize_value(value: str) -> str:
            return re.sub(r"\s+", " ", value.strip())

        def add_unique(container: List[str], value: str) -> None:
            cleaned = normalize_value(value)
            if cleaned and cleaned not in container:
                container.append(cleaned)

        for entry in exif_entries:
            label = entry.get('label') or entry.get('tag') or ''
            value = entry.get('raw', {}).get('_content', '')
            if not value:
                continue

            label_key = re.sub(r"[^a-z0-9]", "", label.lower())
            normalized_value = normalize_value(value)

            if not normalized_value:
                continue

            if label_key in {'source', 'sourceurl'}:
                if normalized_value.startswith(('http://', 'https://')):
                    add_unique(hints['source_urls'], normalized_value)
                add_unique(hints['phrases'], normalized_value)
                continue

            if label_key in {'keywords', 'supplementalcategories', 'category'}:
                parts = re.split(r"[;,|]", value)
                for part in parts:
                    add_unique(hints['keywords'], part)
                continue

            if label_key in {
                'organization', 'event', 'objectname', 'headline', 'title',
                'transmissionreference', 'originaltransmissionreference'
            }:
                add_unique(hints['phrases'], normalized_value)
                continue

            if label_key in {'city', 'sublocation', 'sublocation', 'provinceorstate', 'provincestate', 'state', 'country', 'location'}:
                add_unique(hints['phrases'], normalized_value)
                continue

            # Add generic catch-all for notable string fields
            if len(normalized_value) > 3:
                add_unique(hints['phrases'], normalized_value)

        return hints

    def build_photo_url(self, photo: Dict) -> str:
        """Build the Flickr photo URL."""
        return f"https://live.staticflickr.com/{photo['server']}/{photo['id']}_{photo['secret']}_c.jpg"
    
    def get_photo_page_url(self, photo_info: Dict) -> Optional[str]:
        """Extract the Flickr photo page URL from photo info."""
        if photo_info and 'photo' in photo_info and 'urls' in photo_info['photo']:
            for url_entry in photo_info['photo']['urls']['url']:
                if url_entry.get('type') == 'photopage':
                    return url_entry['_content']
        return None
    
    def extract_source_url(self, description: str, photo_info: Dict) -> Optional[str]:
        """Extract blog post URL from description, strictly matching the account's primary domain."""
        import re

        if not description:
            return None

        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+[^\s<>"{}|\\^`\[\],.]'
        urls = re.findall(url_pattern, description)
        if not urls:
            return None

        # Strict: only accept URLs from the account's primary (first) domain
        account_config = get_account_config(self.config.account)
        primary_domain = (account_config.blog_domains[0]
                          if account_config and account_config.blog_domains
                          else None)

        if primary_domain:
            for url in urls:
                if primary_domain.lower() in url.lower():
                    return url

        return None
    
    def extract_hashtags(self, photo_info: Dict, location_data: Optional[Dict] = None) -> str:
        """Extract and format hashtags from photo tags and location data."""
        hashtags = []
        
        # Extract tags from photo info
        if photo_info and 'photo' in photo_info and 'tags' in photo_info['photo']:
            for tag in photo_info['photo']['tags']['tag']:
                hashtag = f"#{tag['_content']}"
                hashtags.append(hashtag)
        
        # Extract location-based hashtags
        if location_data and 'photo' in location_data and 'location' in location_data['photo']:
            location = location_data['photo']['location']
            for field in ['locality', 'neighbourhood', 'county', 'region', 'country']:
                if field in location and '_content' in location[field]:
                    content = location[field]['_content'].replace(' ', '')
                    if content:  # Only add non-empty tags
                        hashtag = f"#{content}"
                        hashtags.append(hashtag)
        
        return ' '.join(hashtags)
    
    def get_photoset_info(self, photoset_id: str) -> Optional[Dict]:
        """Get photoset information including title."""
        params = {
            'method': 'flickr.photosets.getInfo',
            'api_key': self.config.flickr_api_key,
            'user_id': self.config.flickr_user_id,
            'photoset_id': photoset_id,
            'format': 'json',
            'nojsoncallback': '1'
        }
        
        try:
            response = requests.get(self.config.flickr_api_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            if data.get('stat') == 'ok':
                self.logger.debug(f"Retrieved info for photoset {photoset_id}")
                return data
            else:
                self.logger.error(f"Flickr API error for photoset {photoset_id}: {data.get('message', 'Unknown error')}")
                return None
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to get photoset info for {photoset_id}: {e}")
            return None

    def get_album_photo_count(self, photoset_id: Optional[str] = None) -> int:
        """Get the total number of photos in an album with a single API call."""
        photoset_id = photoset_id or self.config.flickr_album_id
        info = self.get_photoset_info(photoset_id)
        if info and 'photoset' in info:
            count = int(info['photoset'].get('count_photos', 0))
            self.logger.info(f"Album {photoset_id} has {count} photos")
            return count
        return 0

    def get_photo_list(self) -> List[Dict]:
        """Get lightweight photo list from album (single API call, no per-photo metadata)."""
        photoset_id = self.config.flickr_album_id

        photos_data = self.get_photos_from_photoset(photoset_id)
        if not photos_data:
            return []

        photos = []
        for photo in photos_data['photoset']['photo']:
            photos.append({
                'id': photo['id'],
                'title': photo['title'],
                'url': self.build_photo_url(photo),
                'server': photo['server'],
                'secret': photo['secret'],
                'date_taken': photo.get('datetaken', ''),
            })

        # Sort by date taken (oldest first) for chronological publication order
        photos.sort(key=lambda x: x['date_taken'] or '9999-12-31 23:59:59')

        # Assign album positions based on chronological order
        for index, photo in enumerate(photos):
            photo['album_position'] = index + 1

        self.logger.info(f"Retrieved {len(photos)} photos from album {photoset_id} (lightweight listing)")
        return photos

    def enrich_photo(self, photo: Dict) -> Dict:
        """Fetch detailed metadata (info, location, EXIF) for a single photo."""
        photo_id = photo['id']

        photo_info, description = self.get_photo_info(photo_id)
        location_data = self.get_photo_location(photo_id)
        exif_data = self.get_photo_exif(photo_id)

        photo['description'] = description
        photo['photo_page_url'] = self.get_photo_page_url(photo_info)
        photo['source_url'] = self.extract_source_url(description, photo_info)
        photo['hashtags'] = self.extract_hashtags(photo_info, location_data)
        photo['exif_data'] = exif_data
        photo['exif_hints'] = self.extract_exif_hints(exif_data)
        photo['location_data'] = location_data

        self.logger.info(f"Enriched photo #{photo.get('album_position', '?')}: {photo['title']}")
        return photo

    def get_unposted_photos(self) -> List[Dict]:
        """Get all photos with full metadata. Use get_photo_list() + enrich_photo() instead for efficiency."""
        photos = self.get_photo_list()
        for photo in photos:
            self.enrich_photo(photo)
        return photos