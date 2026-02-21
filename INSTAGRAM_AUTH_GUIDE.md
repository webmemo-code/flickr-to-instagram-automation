# Instagram Graph API Authentication Guide

How to obtain `INSTAGRAM_ACCESS_TOKEN` and `INSTAGRAM_ACCOUNT_ID` for this project.

There are two authentication flows depending on when the Facebook App was created. Meta migrated to a new Instagram Business API in 2024. Both flows are documented below.

## Prerequisites

1. **Instagram Business or Creator account** — Personal accounts cannot use the Graph API. Convert via Instagram Settings > Account > Switch to Professional Account.
2. **Facebook Page linked to the Instagram account** — Go to your Facebook Page Settings > Linked Accounts > Instagram and connect it.
3. **Meta Developer account** — Sign up at [developers.facebook.com](https://developers.facebook.com) if you haven't already.

## Token Types and API Domains

| Token prefix | API Domain | Flow | Era |
|---|---|---|---|
| `EAA...` | `https://graph.facebook.com/` | Legacy Facebook Login | Pre-2024 apps |
| `IGAA...` | `https://graph.instagram.com/` | New Instagram Business API | 2024+ apps |

The code **auto-detects** the correct API domain based on the token prefix (see `_detect_graph_api_domain()` in [config.py](config.py)). No manual configuration is needed — just set the token and it works.

---

## Flow A: New Instagram Business API (2024+) — Recommended

This is the flow for newly created Facebook Apps. You'll know you're on this path if the developer portal shows "Instagram API" as a Use Case with `instagram_business_*` permission names.

### A1. Create or Configure a Facebook App

1. Go to [Meta Developer Portal — My Apps](https://developers.facebook.com/apps/)
2. Click **Create App** > select **Business** app type
3. Under **Use Cases**, select **Instagram API**
4. The portal will guide you through "API setup with Facebook login"

### A2. Configure Permissions

Go to **Use Cases > Instagram API > Permissions and features** and ensure these are added:
- `instagram_business_basic` (auto-included)
- `instagram_business_content_publish` (must be added manually — this is critical for posting)
- `instagram_business_manage_comments` (optional)
- `instagram_business_manage_messages` (optional)

### A3. Add Instagram Tester Role

Before generating tokens, the Instagram account must be added as a tester:

1. Go to **App roles > Roles** in the left sidebar
2. Click **Add People** and add the Instagram account as **Instagram Tester**
3. Accept the invitation from the Instagram app: Settings > Website > Apps and Websites > Tester Invitations

### A4. Generate Access Token

1. Go to **Use Cases > Instagram API > API setup with Facebook login**
2. Expand **Step 2: Generate access tokens**
3. Click **Generate token** for the Instagram account
4. Authorize the permissions when prompted
5. Copy the generated token (starts with `IGAA...`)

### A5. Exchange for Long-Lived Token

The token from Step A4 may be short-lived. Exchange it:

```bash
curl -s "https://graph.instagram.com/access_token?\
grant_type=ig_exchange_token&\
client_secret={INSTAGRAM_APP_SECRET}&\
access_token={SHORT_LIVED_TOKEN}"
```

Response:
```json
{
  "access_token": "IGAAbF...long-lived-token...",
  "token_type": "bearer",
  "expires_in": 5184000
}
```

> **Note**: If this returns error 452 ("Session key invalid"), the token is likely already long-lived. Verify by calling the refresh endpoint instead (see Token Renewal below).

The **Instagram App Secret** is found on the Use Cases > API setup page (click "Show" next to the masked secret).

### A6. Get the Instagram Account ID

With your `IGAA...` token:

```bash
curl -s "https://graph.instagram.com/v21.0/me?fields=id,username&\
access_token={LONG_LIVED_TOKEN}"
```

Response:
```json
{
  "id": "8757938867663187",
  "username": "reisememo"
}
```

The `id` field is your `INSTAGRAM_ACCOUNT_ID`.

> **Note**: The response may also include a `user_id` field (legacy format like `17841400...`). Use the `id` field, not `user_id`.

### A7. Complete App Review (if needed)

For the `instagram_business_content_publish` permission, Meta may require:

1. A text description of how the app uses the permission
2. A screen recording demonstrating usage
3. At least 1 test API call (shown as "0 of 1 API call(s) required")
4. Agreement to the data usage policy

Go to **Review > App Review** to submit. The test API call is a content publish to your own account — you can use the dry-run workflow or `curl`:

```bash
curl -X POST "https://graph.instagram.com/v21.0/{INSTAGRAM_ACCOUNT_ID}/media?\
image_url={PUBLIC_IMAGE_URL}&\
caption=Test%20post&\
access_token={TOKEN}"
```

> **Note**: App Review is only needed for Advanced Access (Live mode for non-role-holders). In Development mode, the app works for Admin/Developer/Tester roles without App Review.

---

## Flow B: Legacy Facebook Login (Pre-2024 Apps)

This flow applies to apps created before Meta's 2024 migration. These apps use `EAA...` tokens and `graph.facebook.com`.

### B1. Create or Configure a Facebook App

1. Go to [Meta Developer Portal — My Apps](https://developers.facebook.com/apps/)
2. Click **Create App** > select **Business** app type
3. Under **Add Products**, find **Instagram Graph API** and click **Set Up**

### B2. Get a Short-Lived Access Token

#### Option 1: Graph API Explorer

1. Go to [Graph API Explorer](https://developers.facebook.com/tools/explorer/)
2. Select your **Facebook App** from the dropdown
3. Click **Generate Access Token**
4. Select permissions: `instagram_basic`, `instagram_content_publish`, `pages_show_list`, `pages_read_engagement`
5. When prompted, select the **Facebook Page** linked to your target Instagram account
6. Copy the token (starts with `EAA...`, valid ~1 hour)

#### Option 2: Manual OAuth Flow

```
https://www.facebook.com/v21.0/dialog/oauth?client_id={APP_ID}&redirect_uri=https://localhost/&scope=instagram_basic,instagram_content_publish,pages_show_list,pages_read_engagement&response_type=code
```

After authorizing, extract the code from the redirect URL and exchange:

```bash
curl -X GET "https://graph.facebook.com/v21.0/oauth/access_token?\
client_id={APP_ID}&\
redirect_uri=https://localhost/&\
client_secret={APP_SECRET}&\
code={CODE}"
```

### B3. Exchange for Long-Lived Token

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

### B4. Get the Instagram Account ID

```bash
# Get your Facebook Page ID
curl -X GET "https://graph.facebook.com/v21.0/me/accounts?\
access_token={LONG_LIVED_TOKEN}"

# Get the Instagram Business Account ID from the Page
curl -X GET "https://graph.facebook.com/v21.0/{PAGE_ID}?\
fields=instagram_business_account&\
access_token={LONG_LIVED_TOKEN}"
```

The `instagram_business_account.id` is your `INSTAGRAM_ACCOUNT_ID`.

### Where to find App ID and App Secret (legacy)

- Go to [Meta Developer Portal — My Apps](https://developers.facebook.com/apps/)
- Select your app > **Settings > Basic**
- **App ID** is shown at the top
- **App Secret** — click "Show" to reveal it

---

## Verify the Setup

Test that your token and account ID work (adjust domain based on token type):

```bash
# For IGAA... tokens
curl -s "https://graph.instagram.com/v21.0/{INSTAGRAM_ACCOUNT_ID}?\
fields=id,username,name&access_token={TOKEN}"

# For EAA... tokens
curl -s "https://graph.facebook.com/v21.0/{INSTAGRAM_ACCOUNT_ID}?\
fields=id,username&access_token={TOKEN}"
```

You should see your Instagram username in the response.

## Store the Credentials

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

Both return a new long-lived token with a fresh 60-day expiry. Update the token in GitHub Secrets and/or your `.env` file.

> **Tip**: Set a calendar reminder for every 50 days to renew the token before it expires.

## Troubleshooting

### Error 190: Invalid OAuth Token
The token has expired or been revoked. Generate a new one following the relevant flow above.

### Error 190 with `IGAA...` token on `graph.facebook.com`
New Instagram Business API tokens (`IGAA...` prefix) only work with `graph.instagram.com`, not `graph.facebook.com`. The code auto-detects this. If you see this error, ensure you're running the latest version of `config.py`.

### Error 452: Session key invalid (during token exchange)
The token is likely already long-lived. Try the refresh endpoint instead of the exchange endpoint.

### Error 10: No Page linked
The Instagram account is not connected to a Facebook Page, or the token doesn't have permission for that Page. Re-authorize and make sure you select the correct Page.

### Error 200: Permission denied
The app doesn't have the required permissions. Check that `instagram_business_content_publish` (new) or `instagram_content_publish` (legacy) is granted. For apps in Live mode, this permission may require App Review.

### "instagram_business_account" field is empty
The Instagram account is not a Business or Creator account, or it's not linked to the Facebook Page. Check the Prerequisites.

### Token works in Explorer but not in code
Make sure you selected the correct Page and Instagram account during authorization. Also verify the API version matches — this project defaults to `v18.0` (configurable via `GRAPH_API_VERSION`).

## API Version Notes

- This project defaults to Graph API **v18.0** (set in [config.py](config.py))
- Can be overridden via `GRAPH_API_VERSION` environment variable
- Meta deprecates API versions ~2 years after release — check [Meta API Changelog](https://developers.facebook.com/docs/graph-api/changelog) for current versions
- The `curl` examples in this guide use `v21.0` — adjust to match your configured version
- Both `graph.facebook.com` and `graph.instagram.com` support the same version numbers
