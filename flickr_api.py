"""
Flickr API integration for photo retrieval and metadata extraction.
"""
import requests
import json
import logging
from typing import Dict, List, Optional, Tuple
from config import Config


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
            'nojsoncallback': '1'
        }
        
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
        """Extract blog post URL from description or photo metadata."""
        import re
        
        # Look for URLs in description
        if description:
            url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+[^\s<>"{}|\\^`\[\],.]'
            urls = re.findall(url_pattern, description)
            
            # Filter for blog URLs (travelmemo.com, reisememo.ch, etc.)
            for url in urls:
                if any(domain in url.lower() for domain in ['travelmemo.com', 'reisememo.ch', 'blog']):
                    return url
            
            # Return first URL if no blog-specific URL found
            if urls:
                return urls[0]
        
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
    
    def get_unposted_photos(self) -> List[Dict]:
        """Get list of photos that haven't been posted yet."""
        photoset_id = self.config.flickr_album_id
        
        photos_data = self.get_photos_from_photoset(photoset_id)
        if not photos_data:
            return []
        
        photos = []
        for index, photo in enumerate(photos_data['photoset']['photo']):
            # Get additional photo information
            photo_info, description = self.get_photo_info(photo['id'])
            location_data = self.get_photo_location(photo['id'])
            exif_data = self.get_photo_exif(photo['id'])
            
            # Build photo URL
            photo_url = self.build_photo_url(photo)
            
            # Extract additional URLs and context
            photo_page_url = self.get_photo_page_url(photo_info)
            source_url = self.extract_source_url(description, photo_info)
            
            # Extract hashtags
            hashtags = self.extract_hashtags(photo_info, location_data)
            
            photo_data = {
                'id': photo['id'],
                'title': photo['title'],
                'description': description,
                'url': photo_url,
                'hashtags': hashtags,
                'server': photo['server'],
                'secret': photo['secret'],
                'album_position': index + 1,  # Add position in album (1-based)
                'photo_page_url': photo_page_url,
                'source_url': source_url,
                'exif_data': exif_data,
                'location_data': location_data
            }
            photos.append(photo_data)
        
        self.logger.info(f"Retrieved {len(photos)} photos from album {photoset_id} in order")
        return photos