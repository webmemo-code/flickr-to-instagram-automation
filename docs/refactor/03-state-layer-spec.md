# WP3 Spec — State-Layer Safety

**Assigned model: Opus 4.8.** This is the one genuinely subtle package: changing exception semantics inside a 608-line module with broad `except Exception` blocks, while preserving first-run bootstrap, failed-position retry mechanics, and on-branch data compatibility. The failure mode on either side (silent album restart, or broken bootstrap) is exactly the production-critical behavior this refactor exists to fix.

## Problem statement (verified in code)

- `state_manager.py:63-94 get_instagram_posts()`: a 403/permission error raises `CriticalStateFailure` (correct), but **any other read failure logs and returns `[]`**. `get_next_photo_to_post` then sees an empty posted list and would select **photo 1** — silently restarting a half-posted album. The same catch-and-return-empty pattern repeats across `get_failed_positions`, `get_enhanced_failed_positions`, metadata getters, etc.
- Read paths write: `is_album_complete` (`state_manager.py:290`) and friends rewrite `metadata.json`, so read-only operations produce commits on `automation-state`.
- `StateManager.__init__` (`state_manager.py:40-41`) constructs its own `Github` client + repo that are **never used** (the storage adapter has its own).
- `GitFileStorageAdapter.is_available()` (`storage_adapter.py:241`) performs a live `get_branch` API call on **every** read/write.
- posts/failed/metadata are written as separate files → separate commits; metadata churn multiplies commit count per run.

## Error taxonomy (the core design)

Classify every storage-read outcome into exactly three cases:

| Case | Meaning | Behavior |
|---|---|---|
| **Absent** | File/branch does not exist yet (GitHub Contents API 404 on a fresh album or first-ever run) | Return empty state. This is the ONLY case that may return empty. |
| **Denied/Failed** | 401/403, 5xx, rate-limit, connection error, JSON parse error, any other exception | Raise `CriticalStateFailure` with a message naming the operation and album. No fallback, no empty return. |
| **Success** | Data read | Return parsed data; individual records that fail to parse are logged and skipped (current behavior, keep). |

Implementation notes:
- The distinction must be made **where the HTTP status is known** — in `GitFileStorageAdapter`. Have the adapter raise a dedicated exception (e.g. `StateFileNotFound`) for the 404-absent case, or return a sentinel; string-matching `"403"`/`"404"` in `state_manager.py` (current approach) is fragile — replace it with typed handling. Keep `CriticalStateFailure` (in `notification_system.py`) as the public fail-loud exception so `main.py` wiring stays.
- `main.py` must let `CriticalStateFailure` surface as a **non-zero exit** and trigger the critical-failure alert (existing wiring via `notifier.send_critical_failure_alert` — verify it fires on all newly-raised paths, not just the old 403 one).
- Write failures already surface as errors; ensure they, too, cannot be swallowed into a "success" return.

## Reads must not write

- Remove metadata rewrites from all read paths (`is_album_complete`, stats, next-photo selection). Metadata is updated only as part of a posting/failure/reset operation.
- Acceptance: `fake_storage` write log empty after any read-only CLI path (`--stats`, completion check).

## Write batching

- One successful posting cycle: ≤ 2 storage writes (posts + metadata). Eliminate redundant metadata-only commits.
- **Write order is a compatibility contract:** the delayed-Threads workflow reads the same branch. Preserve the current effective commit point — the posts file is written such that a concurrently-scheduled Threads run never observes a post without its threads-due record. Do not reorder posts-file vs failed-position writes.

## Other removals/fixes in this WP

- Delete `self.github`/`self.repo` from `StateManager` (lines 40-41) and their construction.
- Cache `is_available()`: one `get_branch` per process lifetime (per `GitFileStorageAdapter` instance is fine — one instance per run).
- Optional (may defer to WP5): collapse the abstract `StateStorageAdapter` base into the concrete class, keeping the public method surface identical. Note the `fake_storage` test fixture subclasses the adapter interface — keep it subclassable.

## Hard compatibility contract

- `posts.json`, `metadata.json`, `failed.json` **schemas unchanged**. Old and new code overlap in production during the rollout window: new code may ignore unknown fields but must not require new ones and must not change the written shape.
- `test_existing_posts_json_parses_unchanged` runs against a fixture copied from real production state (including legacy `retry_history` keys).
- Fresh-album bootstrap (`automation-state` branch auto-creation, first 404s) must keep working — covered by `test_first_run_404_returns_empty_state`.

## Operational consequence (intended)

After WP3, a transient GitHub API blip **fails the run** where it previously "succeeded" dangerously. That is the intended trade. A red run with `CriticalStateFailure` needs **no state repair** — just re-run. This is documented in [runbooks/token-refresh-ops.md](runbooks/token-refresh-ops.md) §general-alerts and must be stated in the WP3 PR description. WP4 (reliable alerting) follows immediately for this reason.
