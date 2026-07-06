# Runbook — Activate the Reisememo Account (WP8)

**Prerequisites:** WP6 merged (config-driven content path), WP7 merged and proven (token refresh). This runbook is finalized as part of WP8 — the developer must verify every env-var name below against the post-WP5/WP6 code (`config.py`, `account_config.py`) before marking WP8 done.

## 1. GitHub environment: `secondary-account`

The secondary account is isolated via the `secondary-account` GitHub environment; the code reads the **same unsuffixed variable names** as primary, resolved per-environment. Checklist of environment secrets/vars:

| Name | Value for reisememo | Notes |
|---|---|---|
| `FLICKR_ALBUM_ID` | Reisememo's Flickr album | 1-based position tracking starts fresh per album |
| `INSTAGRAM_ACCESS_TOKEN` | `IGAA...` long-lived token for the Reisememo IG account | Already IGAA; refresh workflow rotates it |
| `INSTAGRAM_ACCOUNT_ID` | Reisememo IG account id (from `me?fields=id,username` on `graph.instagram.com`) | |
| `FACEBOOK_PAGE_ID` / `FACEBOOK_PAGE_ACCESS_TOKEN` | Reisememo Facebook Page (optional) | Omit both to disable FB cross-posting for this account |
| `THREADS_USER_ID` / `THREADS_ACCESS_TOKEN` | Reisememo Threads account (optional) | Omit to disable Threads cross-posting |
| `WORDPRESS_USERNAME` / `WORDPRESS_APP_PASSWORD` | reisememo.ch WP credentials | For authenticated REST access |
| `ANTHROPIC_API_KEY`, Flickr keys, SMTP settings, `GITHUB_TOKEN`-equivalent | Same as primary (repo-level or duplicated per environment) | Verify which are repo-level vs environment-level today |

**Repo-level (not environment) variables** for account identity — verify names post-WP6:

| Name | Value |
|---|---|
| `SECONDARY_ACCOUNT_ID` | `reisememo` (default — usually no need to set) |
| Secondary display name / language / caption style / signature / blog domains vars | German, reisememo.ch — see `account_config.py` env names |
| `SECONDARY_WP_AUTH_KEY` (WP6, if the reisememo WP plugin uses a different key) | Auth key configured in the WP plugin on reisememo.ch |

## 2. WordPress side (reisememo.ch)

- Install/activate the content-API plugin (repo ships `travelmemo-content-api.php`; WP6 makes the namespace/auth key configurable — install with reisememo's values).
- Verify: `GET https://reisememo.ch/wp-json/<namespace>/extract/?slug=<known-post-slug>&auth_key=<key>` returns content.
- Fallbacks (standard WP REST, direct scraping) work without the plugin, at lower caption quality.

## 3. Smoke procedure

1. Dispatch `secondary-flickr-to-insta.yml` manually with **dry-run**. Verify: photo selected at position 1, caption generated in German with reisememo signature and reisememo.ch blog context, no posting, state record written with `is_dry_run` under `state-data/secondary/album-<id>/` on `automation-state`.
2. Reset dry-run state (`python main.py --account reisememo --reset-dry-runs` or equivalent) if position tracking should restart.
3. Dispatch a real run. Verify the post on Instagram (and Threads/FB if configured).
4. Check `python main.py --account reisememo --stats` output.

## 4. Enable the schedules

- Uncomment the `schedule:` cron blocks in `.github/workflows/secondary-flickr-to-insta.yml` and (if Threads is used) `secondary-threads-delayed.yml`.
- Pick cron times that do not collide with the primary account's runs (avoid simultaneous state-branch writers as a general hygiene measure, even though accounts write different paths).

## 5. Album-completion behavior

When the album completes, `main.py` writes `album_complete.marker` and the workflow **disables itself** via `gh workflow disable` and sends a completion email. Starting the next album = set the new `FLICKR_ALBUM_ID` in the environment and re-enable the workflow.
