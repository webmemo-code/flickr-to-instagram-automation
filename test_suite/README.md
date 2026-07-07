# Test Suite

Offline-first pytest suite for the Flickr-to-Instagram automation. CI runs the
offline subset on every PR (`.github/workflows/tests.yml`).

## Running tests

From the repo root (not `test_suite/`) — `pytest.ini` sets `pythonpath = .`
and `testpaths = test_suite`:

```bash
# Offline suite (what CI runs) — no live Flickr/Anthropic/travelmemo.com calls
python -m pytest -m "not live_api"

# Everything, including live-API tests (requires real credentials in .env)
python -m pytest

# A single file
python -m pytest test_suite/test_state_manager.py -v
```

`test_suite/run_tests.py` is a thin alias over the same commands for
muscle-memory compatibility (`python run_tests.py quick`, `all`, `live`,
`blog`, `caption`, `integration`, `threads`).

## Markers

- `live_api` — hits a real external service (Flickr, Anthropic, travelmemo.com).
  Excluded from CI via `-m "not live_api"`. Needs real credentials in `.env`.
- `slow` — long-running; not currently auto-excluded.
- `integration` — exercises multiple modules together rather than one unit.

## Fixtures (`conftest.py`)

Shared fixtures live in `conftest.py` — no test file should redefine one of
these:

| Fixture | Purpose |
|---|---|
| `full_env` | Factory: monkeypatch a complete valid `Config()` environment; `full_env(**overrides)`. |
| `igaa_env` / `eaa_env` | `full_env` variants with an `IGAA...` / `EAA...` Instagram token, for Graph API domain routing tests. |
| `fake_storage` | In-memory storage adapter double with a call log (`.calls`, `.writes`), seeding, and failure injection. |
| `mock_github_contents` | `responses`-based fake of the GitHub Contents API (404-first-run, 403, 500, connection-error, success scenarios). |
| `graph_api` | `responses`-based canned Meta Graph API payloads (media create/publish, error 190, rate-limit, token refresh). |
| `sample_photo` / `sample_album` | `EnrichedPhoto` dataclass factories — always dataclasses, never dicts. |
| `sample_posts_json` | Realistic `posts.json` content, including a legacy `retry_history`/`flickr_photo_id` entry. |
| `captured_emails` | Patches `smtplib.SMTP`; yields the list of sent messages. |
| `account_env_reisememo` | `SECONDARY_*` env preset for the reisememo.ch account. |

## Conventions

- Tests using external APIs are marked `@pytest.mark.live_api` (or
  module-wide via `pytestmark = pytest.mark.live_api`).
- New tests should build photo data with `sample_photo`/`sample_album`
  (or `EnrichedPhoto` directly) — never a plain dict.
- Scaffolded tests carry `@pytest.mark.xfail(reason="WP<n> not implemented")`
  until their work package lands; see `docs/refactor/02-test-scaffold-map.md`
  for the fixture contract and per-WP test map.
