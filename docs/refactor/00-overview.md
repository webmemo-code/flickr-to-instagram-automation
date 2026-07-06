# Targeted Stabilization — Overview

**Status:** Approved by Walter, 2026-07-06. Ready for developer pickup.
**Planner/Reviewer:** Claude (Fable 5). **Executors:** Claude Sonnet 5 (default), Claude Opus 4.8 (WP3, optionally WP7).

## Why this refactor

Goal: adapt the automation to serve Reisememo's Instagram alongside Travelmemo's, on a stabilized foundation. Exploration (2026-07-06) established:

1. **The "deprecated API" migration is a token swap, not a rewrite.** `config.py:_detect_graph_api_domain()` routes by token prefix (`IGAA...` → `graph.instagram.com`, anything else → `graph.facebook.com`). `instagram_api.py` is fully domain-agnostic; the `/media`, `/media_publish`, and account-info endpoints exist on both domains. Reisememo already uses an `IGAA` token. Migrating Travelmemo means replacing one GitHub secret.
2. **The real brittleness is elsewhere:**
   - `state_manager.py` returns `[]` when a state read fails for any non-403 reason → `get_next_photo_to_post` sees "nothing posted" → **risk of re-posting from photo 1**.
   - Metadata is rewritten even on read paths → every run produces unnecessary commits on the `automation-state` branch; `is_available()` does a live API call per storage operation.
   - **No token-refresh automation.** Long-lived tokens expire every 60 days; renewal is manual with no alerting — the most likely cause of silent production breakage.
   - Three overlapping SMTP notification paths; substantial dead code; travelmemo hardcoded in the blog-content path (blocks Reisememo captions).
   - No CI runs the test suite; several "quick" tests secretly hit live APIs.

## Decisions (locked)

| Decision | Choice |
|---|---|
| Scope | **Targeted stabilization** — fix hotspots, keep the architecture. No storage redesign, no blog-extractor rewrite. |
| Cross-posters | **Keep both** Facebook Page (`facebook_api.py`) and Threads (`threads_api.py`). |
| Token refresh | **Automate** via `ig_refresh_token` + scheduled workflow; migrate Travelmemo EAA → IGAA (runbook). |
| Work tracking | GitHub issues (label `refactor`), one per work package; specs in `docs/refactor/`. |

## Method: TDD with scaffolded tests

The planner scaffolded skeleton tests in `test_suite/` that pin the expected behavior (see [02-test-scaffold-map.md](02-test-scaffold-map.md)). Per work package, the developer:

1. Reads the WP issue + linked spec in this directory.
2. Fleshes out the scaffolded tests for that WP (remove `xfail`, implement test bodies per the docstrings; regression tests must pass **before** the change).
3. Implements until green: `python -m pytest -m "not live_api"` from the repo root.
4. Opens one PR per WP. CI (WP1's gate) must be green. PR description lists any intentionally retired tests.
5. The reviewer (Claude) approves or files change-request issues.

## Dependency graph

```
WP1 (CI gate) → WP2 (test hygiene) → WP3 (state safety) → WP4 (notifications) → WP5 (dead code)
                        └────────────→ WP6 (de-hardcode travelmemo, parallel to WP3–WP5)
WP4 + WP6 → WP7 (token refresh) → WP8 (reisememo activation) → WP9 (doc sync)
```

## Definition of done

- All 9 WP issues closed; CI green on `main`.
- A state-read failure can never silently restart an album (WP3 tests prove it).
- One SMTP send path; dead code gone; `pytest -m "not live_api"` runs fully offline.
- Reisememo blog content works without code edits (config-driven endpoint/UA/domains/signature).
- Token refresh workflow has run successfully for reisememo; Travelmemo migrated to IGAA per runbook.
- Docs match code (no v18.0 references, module tables current).

## Out of scope (do not scope-creep — see [99-risks-and-sequencing.md](99-risks-and-sequencing.md))

- `social-automation.yml` inline Python heredocs dedup
- `blog_content_extractor.py` rewrite (only dedupe + config injection)
- Storage backend redesign (Contents API + `automation-state` branch stays)
- Retry-system redesign; Threads duplicate-post window hardening (made visible, not fixed)
- True N-account support (two accounts via GitHub Environments stays)

## Files in this directory

| File | Purpose |
|---|---|
| [01-work-packages.md](01-work-packages.md) | The 9 work packages: goals, files, acceptance criteria, sizes, issue links |
| [02-test-scaffold-map.md](02-test-scaffold-map.md) | conftest fixture contract + per-WP test map, xfail/skip convention |
| [03-state-layer-spec.md](03-state-layer-spec.md) | WP3 deep spec: error taxonomy, write batching, data compatibility |
| [04-token-refresh-spec.md](04-token-refresh-spec.md) | WP7 deep spec: endpoints, cadence, PAT scope, secret handling |
| [99-risks-and-sequencing.md](99-risks-and-sequencing.md) | Risks, sequencing rules, deferred items |
| [runbooks/eaa-to-igaa-migration.md](runbooks/eaa-to-igaa-migration.md) | Manual Travelmemo token swap + verification + rollback |
| [runbooks/reisememo-activation.md](runbooks/reisememo-activation.md) | Bring the secondary account fully live |
| [runbooks/token-refresh-ops.md](runbooks/token-refresh-ops.md) | Operating the refresh workflow / responding to alerts |
