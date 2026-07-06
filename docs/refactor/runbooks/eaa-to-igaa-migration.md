# Runbook — Migrate Travelmemo from legacy EAA token to IGAA (Instagram Login API)

**When:** Only after the token-refresh workflow (WP7) has completed at least one successful end-to-end run for reisememo (already IGAA), including secret write-back and a subsequent posting run.

**Why no code change is needed:** `config.py:_detect_graph_api_domain()` selects the Graph domain by token prefix — `IGAA...` → `graph.instagram.com`, otherwise `graph.facebook.com`. All Instagram endpoints used (`/media`, `/media_publish`, account info) exist on both domains. The Facebook Page cross-post (`facebook_api.py`) uses its own separate `FACEBOOK_PAGE_ACCESS_TOKEN` and is unaffected.

## Steps

1. **Generate an IGAA token for the Travelmemo Instagram account** following `INSTAGRAM_AUTH_GUIDE.md`, Flow A (New Instagram Business API):
   - Meta app with the **Instagram API** use case and `instagram_business_content_publish` permission.
   - Add the Travelmemo IG account as an **Instagram Tester** and accept the invite in the IG app.
   - Generate the token (starts `IGAA`), then exchange for the long-lived variant:
     `GET https://graph.instagram.com/access_token?grant_type=ig_exchange_token&client_secret=<APP_SECRET>&access_token=<SHORT_TOKEN>`
2. **Verify the account ID** matches the existing `INSTAGRAM_ACCOUNT_ID` secret:
   `GET https://graph.instagram.com/v23.0/me?fields=id,username&access_token=<NEW_TOKEN>` — use the `id` field. If it differs from the current secret, stop and investigate before proceeding.
3. **Swap the secret:** in the repo's `primary-account` GitHub environment, replace `INSTAGRAM_ACCESS_TOKEN` with the new IGAA token. Do **not** revoke or delete the old EAA token.
4. **Verify with a dry run:** dispatch the primary workflow with dry-run, confirm the log shows requests going to `graph.instagram.com` and the run succeeds.
5. **Verify with a real post:** let the next scheduled run post (or dispatch manually). Confirm the photo appears on Instagram and the Facebook Page cross-post still works.
6. **Confirm refresh coverage:** check that the next weekly `token-refresh.yml` run refreshes the primary token successfully.
7. **Retire rollback after ~1 week:** once several posting runs and one refresh have succeeded, the EAA token may be left to expire naturally.

## Rollback

Restore the previous EAA token as `INSTAGRAM_ACCESS_TOKEN` in the `primary-account` environment. Domain routing reverts automatically on the next run. (This is why the EAA token must not be revoked during the transition window.)

## Failure signatures

- **Error 190 on `graph.instagram.com`:** token expired/invalid or app lacks `instagram_business_content_publish` — regenerate per step 1.
- **Error 190 on `graph.facebook.com` with an IGAA token:** the token was pasted somewhere that still routes to the legacy domain — check that the secret really starts with `IGAA` (no whitespace) and that the run used the updated secret.
- **`(#10) Application does not have permission`:** the IG account is not added/accepted as Instagram Tester, or the app's use case is missing the publish permission.
