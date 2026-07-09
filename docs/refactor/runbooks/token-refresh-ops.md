# Runbook — Token Refresh Operations

## Normal operation

`.github/workflows/token-refresh.yml` runs weekly (plus `workflow_dispatch`), matrixed over the `primary-account` and `secondary-account` environments. Each job:

1. Reads the environment's `INSTAGRAM_ACCESS_TOKEN` and, if configured, `THREADS_ACCESS_TOKEN`.
2. Calls `graph.instagram.com/refresh_access_token?grant_type=ig_refresh_token`, then (if a Threads token is present) `graph.threads.net/refresh_access_token?grant_type=th_refresh_token`.
3. Writes each rotated token back with `gh secret set <NAME> --env <environment> --body -` (stdin), authenticated via the `GH_PAT_SECRETS_ADMIN` fine-grained PAT. An environment with no Threads token configured is skipped for that part without error.

Tokens live 60 days and are refreshable after 24 hours, so a weekly cadence leaves ~7 weeks of margin after any single failure.

`GH_PAT_SECRETS_ADMIN` itself is a fine-grained PAT (this repo only; Secrets: read/write, Environments: read) set with a **1-year expiration** — a deliberate choice for periodic credential rotation, not a GitHub-imposed maximum (the creation form also offers "No expiration"). Rotate it before it expires; an expired PAT surfaces as case 3 below.

## When the refresh workflow alerts (email or red run)

1. **Read the failure email / job log.** The token value itself is never logged; look for the HTTP status or `gh` error.
2. **HTTP 400/190 from the refresh endpoint** — token already expired or invalidated (password change, security event):
   - Generate a fresh IGAA token manually (Flow A in `INSTAGRAM_AUTH_GUIDE.md`), set it in the affected environment, re-dispatch the refresh workflow to confirm.
3. **`gh secret set` failure** — usually the PAT:
   - `GH_PAT_SECRETS_ADMIN` expired (1-year rotation policy) or lost permissions. Mint a new fine-grained PAT (this repo only; Secrets: read/write, Environments: read; 1-year expiration), update the repo secret, re-dispatch.
4. **Refresh succeeded but write-back failed** — the new token is live at Meta but GitHub still holds the old one. The old one remains valid until its original expiry, so posting keeps working; still fix the PAT and re-dispatch promptly (the next refresh call must use the newest token).
5. **Non-IGAA token refused** — someone set an `EAA...` token in that environment. Follow [eaa-to-igaa-migration.md](eaa-to-igaa-migration.md).

## General alert triage (post-WP3 fail-loud)

A posting run that fails with `CriticalStateFailure` means a **state read/write failed** (GitHub API blip, rate limit, permissions). It does **not** mean state is corrupted, and it requires **no manual state repair** — the run aborted precisely so nothing wrong was posted. Action: re-run the workflow, or let the next scheduled run proceed. Investigate only if it recurs across multiple runs (check GitHub status, token/PAT permissions).

## Manual renewal fallback (if automation is down)

- Instagram (IGAA): `GET https://graph.instagram.com/refresh_access_token?grant_type=ig_refresh_token&access_token=<CURRENT>` → set the returned token as the environment secret.
- Threads: `GET https://graph.threads.net/refresh_access_token?grant_type=th_refresh_token&access_token=<CURRENT>` → same 24h-minimum-age / 60-day-lifetime contract and response shape as Instagram; set the returned token as `THREADS_ACCESS_TOKEN`. Requires the `threads_basic` permission still granted.
- Facebook Page token: long-lived Page tokens typically do not expire; if posting fails with 190, regenerate via `me/accounts` with a long-lived user token.
