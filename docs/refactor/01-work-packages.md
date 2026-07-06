# Work Packages

One GitHub issue per WP (label `refactor`). One WP = one PR. Never merge red. Sizes: S ≈ half a day, M ≈ 1–2 days, L ≈ 2–4 days of focused developer-agent work.

Issue links are filled in after `gh issue create` (see the table at the bottom).

---

## WP1 — CI test gate (S)

**Goal:** Every PR runs the offline test suite. The safety net for everything after it. Requires marking the currently-leaking live tests so the gate is green on day one.

**Files:**
- `.github/workflows/tests.yml` (new) — on `pull_request` and `push` to `main`: Python 3.11, install `requirements.txt` + `test_suite/test_requirements.txt`, run `python -m pytest -m "not live_api"` from repo root.
- `pytest.ini` (new, repo root) — `testpaths = test_suite`, `pythonpath = .`, markers (`live_api`, `slow`, `integration`), `--strict-markers`. Delete `test_suite/pytest.ini` (superseded).
- `test_suite/test_integration.py` — module-level `pytestmark = pytest.mark.live_api`.
- `test_suite/test_blog_content_extractor.py` — `live_api` marker on the 3 tests fetching live travelmemo.com.

**Acceptance criteria:**
- `python -m pytest -m "not live_api"` passes locally **with network disabled** (no live Flickr/Anthropic/travelmemo.com calls).
- Workflow fails a PR when a test fails.
- No production module changed.

**Depends on:** — (first).

---

## WP2 — Test-suite hygiene (M)

**Goal:** Shared fixtures via `conftest.py`, retire drift and checked-in artifacts. Foundation for TDD on WP3–WP7.

**Files:**
- `test_suite/conftest.py` — implement the fixture contract in [02-test-scaffold-map.md](02-test-scaffold-map.md) (scaffolded stubs exist).
- `test_suite/test_integration.py` — retire or rewrite the tests treating photos as dicts (production uses `EnrichedPhoto` dataclasses); everything kept stays `live_api`-marked.
- `test_suite/run_tests.py` — delete, or reduce to a thin alias over `pytest -m`.
- `test_suite/test_requirements.txt` — keep `pytest`, `pytest-cov`, `responses` (used by new fixtures); drop `pytest-mock` (unused; tests use `unittest.mock`/`monkeypatch`).
- `test_suite/README.md` — rewrite to match reality (markers, quick vs live runs).
- `.gitignore` — add `__pycache__/`, `.pytest_cache/`; `git rm -r --cached` the checked-in `test_suite/__pycache__` and `test_suite/.pytest_cache`.
- Existing test files — replace copy-pasted fixture blocks (`REQUIRED_ENV`, `_build_config`, `safe_print`, config mocks) with conftest fixtures. Mechanical; no assertion changes.
- Delete `test_multi_account.py` (repo root) — print-only script, no assertions, references an obsolete `_REISEMEMO`-suffixed env scheme. (Listed here rather than WP5 because it lives in test land.)
- Fix the hidden `grapheme` dependency: `test_threads_caption.py::test_truncation_does_not_split_multi_codepoint_emoji` fails when the optional `grapheme` library is absent (verified 2026-07-06). Either add `grapheme` to `test_requirements.txt` + `requirements.txt`, or make the test skip when the library is missing (mirroring the production fallback).

**Acceptance criteria:**
- `pytest -m "not live_api"` green offline; passing-test count not lower than before minus intentionally retired tests (listed in PR description).
- No `__pycache__`/`.pytest_cache` tracked in git.
- No test file redefines a fixture that conftest provides.

**Depends on:** WP1.

---

## WP3 — State-layer safety (L) — highest risk, highest value

**Goal:** State reads that fail must fail loud (never return `[]` → never re-post from photo 1). Reads must not write. Fewer commits per run. **No storage redesign** — `GitFileStorageAdapter` + Contents API + `automation-state` branch stay.

Full spec: [03-state-layer-spec.md](03-state-layer-spec.md). Assign to **Opus 4.8**.

**Files:** `state_manager.py`, `storage_adapter.py`, `main.py` (exit-code wiring), scaffolded `test_suite/test_state_manager.py` + `test_suite/test_storage_adapter.py`.

**Acceptance criteria:**
- Simulated network error / 500 / rate-limit on a state read raises `CriticalStateFailure`; `get_next_photo_to_post` can never observe a spuriously empty posted list.
- 404-on-first-run still bootstraps empty state.
- Read-only paths (`is_album_complete`, `--stats`) produce **zero** storage writes (fake-storage call log).
- One full posting cycle produces ≤ 2 storage writes; failed-position handling unchanged.
- `posts.json`/`metadata.json`/`failed.json` schemas unchanged — existing production files parse without migration.
- Unused `self.github`/`self.repo` removed from `StateManager`; `is_available()` branch check cached per process.

**Depends on:** WP2.

---

## WP4 — Notification consolidation (M)

**Goal:** Exactly one SMTP send path. `email_notifier.py` owns sending; `CriticalFailureNotifier` delegates to it.

**Files:**
- `email_notifier.py` — extract a single `send_email(subject, text_body, html_body=None)` core; SMTP config read once.
- `notification_system.py` — `CriticalFailureNotifier` reuses that core; delete dead `fail_safe_state_operation` and `validate_state_access_or_fail` (a `pass` stub).
- `state_manager.py` — keep the critical-failure wiring pointing at the consolidated notifier.
- Scaffolded `test_suite/test_notifications.py`; fold in/extend `test_suite/test_email_config.py`.

**Acceptance criteria:**
- Exactly one code path constructs `smtplib.SMTP` (grep-verifiable); completion, WP-API-failure, and critical-state-failure emails all route through it.
- Same env var names as today; no secret changes.
- Completion email content unchanged (snapshot assertion); existing email tests pass.

**Depends on:** WP3 (fail-loud semantics settled → alerting must be reliable immediately after).

---

## WP5 — Dead-code removal (M)

**Goal:** Delete verified-dead code and stray files. Pure deletion + green suite.

**Files:**
- `state_models.py` — remove `RetryAttempt`, `retry_history`, `RETRYING` status, computed-never-read `AlbumMetadata` fields. **Constraint:** parsing must still tolerate legacy keys present in production `posts.json` (ignore unknown keys, never require new ones).
- `config.py` — collapse the identical primary/secondary branch (lines 40–50) into one path (`INSTAGRAM_APP_ID` with per-account suffix fallback if desired — it is unused anyway); simplify the pre-environment-scope special-case validation (lines 117–158) to what the workflows actually need.
- `main.py` — delete `instagram_api_url_ok`; use `InstagramAPI.validate_image_url` (canonical behavior).
- Delete: `fix_all_commits.sh`, `resolve_conflicts_script.sh`, `reword_only_script.sh` (one-off git-history maintenance leftovers).
- Scaffolded `test_suite/test_config.py`; extend `test_suite/test_state_manager.py`.

**Acceptance criteria:**
- `pytest -m "not live_api"` green.
- Regression test proves `posts.json` entries containing legacy `retry_history` keys still deserialize.
- `grep -rn "RETRYING\|retry_history\|instagram_api_url_ok\|fail_safe_state_operation" --include="*.py"` matches only test fixture data.
- `Config` behaves identically for primary and secondary env setups (parametrized test).

**Depends on:** WP3, WP4.

---

## WP6 — De-hardcode travelmemo in the content path (M/L)

**Goal:** Endpoint namespace, auth key, User-Agent, fallback domains, and fallback brand signature come from `AccountConfig`/env — so reisememo.ch's WordPress works without code edits. Dedupe, don't rewrite, `blog_content_extractor.py`.

**Files:**
- `account_config.py` — extend `AccountConfig`: `wp_endpoint_namespace` (default `travelmemo-content/v1`), `wp_auth_key` (default `tm-post-retrieval`, env-overridable), `user_agent` (default derived from display name, current literal preserved for primary), keep `blog_domains`/`brand_signature`; give primary explicit values for all of these.
- `custom_endpoint_extractor.py` — namespace + auth key from `AccountConfig` (currently hardcoded at lines 46, 53); dedupe `_extract_url_slug` (line 96) with the copy in `blog_content_extractor.py` — one shared helper (suggested home: `blog_url_resolver.py`).
- `blog_content_extractor.py` — fallback domains (line 462 `['travelmemo.com']`) and the "Primary (TravelMemo)" label (line 540) from `AccountConfig`; replace all 5 hardcoded `'TravelMemo-ContentFetcher/1.0'` User-Agents with the config value.
- `caption_generator.py` — fallback signature (line 231 hardcoded English travelmemo string) from `AccountConfig.brand_signature`; current string remains the primary default.
- `.env.example` — document new optional vars (e.g. `SECONDARY_WP_AUTH_KEY`).
- Scaffolded `test_suite/test_custom_endpoint_extractor.py`; extensions to `test_blog_content_extractor.py` and `test_caption_generator.py`.

**Acceptance criteria:**
- With reisememo env vars set: custom-endpoint URL is `https://reisememo.ch/wp-json/<namespace>/...`, configured auth key + UA on every outbound request, fallback domains `['reisememo.ch']`, German fallback signature — proven by offline unit tests.
- With no new env vars: primary behavior **byte-identical** to today (regression tests on URL, headers, signature — these must pass before the change too).
- `_extract_url_slug` exists exactly once.

**Depends on:** WP2. Parallel-safe with WP3–WP5.

---

## WP7 — Token refresh automation + EAA→IGAA migration (L)

**Goal:** Scheduled workflow refreshes IGAA tokens before the 60-day expiry, writes them back to environment-scoped GitHub secrets, and emails on failure. Travelmemo's EAA→IGAA migration is a manual runbook step (code needs no change — domain routing is automatic).

Full spec: [04-token-refresh-spec.md](04-token-refresh-spec.md). Runbook: [runbooks/eaa-to-igaa-migration.md](runbooks/eaa-to-igaa-migration.md).

**Files:** `token_refresh.py` (new), `.github/workflows/token-refresh.yml` (new), `.env.example`, `README.md`. Scaffolded `test_suite/test_token_refresh.py`.

**Acceptance criteria:**
- All unit tests offline/mocked: refresh success parses new token + expiry; HTTP error → alert email + non-zero exit; non-`IGAA` token → refused with actionable message and **zero** HTTP calls; secret update calls `gh secret set <NAME> --env <env>` with the token via **stdin**; token value never appears in logs (caplog assertion).
- Workflow YAML lints (`actionlint` or `gh workflow view`).
- Manual `workflow_dispatch` run succeeds end-to-end for reisememo (already IGAA) **before** the Travelmemo swap.

**Depends on:** WP4 (alert path).

---

## WP8 — Reisememo activation runbook (S)

**Goal:** Ops document to bring the secondary account fully live. Mostly documentation; minimal code.

**Files:** [runbooks/reisememo-activation.md](runbooks/reisememo-activation.md) (scaffolded — verify against post-WP5/WP6 code and finalize); possibly a `workflow_dispatch` dry-run input if missing.

**Acceptance criteria:** A person or agent can activate reisememo end-to-end following only the runbook; the secrets checklist maps 1:1 to env vars actually read by `config.py`/`account_config.py` after WP5/WP6.

**Depends on:** WP6, WP7.

---

## WP9 — Documentation sync (S)

**Goal:** Docs match code.

**Files:**
- `INSTAGRAM_AUTH_GUIDE.md` — v18.0 → current default (v23.0 in `config.py`); add automated-refresh section pointing at `token-refresh.yml`.
- `.env.example` — v18.0 → v23.0; ensure WP6/WP7 vars documented.
- `README.md` + `CLAUDE.md` — module tables updated (deleted files removed; `token_refresh.py` added); test instructions = `python -m pytest -m "not live_api"`.
- Note deliberately-deferred items (from [99-risks-and-sequencing.md](99-risks-and-sequencing.md)).

**Acceptance criteria:** No doc mentions v18.0; no doc references deleted files; CLAUDE.md module table matches the file listing.

**Depends on:** all prior WPs (last).

---

## Issue links

| WP | GitHub issue |
|----|--------------|
| WP1 | _filled after issue creation_ |
| WP2 | _filled after issue creation_ |
| WP3 | _filled after issue creation_ |
| WP4 | _filled after issue creation_ |
| WP5 | _filled after issue creation_ |
| WP6 | _filled after issue creation_ |
| WP7 | _filled after issue creation_ |
| WP8 | _filled after issue creation_ |
| WP9 | _filled after issue creation_ |
