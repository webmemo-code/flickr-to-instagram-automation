"""
OpenAI GPT-4 Vision integration for generating Instagram captions.
"""
import time
import logging
from openai import OpenAI
from typing import Optional
from config import Config


class CaptionGenerator:
    """Generate Instagram captions using OpenAI GPT-4 Vision."""
    
    def __init__(self, config: Config):
        self.config = config
        self.client = OpenAI(api_key=config.openai_api_key)
        self.logger = logging.getLogger(__name__)
    
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
            
            # Build the enhanced prompt
            context_text = "\n".join(context_parts) if context_parts else ""
            
            if context_text:
                # Enhanced prompt with context
                prompt = ("You are an Instagram influencer for travel content. Create an engaging Instagram caption "
                         "in two short paragraphs (2 sentences each). Do not number paragraphs or use quotation marks. "
                         "Make it engaging, authentic and personal. Use the provided context to create a more specific and "
                         "engaging caption that references the location, story, or context when available.")
                prompt += f"\n\nContext about this photo:\n{context_text}"
                self.logger.debug(f"Using enhanced prompt with context for photo {photo_data.get('id')}")
            else:
                # Fallback to original prompt style when no context available
                prompt = ("You are an Instagram influencer. Describe this image in two very short paragraphs "
                         "with two sentences each. They serve as Instagram captions. Do not number the paragraphs nor the sentences. "
                         "Do not use quotation marks. Keep it engaging, personal and authentic.")
                self.logger.debug(f"Using basic prompt (no context available) for photo {photo_data.get('id')}")
            
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
                max_tokens=120,
                temperature=0.7
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
        
        # Add standard footer
        caption_parts.append("Travelmemo from a one-of-a-kind travel experience.")
        
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
