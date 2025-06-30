# Claude Context for Flickr to Instagram Automation

## Project Overview
This is a Python automation system that posts one photo per day from a specific Flickr album to Instagram with AI-generated captions using GitHub Actions and OpenAI GPT Vision. The system uses enhanced context from EXIF data, location information, and blog post URLs to generate more specific and engaging captions.

## Key Components

### Core Files
- `main.py` - Main orchestration script
- `config.py` - Configuration management (environment variables)
- `flickr_api.py` - Flickr API integration for photo retrieval
- `caption_generator.py` - OpenAI GPT-4 Vision caption generation
- `instagram_api.py` - Instagram Graph API posting
- `state_manager.py` - GitHub Issues-based state management
- `requirements.txt` - Python dependencies

### Dependencies
- `requests>=2.31.0` - HTTP requests
- `openai>=1.3.0` - OpenAI API integration
- `PyGithub>=1.59.0` - GitHub API integration
- `python-dotenv>=1.0.0` - Environment variable management

## Testing Commands
Use these commands for testing and maintenance:

```bash
# Install dependencies
pip install -r requirements.txt

# Test without posting (dry run)
python main.py --dry-run

# Post next photo (live)
python main.py

# Show statistics and progress
python main.py --stats

# Debug mode
python main.py --log-level DEBUG --dry-run
```

## Configuration
All configuration is done via environment variables/GitHub repository settings:

### Required Secrets
- `FLICKR_API_KEY` - Your Flickr API key
- `FLICKR_USER_ID` - Your Flickr user ID
- `INSTAGRAM_ACCESS_TOKEN` - Instagram Graph API access token
- `INSTAGRAM_ACCOUNT_ID` - Instagram business account ID
- `OPENAI_API_KEY` - OpenAI API key

### Required Variables
- `FLICKR_USERNAME` - Your Flickr username
- `FLICKR_ALBUM_ID` - Target Flickr album ID
- `GRAPH_API_VERSION` - Facebook/Instagram API version (e.g., v18.0)
- `OPENAI_MODEL` - OpenAI model (e.g., gpt-4o-mini)

## Architecture
- **Infrastructure**: GitHub Actions for automation, Python 3.11 runtime
- **State Management**: GitHub Issues API for progress tracking
- **External APIs**: Flickr API, Instagram Graph API, OpenAI GPT-4 Vision
- **Security**: GitHub Secrets for credential management

## Enhanced Caption Generation
The system now collects rich context for better captions:

### Context Sources
- **Photo Metadata**: Title, description from Flickr
- **Blog URLs**: Automatically extracts blog post URLs from photo descriptions (travelmemo.com, reisememo.ch)
- **Location Data**: City, region, country from Flickr geo-tagging
- **EXIF Data**: Camera make/model and technical settings
- **Flickr URLs**: Photo page URLs for reference

### Smart Fallback
- Uses enhanced travel-focused prompts when context is available
- Falls back to generic prompts when no additional context exists
- Logs which approach is used for each photo

## Workflow
1. Fetches photos from specified Flickr album with enhanced metadata
2. Identifies next unposted photo using GitHub Issues state
3. Collects additional context (EXIF, location, blog URLs)
4. Generates AI caption using OpenAI GPT-4 Vision with enhanced context
5. Posts to Instagram via Graph API
6. Records success/failure in GitHub Issues
7. Stops automatically when album is complete

## Recent Changes
- Enhanced caption generation with EXIF data, location context, and blog URL extraction
- Smart fallback system for photos without additional metadata
- Improved Flickr API integration with additional metadata collection
- Updated caption generator to use rich context for more specific Instagram captions

## Current Status
Repository is clean with recent commits focused on README documentation improvements. Enhanced caption generation system implemented and ready for testing.