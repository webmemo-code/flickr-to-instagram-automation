# Risks & Sequencing

## Sequencing rules

```
WP1 → WP2 → WP3 → WP4 → WP5 → WP7 → WP8 → WP9
        └──→ WP6 (parallel to WP3–WP5) ──┘
```

1. **Production posts daily throughout the refactor.** One WP = one PR, gated by WP1's CI workflow. Never merge red. Each PR must be independently revertable.
2. Merge state-touching WPs (3, 5) **right after** a successful scheduled posting run, then watch the next run before starting the following WP.
3. WP4 follows WP3 immediately: fail-loud without reliable alerting is a regression in operability.

## Risks

### 1. State-data compatibility (hard contract)
Old and new code overlap in production during rollout. `posts.json`/`metadata.json`/`failed.json` on the `automation-state` branch must stay readable by both. Rule: new code may **ignore** unknown fields (e.g. legacy `retry_history`), must not **require** new ones, must not change the written schema. Enforced by `test_existing_posts_json_parses_unchanged` (fixture copied from real production state).

### 2. Fail-loud is a behavior change with an ops cost (intended)
After WP3, a transient GitHub API blip fails the run where it previously "succeeded" dangerously. A red run with `CriticalStateFailure` needs **no state repair** — just re-run (or wait for the next scheduled run). Documented in the runbooks; must be restated in the WP3 PR description.

### 3. Token migration timing
Strict order: WP7 merged → scheduled/dispatch refresh proven for **reisememo** (already IGAA) → Travelmemo swap per runbook → verify one posting run on `graph.instagram.com` → keep the EAA token valid (not revoked) ~1 week as rollback. Do the swap right after generating a fresh IGAA token so the weekly cron fires well inside the 60-day window.

### 4. Concurrent readers of the state branch
The delayed-Threads workflows read the same `automation-state` branch. WP3's write batching must preserve write order so a concurrent Threads run never observes a post without its threads-due record (see [03-state-layer-spec.md](03-state-layer-spec.md) §Write batching).

### 5. CI gate blind spots early on
Until WP3/WP6 tests land, WP1's gate protects less than it appears (`instagram_api.py`, `storage_adapter.py` have zero coverage today). Hence WP2/WP3 immediately after WP1, and hence WP6's REGRESSION tests that must pass **before** the change.

### 6. `gh secret set` PAT is a new credential
`GH_PAT_SECRETS_ADMIN` can rewrite repo secrets. Mitigations: fine-grained, single-repo, secrets-write-only; value delivered via stdin; never logged. If Walter prefers not to mint a PAT, fallback: the refresh workflow opens an issue with instructions instead of writing the secret (loses full automation — decide at WP7 kickoff).

## Explicitly deferred (recorded so nobody "helpfully" does them)

| Item | Why deferred |
|---|---|
| `social-automation.yml` inline Python heredocs (config validation, completion check) duplicating `main.py` logic | Working; dedup into `main.py` subcommands is a clean follow-up after stabilization |
| `blog_content_extractor.py` (862 lines, triple fallback) rewrite | WP6 only dedupes + injects config; a rewrite risks caption quality regressions |
| Storage backend redesign (move off Contents API / orphan branch) | Out of targeted scope; current design works within GitHub-only constraints |
| Threads duplicate-post window (`main.py:343-358`: publish succeeds, persist fails) | WP3's fail-loud makes it visible instead of silent; a transactional fix is a follow-up |
| Retry-system redesign (`FailedPosition` flow) | Works; only the dead `retry_history` model is removed (WP5) |
| True N-account support (registry hardcodes primary + one secondary) | Two accounts via GitHub Environments is sufficient for Travelmemo + Reisememo |

## Post-refactor follow-up candidates (not committed)

- Threads publish/persist transactionality (idempotency key or pre-persist "pending" record)
- Workflow heredoc dedup into `main.py` subcommands (`--validate-config`, `--check-complete`)
- `blog_content_extractor.py` structural simplification behind the now-tested config seam
