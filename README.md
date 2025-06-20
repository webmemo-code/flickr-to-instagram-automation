# Flickr to Instagram Automation

Automated social media posting system that posts one photo per day from a specific **Flickr album** to **Instagram** with **AI-generated captions** using GitHub Actions and OpenAI GPT Vision.

**Instagram's API** requires source photos to be published online. I chose my Flickr gallery as the source: https://flickr.com/photos/schaerer/albums/.

The *ID '72177720326826937'* of a **Flickr album** (found in the URL; for example, https://flickr.com/photos/schaerer/albums/72177720326826937) serves as the **source configuration key**.

### The Why - The motivation behind this automation
I take lots of photos that I edit in Adobe Lightroom and publish on my travel blogs, https://travelmemo.com in English and https://reisememo.ch in German.

However, I don't take the time to post them on Instagram. This automation helps me repurpose my photos.

## Features

- 📅 **Daily Posting**: Posts one photo per day until the album is complete
- 🎯 **Single Album Focus**: Processes one specific Flickr album
- 🤖 **AI-Generated Captions**: Uses OpenAI GPT-4 Vision for engaging Instagram captions
- 📊 **Progress Tracking**: Shows completion progress and statistics
- 🔧 **Manual Control**: Run automation manually with different options
- 🛡️ **Smart Stopping**: Automatically stops when all photos are posted
- 📈 **Analytics**: Built-in statistics and monitoring

## Quick Start

### 1. Repository Setup

1. Fork or clone this repository
2. In the file caption_generator.py, adapt the branding to reflect your own brand instead of my Travelmemo brand
3. No other code changes are needed - all configuration is done via environment variables
4. Optional: To change the publishing schedule, edit the workflow file social-media-automation.yml

### 2. Configure Secrets and Variables

Add the following **secrets** to your GitHub repository (`Settings > Secrets and variables > Actions > Repository secrets`):

```
FLICKR_API_KEY=your_flickr_api_key
FLICKR_USER_ID=your_flickr_user_id
INSTAGRAM_ACCESS_TOKEN=your_instagram_access_token
INSTAGRAM_ACCOUNT_ID=your_instagram_business_account_id
OPENAI_API_KEY=your_openai_api_key
```

Add the following **variables** to your GitHub repository (`Settings > Secrets and variables > Actions > Repository variables`):

```
FLICKR_USERNAME=your_flickr_username
FLICKR_ALBUM_ID=your_flickr_album_id
GRAPH_API_VERSION=v18.0 (current Facebook/Instagram API version)
OPENAI_MODEL=gpt-4o-mini (current OpenAI vision model number. The mini version will do just fine at a lower cost)
```

### 3. First Run

1. Go to `Actions` tab in your repository
2. Click on "Flickr to Instagram Automation"
3. Click "Run workflow"
4. Check "Run without posting (dry run)" for testing
5. Click "Run workflow"

## How It Works

The automation follows this simple process:

1. **Daily Schedule**: Runs every day at 9 AM UTC
2. **Check Album**: Fetches all photos from your specified Flickr album
3. **Find Next Photo**: Identifies the next unposted photo
4. **Generate Caption**: Uses GPT-4 Vision to create an engaging caption
5. **Post to Instagram**: Publishes the photo with the generated caption
6. **Track Progress**: Records the post in GitHub Issues
7. **Auto-Complete**: Stops automatically when all photos are posted

## Album Configuration

### Setting Your Album

The system is now fully configurable via GitHub repository variables. No code changes are needed.

Set your Flickr album by updating the repository variables:
- `FLICKR_ALBUM_ID`: Your specific album ID
- `FLICKR_USERNAME`: Your Flickr username

To change albums, simply update the `FLICKR_ALBUM_ID` variable in your GitHub repository settings.

### Finding Your Album ID

Your Flickr album URL looks like:
```
https://flickr.com/photos/[your_username]/albums/72177720326826937
```

The album ID is the number at the end: `72177720326826937`

## API Setup

### Flickr API
1. Visit [Flickr App Garden](https://www.flickr.com/services/apps/create/)
2. Create a new app and get your API key
3. Find your User ID from your Flickr profile URL

### Instagram Graph API
1. Create a Facebook App at [developers.facebook.com](https://developers.facebook.com)
2. Add Instagram Graph API product
3. Get a long-lived access token
4. Connect your Instagram Business account

### OpenAI API
1. Sign up at [platform.openai.com](https://platform.openai.com)
2. Create an API key
3. Ensure you have credits for GPT-4 Vision

## Usage

### Scheduled Automation
- Runs automatically every day at 9 AM UTC
- Posts one photo per day from your album
- Automatically stops when all photos are posted
- No manual intervention required

### Manual Execution

#### GitHub Actions (Manual Trigger)
Use the manual workflow trigger with these options:
- **Dry Run**: Test without posting to Instagram  
- **Show Stats**: Display posting statistics and progress

#### Command Line (Local Testing)
```bash
# Install dependencies
pip install -r requirements.txt

# Post next photo (dry run)
python main.py --dry-run

# Post next photo (live)
python main.py

# Show statistics
python main.py --stats
```

## State Management

The system uses GitHub Issues to track progress:

### Issue Types
- **Posted Photos**: Each posted photo creates an issue with metadata
- **Automation Logs**: Success/failure records for each run
- **Progress Tracking**: Shows completion status

### Issue Labels
- `automated-post`: Photos posted by automation
- `instagram`: Posted to Instagram
- `flickr-album`: From the configured Flickr album
- `posted`: Successfully posted
- `failed`: Failed to post
- `automation-log`: Automation run records

## Monitoring Progress

### View Statistics
Run the workflow with "Show statistics only" checked, or use:
```bash
python main.py --stats
```

This shows:
- Total photos in album
- Photos posted so far
- Photos remaining
- Completion percentage
- Success rate

### Check Individual Posts
View GitHub Issues in your repository to see:
- Each photo that was posted
- Instagram post IDs
- Timestamps
- Any errors that occurred

## Album Completion

When all photos in your album have been posted:

1. 🎉 The automation displays "Album complete!"
2. ⏸️ Scheduled runs automatically skip execution
3. 📊 Statistics show 100% completion
4. 🔄 To start a new album, update the `FLICKR_ALBUM_ID` variable in GitHub repository settings

## Project Structure

```
├── main.py                 # Main automation script
├── config.py              # Configuration management (environment variables)
├── flickr_api.py          # Flickr API integration
├── caption_generator.py   # OpenAI caption generation
├── instagram_api.py       # Instagram posting
├── state_manager.py       # GitHub Issues state management
├── requirements.txt       # Python dependencies
└── .github/
    └── workflows/
        └── social-media-automation.yml  # GitHub Actions workflow
```

### Common Issues

**Album Complete Message**
```
🎉 Album complete! All photos have been posted to Instagram.
```
- This means all photos from your album have been successfully posted
- To start posting from a new album, update the `FLICKR_ALBUM_ID` variable in GitHub repository settings

**Missing Environment Variables**
```
Error: Missing required environment variables
```
- Ensure all secrets are configured in GitHub repository settings
- Check that secret names match exactly (case-sensitive)

**Instagram API Errors**
```
Error: Failed to create media container
```
- Check Instagram access token validity (tokens can expire)
- Verify business account connection
- Review Instagram API rate limits (200 requests/hour)

**OpenAI API Errors**
```
Error: Rate limit exceeded
```
- Check OpenAI account credits and usage limits
- Verify GPT-4 Vision model access
- Consider using GPT-4o-mini for lower costs

**Flickr API Errors**
```
Error: Failed to retrieve photos
```
- Verify Flickr API key and user ID
- Check album visibility settings (must be public or accessible)
- Ensure album ID is correct in your GitHub repository variables

**No Photos Found**
```
Warning: No photos found in the album
```
- Check that the album ID in your GitHub repository variables is correct
- Verify the album exists and contains photos
- Ensure album is public or accessible with your API key

### Debug Mode
Enable debug logging for troubleshooting:

```bash
python main.py --log-level DEBUG --dry-run
```

### Check Album Access
Test your Flickr album access:

```bash
# Check if your album is accessible
curl "https://www.flickr.com/services/rest/?method=flickr.photosets.getPhotos&api_key=YOUR_API_KEY&photoset_id=YOUR_ALBUM_ID&format=json&nojsoncallback=1"
```

## Security

- All API credentials stored as GitHub Secrets
- Environment-specific deployment protection
- Input validation for all external data
- Secure state management via GitHub Issues
- No credentials stored in code

## Support

For issues and questions:

1. **Check Configuration**: Verify your GitHub repository variables and secrets
2. **Test with Dry Run**: Use `--dry-run` flag to test without posting
3. **Review Logs**: Check GitHub Actions logs and artifacts
4. **Statistics**: Use `--stats` to check progress and identify issues
5. **GitHub Issues**: Don't create an issue because I don't have the resources to follow up

Use this repo for free. It comes as is, i.e. without any warranty whatsoever. 
I don't offer support due to limited time.

## Example Workflow

Here's what a typical automation cycle looks like:

1. **Day 1**: Posts photo 1/13 from your album
2. **Day 2**: Posts photo 2/13 from your album  
3. **Day 3**: Posts photo 3/13 from your album
4. ...
5. **Day 13**: Posts photo 13/13 from your album
6. **Day 14**: Shows "Album complete!" and stops

The automation intelligently tracks which photos have been posted and always selects the next unposted photo in the album order.

## Contributing

I'm working on this repo in a very limited capacity. Therefore, I can't review PRs or develop the functionality any further.

## License

This project is licensed under the MIT License.
