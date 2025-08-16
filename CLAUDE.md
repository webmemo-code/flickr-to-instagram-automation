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
- `state_manager.py` - Repository Variables-based state management for unlimited scale
- `requirements.txt` - Python dependencies

### Dependencies
- `requests>=2.32.4` - HTTP requests
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

### Optional Variables
- `CREATE_AUDIT_ISSUES` - Set to `true` to create GitHub Issues for audit trail (default: `false` for scale)

## Architecture
- **Infrastructure**: GitHub Actions for automation, Python 3.11 runtime
- **State Management**: GitHub Repository Variables for unlimited scalability
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
2. Identifies next unposted photo using position-based tracking
3. Collects additional context (EXIF, location, blog URLs)
4. Generates AI caption using OpenAI GPT-4 Vision with enhanced context
5. Posts to Instagram via Graph API
6. Records success/failure in Repository Variables
7. Stops automatically when album is complete

## Recent Changes
- **MAJOR MIGRATION**: Migrated from GitHub Issues to Repository Variables for state management
- **Unlimited Scalability**: System now handles thousands of photos without repository pollution
- **Zero Issue Creation**: By default, no GitHub Issues are created (configurable via `CREATE_AUDIT_ISSUES`)
- **Position-Based Tracking**: Uses photo positions instead of individual ID tracking
- **Complete Audit Trail**: All Instagram post data stored in repository variables
- Enhanced caption generation with EXIF data, location context, and blog URL extraction
- Smart fallback system for photos without additional metadata
- Improved Flickr API integration with additional metadata collection

## Current Status
**OPTIMIZED FOR SCALE**: Repository Variables migration complete - Ready for unlimited photos ✅

## State Management Migration (August 2025)

### Major Architecture Change: GitHub Issues → Repository Variables

**Migration Completed**: August 13, 2025

#### Previous System Limitations
- **Scale Problem**: Each photo created a GitHub Issue (127+ issues for small album)
- **Repository Pollution**: Automation issues cluttered actual project issues
- **Performance Degradation**: API calls got slower with more issues
- **Thousands of Photos**: Would create thousands of issues = unusable repository

#### New Repository Variables System
**Benefits**:
- **Unlimited Scalability**: O(1) performance regardless of album size (1000s+ photos)
- **Zero Repository Pollution**: No GitHub Issues created by default
- **Lightning Fast**: Constant performance for any number of photos
- **Complete Audit Trail**: All data preserved in repository variables

**State Variables Created**:
- `LAST_POSTED_POSITION_{album_id}` - Current progression through album
- `TOTAL_ALBUM_PHOTOS_{album_id}` - Total photos in album
- `FAILED_POSITIONS_{album_id}` - Failed positions for retry
- `INSTAGRAM_POSTS_{album_id}` - Complete Instagram post audit trail

#### Migration Results
- **Issues Cleaned**: 127 → 0 automation issues (93% reduction)
- **Performance**: Constant O(1) operations
- **Scalability**: Ready for unlimited photos
- **Audit Trail**: Complete preservation in variables

**CURRENT STATUS** (August 15, 2025):
- **Major Issue**: ❌ **SYSTEM STILL BROKEN** - Posted first photo instead of position 21
- **Root Cause**: Repository Variables not being read correctly OR logic still flawed
- **Variable Reading**: ❌ **NOT WORKING** (despite manual variables created)
- **Variable Writing**: ❌ **BLOCKED** (GitHub Actions permissions: 403 Forbidden)
- **Manual Test Result**: ❌ Posted position 1 instead of continuing from position 20
- **Automation Status**: ❌ **BROKEN** (not respecting existing state)

**Critical Problem**:
Repository Variables cannot be written by GitHub Actions despite `actions: write` permission. Error:
```
Failed to set variable LAST_POSTED_POSITION_72177720326837749: Resource not accessible by integration: 403
```

**Manual Variables Created** (to start system):
- `LAST_POSTED_POSITION_72177720326837749` = `20`
- `FAILED_POSITIONS_72177720326837749` = `[5,6,7,8,11,12,13,14,15,16]`
- `INSTAGRAM_POSTS_72177720326837749` = `[]`
- `TOTAL_ALBUM_PHOTOS_72177720326837749` = `0`

**Environment Protection Rules**: Adding reviewer requirement interrupts automation (defeats purpose)

**Next Session TODO**: 
1. **DEBUG**: Why Repository Variables not being read (should show position 20, not 0)
2. **INVESTIGATE**: Check if variables are accessible to GitHub Actions at all
3. **ALTERNATIVE**: Consider reverting to optimized GitHub Issues approach
4. **TEST**: Verify variable reading logic in state_manager.py

**Files Modified for Migration**:
- `state_manager.py` - Complete rewrite for Repository Variables API
- `main.py` - Updated to use new state management system
- `config.py` - Added `CREATE_AUDIT_ISSUES` configuration option
- `cleanup_legacy_issues.py` - Script to clean up legacy automation issues
- `.env.example.txt` - Documented new configuration options

## Commit Message Convention
Always use these prefixes for commit messages (capitalized for visibility):
- **UPDATE** | When adding functionality
- **FIXING** | For intermediate fixes  
- **FIXED** | When fixing is complete
- **SECURITY** | For security fixes
- **INIT** | For initial file uploads

Format: `[PREFIX] | [Description]`
Example: `UPDATE | Add image retry mechanism for Flickr URL validation`