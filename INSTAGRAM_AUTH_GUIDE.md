# Instagram Graph API Authentication Guide

How to obtain `INSTAGRAM_ACCESS_TOKEN` and `INSTAGRAM_ACCOUNT_ID` for this project.

## Prerequisites

1. **Instagram Business or Creator account** — Personal accounts cannot use the Graph API. Convert via Instagram Settings > Account > Switch to Professional Account.
2. **Facebook Page linked to the Instagram account** — Go to your Facebook Page Settings > Linked Accounts > Instagram and connect it.
3. **Meta Developer account** — Sign up at [developers.facebook.com](https://developers.facebook.com) if you haven't already.

## Step 1: Create or Configure a Facebook App

If you already have a Facebook App (e.g., from a previous Instagram account setup), you can reuse it. Otherwise:

1. Go to [Meta Developer Portal — My Apps](https://developers.facebook.com/apps/)
2. Click **Create App**
3. Select **Business** as the app type
4. Fill in the app name and contact email
5. Under **Add Products**, find **Instagram Graph API** and click **Set Up**

### Required App Settings

- **App Mode**: The app must be in **Live** mode (not Development) for publishing to work. Go to the app dashboard and toggle from Development to Live.
- **Permissions**: The app needs these permissions approved (for Live mode, some may require App Review):
  - `instagram_basic`
  - `instagram_content_publish`
  - `pages_show_list`
  - `pages_read_engagement`

> **Note**: In Development mode, the app works only for users who have a role on the app (Admin, Developer, Tester). This is fine for personal use.

## Step 2: Get a Short-Lived Access Token

### Option A: Graph API Explorer (Recommended for first setup)

1. Go to [Graph API Explorer](https://developers.facebook.com/tools/explorer/)
2. In the top-right dropdown, select your **Facebook App**
3. Click **Generate Access Token**
4. In the permissions dialog, select:
   - `instagram_basic`
   - `instagram_content_publish`
   - `pages_show_list`
   - `pages_read_engagement`
5. Click **Generate Access Token** and authorize
6. **Important**: When prompted, select the **Facebook Page** that is linked to your target Instagram account
7. Copy the token — this is your **short-lived token** (valid ~1 hour)

### Option B: Manual OAuth Flow

Construct this URL in your browser (replace placeholders):

```
https://www.facebook.com/v21.0/dialog/oauth?client_id={APP_ID}&redirect_uri=https://localhost/&scope=instagram_basic,instagram_content_publish,pages_show_list,pages_read_engagement&response_type=code
```

After authorizing, you'll be redirected to `https://localhost/?code={CODE}`. Extract the code and exchange it:

```bash
curl -X GET "https://graph.facebook.com/v21.0/oauth/access_token?\
client_id={APP_ID}&\
redirect_uri=https://localhost/&\
client_secret={APP_SECRET}&\
code={CODE}"
```

This returns a short-lived token.

## Step 3: Exchange for a Long-Lived Access Token

The short-lived token expires in ~1 hour. Exchange it for a long-lived token (~60 days):

```bash
curl -X GET "https://graph.facebook.com/v21.0/oauth/access_token?\
grant_type=fb_exchange_token&\
client_id={APP_ID}&\
client_secret={APP_SECRET}&\
fb_exchange_token={SHORT_LIVED_TOKEN}"
```

Response:
```json
{
  "access_token": "EAAG...long-lived-token...",
  "token_type": "bearer",
  "expires_in": 5184000
}
```

Save this **long-lived token** — this is your `INSTAGRAM_ACCESS_TOKEN`.

### Where to find App ID and App Secret

- Go to [Meta Developer Portal — My Apps](https://developers.facebook.com/apps/)
- Select your app
- Go to **Settings > Basic**
- **App ID** is shown at the top
- **App Secret** — click "Show" to reveal it

## Step 4: Get the Instagram Account ID

### 4a. Get your Facebook Page ID

Using your long-lived token:

```bash
curl -X GET "https://graph.facebook.com/v21.0/me/accounts?\
access_token={LONG_LIVED_TOKEN}"
```

Response includes your Pages. Find the one linked to your Instagram account and note its `id`.

### 4b. Get the Instagram Business Account ID

```bash
curl -X GET "https://graph.facebook.com/v21.0/{PAGE_ID}?\
fields=instagram_business_account&\
access_token={LONG_LIVED_TOKEN}"
```

Response:
```json
{
  "instagram_business_account": {
    "id": "17841400123456789"
  },
  "id": "your-page-id"
}
```

The `instagram_business_account.id` is your `INSTAGRAM_ACCOUNT_ID`.

## Step 5: Verify the Setup

Test that your token and account ID work:

```bash
# Check account info
curl -X GET "https://graph.facebook.com/v21.0/{INSTAGRAM_ACCOUNT_ID}?\
fields=id,username,name,profile_picture_url&\
access_token={LONG_LIVED_TOKEN}"
```

You should see your Instagram username in the response.

## Step 6: Store the Credentials

### For GitHub Actions (production)

Go to your repository **Settings > Environments** and add/update secrets:

| Environment | Secret | Value |
|---|---|---|
| `primary-account` | `INSTAGRAM_ACCESS_TOKEN` | Long-lived token for primary account |
| `primary-account` | `INSTAGRAM_ACCOUNT_ID` | Instagram account ID for primary account |
| `secondary-account` | `INSTAGRAM_ACCESS_TOKEN` | Long-lived token for secondary account |
| `secondary-account` | `INSTAGRAM_ACCOUNT_ID` | Instagram account ID for secondary account |

### For local development

Add to your `.env` file:

```
INSTAGRAM_ACCESS_TOKEN=your_long_lived_token
INSTAGRAM_ACCOUNT_ID=your_instagram_account_id
```

## Token Types and API Domains

There are two token formats depending on how the app was set up:

| Token prefix | API Domain | Era |
|---|---|---|
| `EAA...` | `https://graph.facebook.com/` | Legacy Facebook Login flow |
| `IGAA...` | `https://graph.instagram.com/` | New Instagram Business API (2024+) |

The code **auto-detects** the correct API domain based on the token prefix (see `_detect_graph_api_domain()` in [config.py](config.py)). No manual configuration is needed — just set the token and it works.

## Token Renewal

Long-lived tokens expire after **60 days**. The renewal method depends on the token type.

### For `IGAA...` tokens (new Instagram Business API)

```bash
curl -s "https://graph.instagram.com/refresh_access_token?\
grant_type=ig_refresh_token&\
access_token={CURRENT_LONG_LIVED_TOKEN}"
```

### For `EAA...` tokens (legacy Facebook Login flow)

```bash
curl -X GET "https://graph.facebook.com/v21.0/oauth/access_token?\
grant_type=fb_exchange_token&\
client_id={APP_ID}&\
client_secret={APP_SECRET}&\
fb_exchange_token={CURRENT_LONG_LIVED_TOKEN}"
```

Both return a new long-lived token. Update the token in GitHub Secrets and/or your `.env` file.

> **Tip**: Set a calendar reminder for every 50 days to renew the token before it expires.

## Troubleshooting

### Error 190: Invalid OAuth Token
The token has expired or been revoked. Generate a new one following Steps 2–3.

### Error 10: No Page linked
The Instagram account is not connected to a Facebook Page, or the token doesn't have permission for that Page. Check Step 2 — make sure you selected the correct Page when authorizing.

### Error 200: Permission denied
The app doesn't have the required permissions. Check that `instagram_content_publish` is granted. For apps in Live mode, this permission may require App Review.

### "instagram_business_account" field is empty
The Instagram account is not a Business or Creator account, or it's not linked to the Facebook Page. Check the Prerequisites.

### Token works in Explorer but not in code
The Graph API Explorer generates tokens scoped to your user. Make sure you selected the correct Page and Instagram account during authorization. Also verify the API version matches — this project defaults to `v18.0` (configurable via `GRAPH_API_VERSION`).

### Error 190 with `IGAA...` token on `graph.facebook.com`
New Instagram Business API tokens (`IGAA...` prefix) only work with `graph.instagram.com`, not `graph.facebook.com`. The code auto-detects this. If you see this error, ensure you're running the latest version of `config.py`.

## API Version Notes

- This project defaults to Graph API **v18.0** (set in [config.py](config.py))
- Can be overridden via `GRAPH_API_VERSION` environment variable
- Meta deprecates API versions ~2 years after release — check [Meta API Changelog](https://developers.facebook.com/docs/graph-api/changelog) for current versions
- The `curl` examples in this guide use `v21.0` — adjust to match your configured version
- Both `graph.facebook.com` and `graph.instagram.com` support the same version numbers
