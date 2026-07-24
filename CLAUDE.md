# CLAUDE.md — Project Guide for AI Assistants

## Project Overview

Flickr-to-Instagram automation: posts photos from a Flickr album to Instagram daily with AI-generated captions (Anthropic Claude Vision). Runs as a GitHub Actions workflow. Supports multiple Instagram accounts with independent state.

## Key Commands

```bash
# Run locally (requires .env with all credentials)
python main.py --account primary --dry-run    # Test without posting
python main.py --account primary              # Post next photo
python main.py --account primary --stats      # Show progress

# Secondary account
python main.py --account reisememo --dry-run

# Run tests (from repo root — pytest.ini sets testpaths/pythonpath)
python -m pytest -m "not live_api"            # All tests except live-API ones (what CI runs)
python -m pytest                              # Everything, including live-API tests (needs real credentials)
python -m pytest test_suite/test_blog_content_extractor.py  # A single file
```

## Architecture

### Branch Strategy
- **`main`** — Application code only. No state data.
- **`automation-state`** — Orphan branch. State data only (`state-data/{account}/album-{album_id}/`). Automated commits from workflow runs; never merge into `main`.

### Module Responsibilities
| Module | Role |
|--------|------|
| `main.py` | Orchestration, CLI entry point (`--dry-run`, `--stats`, `--account`) |
| `config.py` | Loads env vars, initializes account-specific config via `Config(account=...)` |
| `account_config.py` | `AccountConfig` dataclass, `AccountManager` for multi-account settings |
| `flickr_api.py` | Flickr API — fetch album photos, EXIF data, metadata |
| `caption_generator.py` | Anthropic Claude Vision — multi-language caption generation with blog context |
| `instagram_api.py` | Instagram Graph API — media container creation, publishing, URL validation. Supports both `graph.facebook.com` (legacy `EAA...` tokens) and `graph.instagram.com` (new `IGAA...` tokens) via auto-detection in `config.py` |
| `blog_content_extractor.py` | WordPress REST API — authenticated blog content extraction |
| `blog_url_resolver.py` | Resolves blog post URLs from EXIF data and photo metadata |
| `custom_endpoint_extractor.py` | Custom WordPress endpoint extraction that bypasses Cloudflare bot protection |
| `facebook_api.py` | Facebook Graph API — cross-posts photos to a linked Facebook Page |
| `threads_api.py` | Threads Graph API — delayed cross-posting of Instagram photos to Threads |
| `token_refresh.py` | Automated long-lived token refresh (Instagram IGAA, Threads) for `token-refresh.yml` |
| `state_manager.py` | Orchestrates state operations via storage adapter |
| `storage_adapter.py` | `GitFileStorageAdapter` — reads/writes JSON state on `automation-state` branch via GitHub Contents API |
| `state_models.py` | Dataclasses: `InstagramPost`, `AlbumMetadata`, `FailedPosition`; enums: `PostStatus`, `AlbumStatus` |
| `photo_models.py` | Photo data models (e.g., `EnrichedPhoto`) |
| `email_notifier.py` | SMTP email notifications for album completion and critical failures |
| `notification_system.py` | Higher-level notification orchestration |

### Workflow Files (`.github/workflows/`)
- `social-automation.yml` — Reusable workflow (centralized logic, `workflow_call`)
- `primary-flickr-to-insta.yml` — Primary account: schedule + manual trigger
- `secondary-flickr-to-insta.yml` — Secondary account: schedule + manual trigger

Account workflows pass parameters (account_id, environment_name, caller_workflow) to the shared workflow.

## Conventions

### Code Style
- Python 3.11+ (runs on `ubuntu-latest` in CI)
- Type hints on function signatures
- Docstrings on classes and public functions
- `dataclass` for data models, `Enum` for status types
- Logging via `logging.getLogger(__name__)` — never `print()`
- UTF-8 encoding throughout (titles contain German/multilingual characters)

### Configuration Pattern
- All credentials from environment variables (never hardcoded)
- `.env` file for local development (see `.env.example`)
- GitHub Secrets + GitHub Environments for CI
- `Config(account='primary')` or `Config(account='reisememo')` initializes everything

### Commit Messages
Format: `type: description` (lowercase type, imperative mood)
Types: `fix:`, `enhance:`, `refactor:`, `chore:`, `docs:`

### State Management
- State lives on `automation-state` branch as JSON files via GitHub Contents API
- `posts.json` — array of `PostRecord` dicts (one per posted photo)
- `metadata.json` — album-level stats (counts, completion %, last posted position)
- `failed.json` — failed attempts for retry
- Path pattern: `state-data/{account}/album-{album_id}/{file}.json`
- The `GitFileStorageAdapter` auto-creates the branch on first run

### Instagram API Authentication
- See `docs/instagram-api-creds-configuration.md` for the step-by-step guide to generate and configure a token (the practical how-to; leads with the common pitfalls — don't use the Graph API Explorer, `GET /me` tests no scope, App Review is usually unnecessary in Development mode)
- See `INSTAGRAM_AUTH_GUIDE.md` for background on both API eras (legacy `EAA` vs new `IGAA`) and troubleshooting
- `config.py:_detect_graph_api_domain()` auto-selects `graph.instagram.com` or `graph.facebook.com` based on token prefix (`IGAA...` vs `EAA...`)
- Primary account (`travelmemo_blog`) uses legacy `EAA...` token; secondary account (`reisememo`) uses new `IGAA...` token
- Long-lived tokens expire after 60 days — renewal endpoints differ by token type

### Things to Watch
- `.gitignore` excludes `CLAUDE.md`, `CODEX.md`, `TASKS.md`, `TODO.md` — these are local-only files
- `album_complete.marker` file is written on album completion and is gitignored
- Photo position tracking is 1-based (first photo = position 1)
- Instagram API requires photos to be publicly accessible URLs (Flickr serves this role)
- Dry runs still persist state records (with `is_dry_run` flag) for tracking purposes

## Memory (index read at session start; leaves read on demand)

The repo includes a curated memory directory at [docs/claude-memory/](docs/claude-memory/) that travels with the code so every machine the user works from has the same context. Treat these files as authoritative project memory:

1. Read [docs/claude-memory/MEMORY.md](docs/claude-memory/MEMORY.md) at the start of any session in this repo. It is a one-line index pointing to per-topic memory files.
2. When a linked memory looks relevant to the task at hand, read the linked file in full before acting on it.
3. **Editing rule:** if a session learns something durable (a new feedback rule, a new SDK gotcha, etc.) that belongs in cross-machine memory, edit the appropriate file in `docs/claude-memory/` and update `MEMORY.md` to reference it. Treat changes there like any other code change — branch, PR, review. Do NOT mirror this content into the harness-managed `~/.claude/projects/.../memory/` directory; that location stays per-machine and is allowed to drift from the canonical in-repo copy.
4. Memory file format inside `docs/claude-memory/`: YAML frontmatter with `name`, `description`, and `metadata.type` (one of `user`, `feedback`, `project`, `reference`), followed by the body. Cross-references between memory files use `[[name-slug]]` syntax matching the `name:` field.

