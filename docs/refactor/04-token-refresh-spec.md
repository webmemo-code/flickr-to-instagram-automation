# WP7 Spec — Automated Token Refresh

## Why

Long-lived Instagram tokens expire after **60 days**. Today, renewal is fully manual (calendar-reminder tip in `INSTAGRAM_AUTH_GUIDE.md`); an expired token surfaces only as error 190 in a failed posting run. This is the most likely cause of silent production breakage.

Only **IGAA** tokens (Instagram Login API, `graph.instagram.com`) support clean programmatic refresh. Legacy **EAA** tokens do not — which is why Travelmemo migrates to IGAA first (see [runbooks/eaa-to-igaa-migration.md](runbooks/eaa-to-igaa-migration.md)); the code needs no change for that swap (`config.py:_detect_graph_api_domain()` routes by prefix).

## New module: `token_refresh.py`

Small, single-purpose, fully unit-testable offline (~150 lines).

### `refresh_igaa_token(token: str) -> RefreshResult`
- Calls `GET https://graph.instagram.com/refresh_access_token?grant_type=ig_refresh_token&access_token=<token>`.
- Returns dataclass `RefreshResult(access_token, expires_in_seconds)`.
- Constraint: a token is refreshable once it is **at least 24 hours old** and not yet expired.

### Guard: refuse non-IGAA tokens
- If the token does not start with `IGAA`/`IGA`: raise with an actionable message ("token is not an Instagram Login (IGAA) token; see eaa-to-igaa-migration runbook") and make **zero** HTTP calls. Never fall back to a `graph.facebook.com` exchange.

### `update_github_secret(secret_name: str, env_name: str, value: str) -> None`
- Shells out: `gh secret set <NAME> --env <ENV> --body -` with the value passed via **stdin only** — never argv (visible in process lists), never logged.

### Failure handling
- Any failure (HTTP error, unexpected payload, `gh` non-zero): send an alert via the consolidated email path (WP4's `email_notifier`) and exit **non-zero** so the workflow run shows red.

### Logging rules
- Token values must never appear in any log record at any level. Log lengths/prefixes at most (e.g. `IGAA…(len=183)`). Enforced by `test_token_value_never_logged`.

### Threads tokens (investigate during implementation)
- Threads long-lived tokens follow the same 60-day pattern; refresh is expected at `GET https://graph.threads.net/refresh_access_token?grant_type=th_refresh_token`. **Confirm against current Meta docs**; if confirmed, refresh `THREADS_ACCESS_TOKEN` in the same run (scaffolded as xfail `test_threads_token_refresh`). If not confirmed, document manual Threads renewal in the ops runbook and close the xfail with a skip + reason.
- `FACEBOOK_PAGE_ACCESS_TOKEN`: Page tokens obtained from a never-expiring user token do not expire; verify Walter's is long-lived, otherwise document manual renewal. Out of automation scope either way.

## New workflow: `.github/workflows/token-refresh.yml`

- **Triggers:** `schedule` weekly cron + `workflow_dispatch` (with an `environment` input for targeted manual runs).
- **Cadence rationale:** tokens live 60 days and are refreshable after 24 h → weekly gives ~8 refresh opportunities per expiry window; any single failure alerts with ~7 weeks of margin.
- **Matrix** over environments: `primary-account`, `secondary-account`. Each job runs with `environment: ${{ matrix.environment }}` so it reads that environment's `INSTAGRAM_ACCESS_TOKEN` (and Threads token if implemented).
- **Secret write-back:** the default `GITHUB_TOKEN` **cannot** write secrets. Requires a fine-grained PAT stored as repo secret `GH_PAT_SECRETS_ADMIN`:
  - Scope: this repository only.
  - Permissions: **Secrets: read/write**, **Environments: read**.
  - Exposed to the job as `GH_TOKEN` env for the `gh` CLI.
- Secrets are **environment-scoped**, so write-back must pass `--env <environment-name>`.
- On failure: the Python module already emails; the workflow additionally surfaces `::error` so the run is visibly red.

## Rollout order (strict)

1. Merge WP7 code + workflow (after WP4).
2. `workflow_dispatch` the refresh for **reisememo** (already IGAA). Must succeed end-to-end, including secret write-back and a subsequent posting run using the rotated token.
3. Only then execute the Travelmemo EAA→IGAA migration runbook.
4. Keep the old EAA token valid (do not revoke) for ~1 week as rollback.

## Acceptance criteria

See WP7 in [01-work-packages.md](01-work-packages.md) and the scaffolded `test_suite/test_token_refresh.py`. Key non-negotiables: non-IGAA refusal with zero HTTP calls; stdin-only secret delivery; no token in logs; alert + non-zero exit on any failure.
