# Travelmemo Content API

A standalone WordPress plugin for blog content extraction that bypasses Cloudflare bot protection.

## Clean Architecture

```
/wp-json/travelmemo-schema/v1/    → Your Schema.org project (unchanged)
/wp-json/travelmemo-content/v1/   → New standalone content API
```

**Why Standalone?**
- ✅ Clean separation from Schema.org project
- ✅ Independent versioning and updates
- ✅ Focused functionality (content extraction only)
- ✅ Easy maintenance and debugging

## API Endpoints

### Content Extraction
```
GET /wp-json/travelmemo-content/v1/extract/{slug}
```

**Parameters:**
- `slug` (required) - Blog post slug
- `auth_key` (optional) - Authentication key: `tm-post-retrieval`

**Example:**
```
https://travelmemo.com/wp-json/travelmemo-content/v1/extract/sardinia-east-coast-beaches?auth_key=tm-post-retrieval
```

**Response:**
```json
{
    "success": true,
    "data": {
        "id": 36956,
        "title": "Sardinia's Eastern Shores...",
        "slug": "sardinia-east-coast-beaches",
        "url": "https://travelmemo.com/italy/sardinia/sardinia-east-coast-beaches",
        "paragraphs": [
            "Eastern Sardinia is known for its picturesque towns...",
            "The beaches between Cala Liberotto and Cala Goloritzé..."
        ],
        "headings": [
            {"level": 2, "text": "Orosei and the Eastern Coast"},
            {"level": 3, "text": "Best Beaches to Visit"}
        ],
        "images": [
            {"src": "https://travelmemo.com/wp-content/...", "alt": "Sardinia beach"},
            {"src": "https://travelmemo.com/wp-content/...", "alt": "Orosei town"}
        ],
        "featured_image": "https://travelmemo.com/wp-content/...",
        "categories": ["Sardinia", "Italy", "Beaches"],
        "tags": ["travel", "mediterranean", "islands"],
        "word_count": 1500,
        "source": "travelmemo_content_api",
        "api_version": "1.0.0"
    }
}
```

### Posts Listing (Optional)
```
GET /wp-json/travelmemo-content/v1/posts?per_page=10
```

## Installation

**Simple Plugin Installation:**
1. Upload `travelmemo-content-api.php` to `/wp-content/plugins/travelmemo-content-api/`
2. Activate "Travelmemo Content API" in WordPress Admin → Plugins
3. Test endpoint: `https://travelmemo.com/wp-json/travelmemo-content/v1/extract/sardinia-east-coast-beaches`

**Verification:**
- Visit: `https://travelmemo.com/wp-json/` (should show the new namespace)
- Test with actual post slug and auth key

## Benefits of Separate Namespace

### ✅ Clean Organization
- **Schema API**: Focused on Schema.org management
- **Content API**: Dedicated to content extraction
- **Independent**: Each API can evolve separately

### ✅ Better Maintenance
- Clear separation of concerns
- Independent versioning
- Easier debugging and updates

### ✅ Cloudflare Bypass
- Uses dedicated API path not recognized as WordPress core
- Custom User-Agent: `TravelMemo-ContentFetcher/1.0`
- No complex authentication headers

## Integration with Automation

Your automation now uses:

1. **Travelmemo Content API** (primary) - `/wp-json/travelmemo-content/v1/extract/{slug}`
2. **Standard WordPress API** (fallback) - `/wp-json/wp/v2/posts?slug={slug}`
3. **Direct Page Scraping** (final fallback) - Full page extraction

## Expected Logs

```
INFO - Attempting custom endpoint extraction for: https://travelmemo.com/...
INFO - Trying custom endpoint for slug: sardinia-east-coast-beaches
INFO - Custom endpoint successful: 21 paragraphs, 1500 words
INFO - Source: travelmemo_content_api
```

## Security Features

- ✅ **Optional Authentication** - Simple key-based auth
- ✅ **Input Validation** - Slug format validation
- ✅ **Permission Checks** - Only published posts
- ✅ **CORS Headers** - Cross-origin request support
- ✅ **Error Handling** - Proper HTTP status codes

## Summary

**One Plugin Solution:**
- **File**: `travelmemo-content-api.php` (standalone plugin)
- **Namespace**: `travelmemo-content/v1`
- **Purpose**: Blog content extraction for automation
- **Independence**: Completely separate from Schema.org project

This focused, standalone plugin provides robust content extraction while keeping your projects cleanly organized! 🚀