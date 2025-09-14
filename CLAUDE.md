# Claude Context for Flickr to Instagram Automation

## Project Overview
This is a social media automation that posts one photo per day from a specific Flickr album to Instagram with AI-generated captions using GitHub Actions and OpenAI GPT Vision.

The system uses enhanced context from EXIF data, location information, and blog post URLs to generate more specific and engaging captions.

## Key Components

### Core Files
- `main.py` - Main orchestration script
- `config.py` - Configuration management (environment variables)
- `flickr_api.py` - Flickr API integration for photo retrieval
- `caption_generator.py` - OpenAI GPT-4 Vision caption generation
- `instagram_api.py` - Instagram Graph API posting
- `state_manager.py` - Repository variables-based state management for unlimited scale
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
- `OPENAI_API_KEY` - OpenAI API key

### Required Variables
- `FLICKR_USERNAME` - Your Flickr username
- `GRAPH_API_VERSION` - Facebook/Instagram API version (e.g., v18.0)
- `OPENAI_MODEL` - OpenAI model (e.g., gpt-4o-mini)

### Optional Variables
- `CREATE_AUDIT_ISSUES` - Set to `true` to create GitHub Issues for audit trail (default: `false` for scale)

### Environment-Specific Variables
- `BLOG_POST_URL` - URL to blog post with photo context (configure in GitHub environment settings, not repository variables)
- `FLICKR_ALBUM_ID` - Target Flickr album ID (configure in GitHub environment settings for multi-account support)
- `INSTAGRAM_ACCESS_TOKEN` - Instagram Graph API access token (configure in GitHub environment secrets for multi-account support)
- `INSTAGRAM_ACCOUNT_ID` - Instagram business account ID (configure in GitHub environment secrets for multi-account support)

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
- **CHRONOLOGICAL ORDERING**: Fixed photo publication order to ensure oldest photos are published first (September 2025)
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

**State Variables Architecture**:

**Environment Variables** (per-environment isolation):
- `LAST_POSTED_POSITION` - Current progression through album
- `FAILED_POSITIONS` - Failed positions for retry
- `INSTAGRAM_POSTS` - Complete Instagram post audit trail

**Repository Variables** (shared/global state):
- `TOTAL_ALBUM_PHOTOS_{album_id}` - Total photos in album (shared across environments)

#### Migration Results
- **Issues Cleaned**: 127 → 0 automation issues (93% reduction)
- **Performance**: Constant O(1) operations
- **Scalability**: Ready for unlimited photos
- **Audit Trail**: Complete preservation in variables

**CURRENT STATUS**:
- **Automation**: ✅ FULLY OPERATIONAL with Repository Variables
- **Scale**: ✅ UNLIMITED (ready for thousands of photos)
- **Performance**: ✅ LIGHTNING FAST (O(1) operations)
- **Repository**: ✅ CLEAN (zero automation issues)
- **Audit Trail**: ✅ COMPLETE (stored in variables)
- **Workflow schedule**: 📅 Daily at 18:13 UTC (20:13 CEST)

**Last Successful Test**: August 13, 2025 - Repository Variables system tested successfully

**Files Modified for Migration**:
- `state_manager.py` - Complete rewrite for Repository Variables API
- `main.py` - Updated to use new state management system
- `config.py` - Added `CREATE_AUDIT_ISSUES` configuration option
- `cleanup_legacy_issues.py` - Script to clean up legacy automation issues
- `.env.example.txt` - Documented new configuration options

## Photo Publication Order Fix (September 2025)

### Issue #145: Order of photos to publish
**Problem**: Photos were being published in Flickr album order, not chronological order by date taken.

**Solution Implemented**:
1. **Enhanced Flickr API Call**: Added `extras=date_taken` parameter to retrieve photo capture dates
2. **Chronological Sorting**: Photos now sorted by `date_taken` (oldest first) before position assignment
3. **Position Assignment**: Album positions now reflect chronological order (position 1 = oldest photo)
4. **Logging Enhancement**: Added detailed logging to verify correct chronological ordering

**Technical Changes**:
- `flickr_api.py`: Modified `get_photos_from_photoset()` to include date_taken data
- `flickr_api.py`: Updated `get_unposted_photos()` to sort by date_taken before position assignment
- `state_manager.py`: Updated comments to reflect chronological ordering
- Added comprehensive logging to verify photo ordering

**Result**: Automation now publishes photos in proper chronological sequence (oldest to newest), ensuring travel stories unfold in the correct temporal order.

## Environment Variable Architecture Fix (September 2025)

### Issue: LAST_POSTED_POSITION stored as repository variable instead of environment variable
**Problem**: State variables like `LAST_POSTED_POSITION_*`, `FAILED_POSITIONS_*`, and `INSTAGRAM_POSTS_*` were being stored as repository variables when they should be environment-specific.

**Architectural Issue**:
- Repository variables are global to all environments
- Each environment (reisememo, travelmemo, etc.) should have isolated state tracking
- Cross-environment state contamination was possible

**Solution Implemented**:
1. **Variable Classification**: Distinguished between environment-specific and repository-wide variables
2. **GitHub CLI Integration**: Used `gh variable set --env` for environment-specific variables
3. **Proper Isolation**: Each environment maintains its own state independently

**New Architecture**:

**Environment Variables** (per-environment isolation):
- `LAST_POSTED_POSITION_{album_id}` - Each environment tracks its own album progress (album-specific)
- `FAILED_POSITIONS_{album_id}` - Per-environment retry lists (album-specific)
- `INSTAGRAM_POSTS_{album_id}` - Environment-specific audit trails (album-specific)

**Repository Variables** (shared/global):
- `TOTAL_ALBUM_PHOTOS_{album_id}` - Album metadata shared across environments

**Technical Implementation**:
- Added `_is_environment_specific_variable()` method for classification
- Created `_set_environment_variable()` using GitHub CLI subprocess calls
- Updated `_get_environment_variable()` to fetch from proper environment scope
- **Fixed**: Preserved full variable names including album_id to prevent conflicts
- Maintained backward compatibility for existing repository variables

**Result**: Proper state isolation between environments, preventing cross-account contamination while maintaining album-specific tracking within each environment.

## Commit Message Convention
Always use these prefixes for commit messages (capitalized for visibility):
- **PLANNING** | For initial plans, PRDs, to dos
- **UPDATE** | When adding functionality
- **FIXING** | For intermediate fixes  
- **FIXED** | When fixing is complete
- **SECURITY** | For security fixes
- **TESTING** | For testing procedures

Format: `[PREFIX] | [Description]`
Example: `UPDATE | Add image retry mechanism for Flickr URL validation`

### Co-Author Information
For all commits, include both co-authors:
- **Claude**: `Claude <noreply@anthropic.com>`
- **Walter**: `walter@webmemo.ch <walter@webmemo.ch>`