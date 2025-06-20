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
    
    def generate_caption(self, image_url: str, title: str = "", description: str = "") -> Optional[str]:
        """Generate an Instagram caption for the given image."""
        try:
            # Prepare the prompt
            prompt = ("You are an Instagram influencer. Describe this image in two very short paragraphs "
                     "with two sentences each. They serve as Instagram captions. Do not number the paragraphs nor the sentences. "
                     "Do not use quotation marks. Keep it engaging and authentic. If a title or a caption "
                      "is provided with the image, refer to it in your copy.")
            
            response = self.client.chat.completions.create(
                model=self.config.openai_model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": image_url}
                            }
                        ]
                    }
                ],
                max_tokens=80,
                temperature=0.7
            )
            
            generated_text = response.choices[0].message.content
            self.logger.info(f"Generated caption for image: {image_url[:50]}...")
            
            return generated_text
            
        except Exception as e:
            self.logger.error(f"Failed to generate caption for {image_url}: {e}")
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
    
    def generate_with_retry(self, image_url: str, title: str = "", description: str = "", max_retries: int = 3) -> Optional[str]:
        """Generate caption with retry logic for rate limiting."""
        for attempt in range(max_retries):
            try:
                caption = self.generate_caption(image_url, title, description)
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
