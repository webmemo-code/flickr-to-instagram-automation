# TODO

## Facebook Page Cross-posting (Issue #168)

Code is implemented and ready. Waiting on Meta platform configuration (up to 24h).

- [ ] Wait for `pages_manage_posts` permission to become available on Travelmemo Picture Graph API app (773074657981300)
https://developers.facebook.com/apps/773074657981300/app-review/permissions/
- [ ] In Graph API Explorer: add `pages_manage_posts` permission, regenerate token
- [ ] Switch "User or Page" dropdown to the Travelmemo page to get a **Page Access Token**
- [ ] Note the **Page ID** from the `/me/accounts` response
- [ ] Test with an unpublished post: `POST /{page_id}/photos?url=...&message=Test&published=false`
- [ ] Add GitHub Secrets in `primary-account` environment:
  - `FACEBOOK_PAGE_ID` — numeric page ID
  - `FACEBOOK_PAGE_ACCESS_TOKEN` — page access token
- [ ] Push code changes to `main` and run a manual dry-run to verify log output
- [ ] Run a live test (`workflow_dispatch` without dry-run) and verify photo appears on both Instagram and Facebook Page

## Threads.com Cross-posting (Issue #169)

Code is merged on `main` (PR #170). Feature is dormant until `THREADS_USER_ID` + `THREADS_ACCESS_TOKEN` are populated. The delayed Threads workflow runs +8h after each Instagram cron.

### Primary account
- [ ] Obtain a Threads access token (an `IGAA…` token with `threads_basic` + `threads_content_publish` scopes; may be the same token as `INSTAGRAM_ACCESS_TOKEN` if scopes overlap)
- [ ] Obtain the **Threads user ID** via `GET https://graph.threads.net/v1.0/me?access_token=...&fields=id`
- [ ] Add GitHub Secrets in `primary-account` environment:
  - `THREADS_USER_ID` — Threads numeric user ID (different from Instagram account ID)
  - `THREADS_ACCESS_TOKEN` — Threads access token
- [ ] (Optional) Add environment variables in `primary-account`:
  - `THREADS_POST_DELAY_HOURS` — defaults to 8
  - `THREADS_API_VERSION` — defaults to `v1.0`
- [ ] `workflow_dispatch` `primary-threads-delayed.yml` with `dry_run=true` to verify env-var plumbing
- [ ] Wait for the next scheduled run (17:13, 03:17 or 15:21 UTC) and verify one real Threads post lands with `threads_post_id` recorded in `state-data/primary/album-*/posts.json`

### Secondary account (reisememo)
- [ ] After primary is stable for ~48h, repeat the secret/variable steps in `secondary-account`
- [ ] Uncomment the `schedule:` block in [secondary-threads-delayed.yml](.github/workflows/secondary-threads-delayed.yml) with crons offset +8h from the secondary Instagram cron (currently disabled)
- [ ] Enable the workflow via `gh workflow enable secondary-threads-delayed.yml`
