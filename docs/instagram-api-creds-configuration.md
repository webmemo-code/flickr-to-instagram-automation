# Instagram API Credentials Configuration

Step-by-step guide to obtain and configure `INSTAGRAM_ACCESS_TOKEN` and
`INSTAGRAM_ACCOUNT_ID` for an account in this project.

This is the practical, mistake-avoiding walkthrough. For background on the two
API eras and troubleshooting, see [INSTAGRAM_AUTH_GUIDE.md](../INSTAGRAM_AUTH_GUIDE.md).

> **Windows/PowerShell note**: Use `curl.exe` (not the `curl` alias, which is
> `Invoke-WebRequest`) and keep each command on a single line — PowerShell does
> not support bash-style `\` line continuation.

> **API version vs. token**: The Graph API version (`v25.0` in the examples
> below) is **not** tied to the token. A token is version-independent — the same
> `IGAA...` token works whether requests go to `/v23.0/...` or `/v25.0/...`.
> Switching `GRAPH_API_VERSION` (default `v23.0` in `config.py`, override per
> environment) never requires regenerating the token. The examples here use
> `v25.0`; adjust the version segment to match whatever `GRAPH_API_VERSION` you
> run with.

---

## TL;DR — the two mistakes to avoid

1. **Do not use the Graph API Explorer to generate the token.** The Explorer
   issues a legacy **`EAA...`** Facebook *user* token on `graph.facebook.com`.
   This project's new-API accounts need an **`IGAA...`** token, generated from
   the app's **Instagram API use case**, that routes to `graph.instagram.com`.
   The code auto-detects the domain from the token prefix
   (`config.py:_detect_graph_api_domain()`), so pasting the wrong token type
   silently routes to the wrong host and fails with error 190.

2. **A `GET /me?fields=id,name` call proves nothing.** That endpoint requires no
   Instagram permission, so it will never satisfy Meta's "0 of 1 API call(s)
   required" testing tracker and it does not verify you can post. Use the
   verification calls in Step 4 instead.

> **You almost certainly do NOT need App Review.** In **Development mode**, the
> app works for accounts holding an Admin / Developer / **Instagram Tester**
> role without App Review. Since you post to your *own* account, add it as a
> tester (Step 2) and skip App Review and the testing tracker entirely. App
> Review / Advanced Access is only needed to act on accounts that do *not* hold
> an app role.

---

## Which flow does this account use?

| Token prefix | API domain | How to generate | Used by |
|---|---|---|---|
| `IGAA...` | `graph.instagram.com` | Instagram API use case (Steps below) | New accounts; the target for all accounts |
| `EAA...`  | `graph.facebook.com`  | Legacy Facebook Login | Primary (`travelmemo`) until migrated — see [eaa-to-igaa-migration.md](refactor/runbooks/eaa-to-igaa-migration.md) |

**These steps produce an `IGAA...` token** (the recommended, current flow). If
you are renewing an existing, still-valid token instead of creating a new one,
skip to [Token Renewal](#token-renewal).

---

## Prerequisites

1. **Instagram Business or Creator account** — personal accounts cannot use the
   API. Convert via Instagram → Settings → Account → Switch to Professional.
2. **Meta app with the Instagram API use case** — in the Meta Developer Portal,
   the app must have the **Instagram API** use case added (not the legacy
   "Instagram Graph API" product). You'll see `instagram_business_*` permission
   names when it's configured correctly.
3. The **`instagram_business_content_publish`** permission added to that use
   case — this is **not** auto-included and is required for posting. Its absence
   causes `(#10) Application does not have permission` at post time even when
   token generation succeeds.

---

## Step 1 — Confirm permissions on the use case

Go to **Use Cases → Instagram API → Permissions and features** and ensure:

- `instagram_business_basic` (auto-included)
- `instagram_business_content_publish` — **add manually; critical for posting**
- `instagram_business_manage_comments` (optional)
- `instagram_business_manage_messages` (optional)

---

## Step 2 — Add the Instagram account as a Tester

This is the step most often missed, and the usual reason an account "never
worked."

1. In the app: **App roles → Roles → Add People → Instagram Tester**, and add
   the target Instagram account (e.g. the reisememo IG account).
2. **Accept the invitation from inside that Instagram account's app**:
   Settings → Apps and websites → Tester invites → Accept.

Until the invite is accepted, token generation for that account will fail.

---

## Step 3 — Generate the token (NOT via Graph API Explorer)

1. Go to **Use Cases → Instagram API → API setup with Facebook login**.
2. Expand **Step 2: Generate access tokens**.
3. Click **Generate token** for the target Instagram account.
4. Authorize the permissions when prompted.
5. Copy the token — it starts with **`IGAA...`**.

The **API setup page issues a long-lived token directly** (60-day expiry) — no
exchange step is needed. Keep this token; it's the value you'll store as
`INSTAGRAM_ACCESS_TOKEN`.

> If the token you copied starts with `EAA...`, you used the wrong tool (the
> Graph API Explorer). Go back and use the **API setup** page as above.

> **Do NOT run an `ig_exchange_token` exchange on this token.** The exchange
> endpoint is only for converting a *short-lived* token to a long-lived one.
> Running it against an already-long-lived token returns
> `error 452 "Session key invalid"` (subcode 2207055). The API setup page
> already gives you the long-lived token, so skip straight to Step 4.

---

## Step 4 — Verify the token and get the account ID

```powershell
curl.exe -s "https://graph.instagram.com/v25.0/me?fields=id,username&access_token={LONG_LIVED_TOKEN}"
```

Response:

```json
{
  "id": "8757938867663187",
  "username": "reisememo"
}
```

- The **`id`** field is your `INSTAGRAM_ACCOUNT_ID` (use `id`, **not** any
  `user_id` field, which is a legacy `17841400...` format).
- Confirm **`username`** is the intended account (e.g. `reisememo`, **not** a
  personal Facebook name). If it's wrong, you generated the token for the wrong
  identity — redo Step 3 for the correct account.

The token from Step 3 is the `{LONG_LIVED_TOKEN}` used in the commands below.

Optional — confirm you can actually publish (this is the meaningful test, and it
registers against the `instagram_business_content_publish` tracker if you ever
do need Advanced Access):

```powershell
curl.exe -X POST "https://graph.instagram.com/v25.0/{INSTAGRAM_ACCOUNT_ID}/media?image_url={PUBLIC_IMAGE_URL}&caption=Test%20post&access_token={LONG_LIVED_TOKEN}"
```

A successful call returns a media container `id`. (Follow with a
`/media_publish` call only if you actually want the test post to go live.)

---

## Step 5 — Store the credentials

### GitHub Actions (production)

Repository **Settings → Environments**, in the environment for this account
(`primary-account` or `secondary-account`):

| Secret | Value |
|---|---|
| `INSTAGRAM_ACCESS_TOKEN` | The long-lived `IGAA...` token from Step 3 |
| `INSTAGRAM_ACCOUNT_ID` | The `id` from Step 4 |

Both accounts read the **same unsuffixed variable names**, resolved per
environment — see [reisememo-activation.md](refactor/runbooks/reisememo-activation.md)
for the full secondary-account checklist.

### Local development

Add to your `.env`:

```
INSTAGRAM_ACCESS_TOKEN=your_long_lived_igaa_token
INSTAGRAM_ACCOUNT_ID=your_instagram_account_id
```

---

## Step 6 — Verify end-to-end with a dry run

Dispatch the account's workflow in dry-run mode and confirm the log shows
requests going to `graph.instagram.com` and the run succeeds:

- Primary: `.github/workflows/primary-flickr-to-insta.yml`
- Secondary: `.github/workflows/secondary-flickr-to-insta.yml`

Locally: `python main.py --account reisememo --dry-run`.

---

## Token Renewal

Long-lived `IGAA...` tokens expire after **60 days**. The weekly
[`token-refresh.yml`](../.github/workflows/token-refresh.yml) workflow rotates
them automatically (Meta requires the token to be **≥ 24h old and not yet
expired** to refresh). To renew manually:

```powershell
curl.exe -s "https://graph.instagram.com/refresh_access_token?grant_type=ig_refresh_token&access_token={CURRENT_LONG_LIVED_TOKEN}"
```

> **Important:** The refresh endpoint only *extends a still-valid token*. It
> **cannot resurrect an expired token** — if a token has fully expired, generate
> a new one from Step 3. (This is why a token that "never worked" or lapsed
> months ago must be regenerated, not refreshed.)

---

## Quick troubleshooting

| Symptom | Cause / fix |
|---|---|
| Token starts with `EAA...` | You used the Graph API Explorer. Use **Use Cases → Instagram API → API setup** (Step 3). |
| Error 190 on `graph.instagram.com` | Token expired/invalid, or app lacks `instagram_business_content_publish`. Regenerate (Step 3). |
| Error 190 on `graph.facebook.com` with an `IGAA` token | Token has stray whitespace or the run used a stale secret — new tokens only work on `graph.instagram.com`. |
| `(#10) Application does not have permission` | Account not accepted as Instagram Tester (Step 2), or publish permission missing (Step 1). |
| `username` in Step 4 is a personal name | Token generated for the wrong identity — redo Step 3 for the correct account. |
| Error 452 "Session key invalid" (subcode 2207055) | You ran an `ig_exchange_token` exchange on an already-long-lived token. Don't exchange — the API setup page (Step 3) already returns a long-lived token; use it directly. |

For anything not covered here, see
[INSTAGRAM_AUTH_GUIDE.md](../INSTAGRAM_AUTH_GUIDE.md).
