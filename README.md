# Flickr to Instagram Automation

Automated social media posting system that posts one photo per day from a specific Flickr album to Instagram with AI-generated captions using GitHub Actions.

Instagram's API requires photos to be published online. I chose my Flickr gallery as the source: https://flickr.com/photos/schaerer/albums/.

The ID '72177720326826937' of a Flickr album (found in the URL; for example, https://flickr.com/photos/schaerer/albums/72177720326826937) serves as the source configuration key.

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
2. Edit `config.py` to set your Flickr album ID:

```python
@property
def flickr_album_id(self) -> str:
    return '72177720326826937'  # Your album ID here

@property  
def album_name(self) -> str:
    return 'Your Album Name'   # Your album name here
```

### 2. Configure Secrets

Add the following secrets to your GitHub repository (`Settings > Secrets and variables > Actions`):

```
FLICKR_API_KEY=your_flickr_api_key
FLICKR_USER_ID=your_flickr_user_id
INSTAGRAM_ACCESS_TOKEN=your_instagram_access_token
INSTAGRAM_ACCOUNT_ID=your_instagram_business_account_id
OPENAI_API_KEY=your_openai_api_key
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

Edit the `config.py` file to specify your Flickr album:

```python
@property
def flickr_album_id(self) -> str:
    """Get the Flickr album ID to process."""
    return '72177720326826937'  # Replace with your album ID

@property
def album_name(self) -> str:
    """Get the album name for logging and state management."""
    return 'Istrien'  # Replace with your album name
```

### Finding Your Album ID

Your Flickr album URL looks like:
```
https://flickr.com/photos/schaerer/albums/72177720326826937
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
4. 🔄 To start a new album, update the `config.py` file

## Project Structure

```
├── main.py                 # Main automation script
├── config.py              # Album configuration (EDIT THIS)
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
- To start posting from a new album, edit `config.py` with a new album ID

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
- Ensure album ID is correct in `config.py`

**No Photos Found**
```
Warning: No photos found in the album
```
- Check that the album ID in `config.py` is correct
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

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with `--dry-run` flag
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:

1. **Check Album Configuration**: Verify your `config.py` settings
2. **Test with Dry Run**: Use `--dry-run` flag to test without posting
3. **Review Logs**: Check GitHub Actions logs and artifacts
4. **Statistics**: Use `--stats` to check progress and identify issues
5. **GitHub Issues**: Create an issue with detailed error information

## Example Workflow

Here's what a typical automation cycle looks like:

1. **Day 1**: Posts photo 1/13 from your album
2. **Day 2**: Posts photo 2/13 from your album  
3. **Day 3**: Posts photo 3/13 from your album
4. ...
5. **Day 13**: Posts photo 13/13 from your album
6. **Day 14**: Shows "Album complete!" and stops

The automation intelligently tracks which photos have been posted and always selects the next unposted photo in the album order.# Flickr to Instagram Automation

Automated social media posting system that transfers photos from Flickr albums to Instagram with AI-generated captions using GitHub Actions.

## Features

- 🔄 **Automated Daily Posting**: Schedule posts from multiple Flickr albums
- 🤖 **AI-Generated Captions**: Uses OpenAI GPT-4 Vision for engaging Instagram captions
- 📊 **State Management**: Tracks posted content using GitHub Issues
- 🔧 **Manual Control**: Run automation manually with different options
- 🛡️ **Error Handling**: Robust retry logic and error recovery
- 📈 **Analytics**: Built-in statistics and monitoring

## Quick Start

### 1. Repository Setup

1. Fork or clone this repository
2. Ensure you have the necessary API credentials (see setup section below)

### 2. Configure Secrets

Add the following secrets to your GitHub repository (`Settings > Secrets and variables > Actions`):

```
FLICKR_API_KEY=your_flickr_api_key
FLICKR_USER_ID=your_flickr_user_id
INSTAGRAM_ACCESS_TOKEN=your_instagram_access_token
INSTAGRAM_ACCOUNT_ID=your_instagram_business_account_id
OPENAI_API_KEY=your_openai_api_key
```

### 3. Manual Trigger

1. Go to `Actions` tab in your repository
2. Click on "Flickr to Instagram Automation"
3. Click "Run workflow"
4. Select your destination and options
5. Click "Run workflow"

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

## Project Structure

```
├── main.py                 # Main automation script
├── config.py              # Configuration management
├── flickr_api.py          # Flickr API integration
├── caption_generator.py   # OpenAI caption generation
├── instagram_api.py       # Instagram posting
├── state_manager.py       # GitHub Issues state management
├── requirements.txt       # Python dependencies
└── .github/
    └── workflows/
        └── social-media-automation.yml  # GitHub Actions workflow
```

## Usage

### Scheduled Automation
The workflow runs daily at 9 AM UTC, automatically rotating through destinations:
- Day 1: Istrien
- Day 2: Madeira  
- Day 3: Sardinia
- Day 4: Seerenbachfaelle
- (Repeats)

### Manual Execution

#### Command Line (Local)
```bash
# Install dependencies
pip install -r requirements.txt

# Post next photo from Istrien
python main.py --destination Istrien

# Dry run (don't actually post)
python main.py --destination Madeira --dry-run

# Show statistics
python main.py --stats --destination Sardinia
```

#### GitHub Actions
Use the manual workflow trigger with these options:
- **Destination**: Choose which Flickr album to process
- **Dry Run**: Test without posting to Instagram
- **Show Stats**: Display posting statistics

## Configuration

### Destinations
Edit `config.py` to add new destinations:

```python
def get_flickr_album_id(self, destination: str) -> Optional[str]:
    flickr_albums = {
        'NewDestination': 'your_flickr_album_id',
        # ... existing destinations
    }
    return flickr_albums.get(destination)
```

### Scheduling
Modify the cron schedule in `.github/workflows/social-media-automation.yml`:

```yaml
schedule:
  - cron: '0 9 * * *'  # Daily at 9 AM UTC
  - cron: '0 17 * * 1-5'  # Weekdays at 5 PM UTC
```

## State Management

The system uses GitHub Issues to track:
- **Posted Photos**: Each posted photo creates an issue with metadata
- **Automation Logs**: Success/failure records for each run
- **Statistics**: Success rates and posting history

### Issue Labels
- `automated-post`: Photos posted by automation
- `instagram`: Posted to Instagram
- `destination-{name}`: Specific destination album
- `posted`: Successfully posted
- `failed`: Failed to post
- `automation-log`: Automation run records

## Monitoring and Debugging

### View Logs
1. Go to Actions tab
2. Click on a workflow run
3. Download the "automation-logs" artifact

### Check Statistics
Run with `--stats` flag or use the "Show Stats" option in manual trigger.

### Debug Failed Posts
Check GitHub Issues with `failed` label for error details.

## Error Handling

The system includes comprehensive error handling:

- **API Rate Limits**: Exponential backoff and retry logic
- **Network Failures**: Automatic retries with delays
- **Invalid Images**: URL validation before posting
- **State Conflicts**: Prevents duplicate posts
- **Scheduled Retry**: Failed scheduled runs retry after 5 minutes

## Security

- All API credentials stored as GitHub Secrets
- Environment-specific deployment protection
- Input validation for all external data
- Secure state management via GitHub Issues

## Customization

### Caption Generation
Modify the prompt in `caption_generator.py`:

```python
prompt = ("Your custom prompt for GPT-4 Vision...")
```

### Post Frequency
Adjust automation frequency by:
1. Changing cron schedule
2. Modifying destination rotation logic
3. Adding custom scheduling logic

### Additional Platforms
Extend the system by:
1. Adding new API integrations (Twitter, TikTok, etc.)
2. Creating platform-specific modules
3. Updating workflow to support multiple targets

## Troubleshooting

### Common Issues

**Missing Environment Variables**
```
Error: Missing required environment variables
```
- Ensure all secrets are configured in GitHub repository settings

**Instagram API Errors**
```
Error: Failed to create media container
```
- Check Instagram access token validity
- Verify business account connection
- Review Instagram API rate limits (200 requests/hour)

**OpenAI API Errors**
```
Error: Rate limit exceeded
```
- Check OpenAI account credits
- Review GPT-4 Vision usage limits
- Consider adjusting retry logic

**Flickr API Errors**
```
Error: Failed to retrieve photos
```
- Verify Flickr API key and user ID
- Check album visibility settings
- Ensure album IDs are correct

### Debug Mode
Enable debug logging:

```bash
python main.py --destination Istrien --log-level DEBUG
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request (Mind you, I might be slow to reply due to limited time.)

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review GitHub Issues for similar problems
3. Create a new issue with detailed information