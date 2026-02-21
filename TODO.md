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
