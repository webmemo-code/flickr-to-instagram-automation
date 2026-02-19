# Quickstart: Configure a New Automation

Once the system is fully set up (API keys, Instagram tokens, GitHub secrets), here's all you need to start posting from a new Flickr album.

## 1. Set the Flickr Album ID

Find your album ID from the URL:
```
https://flickr.com/photos/your_username/albums/72177720326826937
                                                 └── this is the ID
```

Go to **Settings > Environments** in your GitHub repository:

| Account | Environment | Variable |
|---------|-------------|----------|
| Primary | `primary-account` | `FLICKR_ALBUM_ID` |
| Secondary | `secondary-account` | `FLICKR_ALBUM_ID` |

Update the `FLICKR_ALBUM_ID` variable with the new album ID.

## 2. Set the Blog Post URL (optional)

In the same environment, update the `BLOG_POST_URL` variable with the corresponding blog post:
```
https://travelmemo.com/your-new-blog-post/
```
This gives the AI caption generator editorial context for richer captions. Leave empty if no blog post exists.

## 3. Re-enable the Workflow

When an album finishes posting, the workflow auto-disables itself to avoid wasted runs. Before a new album can post, you need to re-enable it:

**Via GitHub UI:**
1. Go to **Actions** > select the disabled workflow
2. Click the **"Enable workflow"** button in the banner

**Via CLI:**
```bash
gh workflow enable primary-flickr-to-insta.yml
```

## 4. Adjust the Posting Schedule

Edit the cron schedule in the account workflow file:

| Account | Workflow file | Default schedule |
|---------|--------------|------------------|
| Primary | `.github/workflows/primary-flickr-to-insta.yml` | `13 18 * * *` (18:13 UTC) |
| Secondary | `.github/workflows/secondary-flickr-to-insta.yml` | disabled (uncomment to enable) |

The cron format is `minute hour * * *` (UTC). Examples:
```yaml
- cron: '0 9 * * *'      # Daily at 09:00 UTC
- cron: '30 17 * * *'    # Daily at 17:30 UTC
- cron: '0 12 * * 1-5'   # Weekdays at 12:00 UTC
```

To enable/disable the secondary account schedule, uncomment/comment the `schedule` block in `secondary-flickr-to-insta.yml`.

## 5. Verify with a Dry Run

Before going live, test the new configuration:

**Via GitHub Actions UI:**
1. Go to **Actions** > select the account workflow
2. Click **Run workflow**
3. Check **"Test mode"** (dry run)
4. Click **Run workflow**

**Via command line:**
```bash
python main.py --account primary --dry-run
python main.py --account primary --stats
```

## State Management

No manual state reset is needed. The system creates separate state files per album under `state/{account}/{album_id}/`, so switching to a new album starts fresh automatically.

## Checklist

- [ ] Update `FLICKR_ALBUM_ID` in the GitHub environment
- [ ] Update `BLOG_POST_URL` if a matching blog post exists
- [ ] Re-enable the workflow (it auto-disables when an album completes)
- [ ] Adjust cron schedule if needed
- [ ] Run a dry run to verify the setup
