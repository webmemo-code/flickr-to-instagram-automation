# Test Scaffold Map

The scaffolded skeletons in `test_suite/` are the TDD contract. Each skeleton test carries a docstring that **is the behavior spec**. The developer implements the test body per the docstring first, watches it fail (for behavior-change tests), then implements production code until green.

## Conventions

- **Behavior-change tests** (new behavior this refactor introduces) are scaffolded as:
  ```python
  @pytest.mark.xfail(reason="WP<n> not implemented", strict=False)
  def test_...():
      """<behavior spec>"""
      pytest.fail("scaffold: implement per docstring")
  ```
  The developer replaces the body with real assertions and removes the `xfail` marker in the WP's PR.
- **Regression tests** (current behavior that must NOT change, e.g. primary-account defaults, posts.json compatibility) are scaffolded the same way but tagged `REGRESSION` in the docstring: once implemented, they must pass **before** the production change is made, and stay green after.
- Markers: `live_api` (network/live-credential tests — excluded in CI), `slow`, `integration`. CI runs `python -m pytest -m "not live_api"` from the repo root.
- No test file may define a fixture that `conftest.py` provides.

## conftest.py fixture contract (implemented in WP2)

| Fixture | Provides |
|---|---|
| `full_env` | Factory: monkeypatch-sets a complete valid env (Flickr, Instagram, Anthropic, GitHub, SMTP); accepts overrides dict. |
| `igaa_env` / `eaa_env` | `full_env` variants with `INSTAGRAM_ACCESS_TOKEN` prefixed `IGAA...` / `EAA...`. |
| `fake_storage` | In-memory `StateStorageAdapter` subclass recording every read/write call (call log asserts zero-writes-on-read and commit counts). |
| `mock_github_contents` | `responses`-based fake of the GitHub Contents API + `get_branch`: canned 404-first-run, 403, 500, connection-error scenarios for `GitFileStorageAdapter`-level tests. |
| `graph_api` | `responses`-based canned Graph API payloads for both `graph.facebook.com` and `graph.instagram.com`: media create/publish success, **error 190 (expired token)**, rate-limit, `refresh_access_token` success/failure. |
| `sample_photo` / `sample_album` | `EnrichedPhoto` dataclass factories (fixes the dict-vs-dataclass drift that broke `test_integration.py`). |
| `sample_posts_json` | Realistic `posts.json` content **including a legacy entry with `retry_history` keys** (copy shape from real production state). |
| `captured_emails` | Patches the single SMTP send point; yields the list of sent messages. |
| `account_env_reisememo` | `SECONDARY_*` env preset for reisememo.ch (domains, auth key, UA, German signature). |

## Per-WP test map

### WP3 — `test_state_manager.py`, `test_storage_adapter.py` (new, scaffolded)

| Test | Spec |
|---|---|
| `test_read_error_raises_critical_state_failure` | Network error/500 on posts read raises `CriticalStateFailure`, never returns `[]`. |
| `test_read_403_raises_critical_state_failure` | Existing 403 path preserved. |
| `test_first_run_404_returns_empty_state` | Missing state file bootstraps empty state, no exception. |
| `test_get_next_photo_never_restarts_after_read_failure` | 5 photos posted + failing read → raises, never returns photo 1. |
| `test_is_album_complete_performs_no_writes` | Read paths leave `fake_storage` write log empty. |
| `test_stats_performs_no_writes` | `--stats` path performs zero writes. |
| `test_posting_cycle_max_two_writes` | One successful post cycle → ≤ 2 storage writes. |
| `test_state_manager_has_no_direct_github_client` | `StateManager` no longer holds its own `github`/`repo`. |
| `test_is_available_cached_per_process` | N reads → exactly one `get_branch` call. |
| `test_existing_posts_json_parses_unchanged` | REGRESSION: `sample_posts_json` (incl. legacy keys) round-trips. |

### WP4 — `test_notifications.py` (new, scaffolded; absorbs/extends `test_email_config.py`)

| Test | Spec |
|---|---|
| `test_single_smtp_send_path` | Completion, WP-failure, and critical-failure notifications all arrive via `captured_emails` through one sender. |
| `test_critical_failure_notifier_delegates_to_email_notifier` | No second `smtplib.SMTP` construction. |
| `test_completion_email_content_unchanged` | REGRESSION: subject/body snapshot vs current builder output. |
| `test_smtp_config_read_once` | SMTP env read in exactly one place. |

### WP5 — `test_config.py` (new, scaffolded) + `test_state_manager.py` additions

| Test | Spec |
|---|---|
| `test_config_identical_for_primary_and_secondary_env` | Parametrized: same env → same effective config for both account types. |
| `test_legacy_retry_history_ignored_on_load` | Unknown/legacy keys tolerated on load, never re-required. |
| `test_main_uses_instagram_api_validate_image_url` | `main.instagram_api_url_ok` gone; URL validation = `InstagramAPI.validate_image_url` semantics. |

### WP6 — `test_custom_endpoint_extractor.py` (new, scaffolded) + extensions

| Test | Spec |
|---|---|
| `test_endpoint_url_uses_configured_namespace` | reisememo env → `https://reisememo.ch/wp-json/<ns>/extract/...`. |
| `test_auth_key_from_account_config` | Configured key sent, not the hardcoded `tm-post-retrieval`. |
| `test_user_agent_from_account_config_everywhere` | Every outbound request in the content path carries the configured UA (assert on `responses` request headers). |
| `test_fallback_domains_from_account_config` | Fallback list comes from config, not `['travelmemo.com']`. |
| `test_primary_defaults_unchanged` | REGRESSION: no new env vars → today's exact URL/UA/signature. |
| `test_fallback_signature_localized` (in `test_caption_generator.py` extension) | German fallback signature for secondary; current English default for primary. |
| `test_extract_url_slug_single_source_of_truth` | Both former call sites use one helper, same results. |

### WP7 — `test_token_refresh.py` (new, scaffolded)

| Test | Spec |
|---|---|
| `test_refresh_success_returns_new_token_and_expiry` | GET `graph.instagram.com/refresh_access_token?grant_type=ig_refresh_token` parsed into token + `expires_in`. |
| `test_refresh_refuses_non_igaa_token` | `EAA...` token → actionable error, **zero** HTTP calls. |
| `test_refresh_http_error_sends_alert_and_exits_nonzero` | Uses `captured_emails`; process exit code ≠ 0. |
| `test_secret_update_invokes_gh_secret_set_env_scoped` | Subprocess mocked: `gh secret set <NAME> --env <env>`, token via stdin, never argv. |
| `test_token_value_never_logged` | caplog at DEBUG contains no token substring. |
| `test_expiry_threshold_logic` | Refresh proceeds inside the window; warns/no-ops outside it. |
| `test_threads_token_refresh` | xfail placeholder: Threads long-lived tokens refresh via `th_refresh_token` on `graph.threads.net` — confirm endpoint during implementation; extend workflow if confirmed. |

### WP1/WP2 — no new behavior tests

Deliverables are the CI workflow, root `pytest.ini`, applied `live_api` markers, and the implemented `conftest.py` (smoke-tested by every other file importing its fixtures).
