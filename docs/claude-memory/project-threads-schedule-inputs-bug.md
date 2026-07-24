---
name: project-threads-schedule-inputs-bug
description: Why the Threads delayed cross-post workflows fail on schedule (0 jobs) — inputs context bug
metadata:
  type: project
---

The Threads delayed cross-post caller workflows fail on **scheduled** runs with 0 jobs / ~2s / "workflow file issue," while manual dispatch works.

**Root cause:** `primary-threads-delayed.yml` (and `secondary-threads-delayed.yml`) pass `dry_run: ${{ inputs.dry_run || false }}` and `threads_limit: ${{ inputs.threads_limit || 1 }}` into the reusable `threads-cross-post.yml`, whose inputs are typed (`boolean`/`number`). On a `schedule` trigger the `inputs` context does not exist, so the value fails type-coercion at reusable-workflow instantiation — the run dies before any job spawns. Manual `workflow_dispatch` works because `inputs` is populated.

**Fix:** gate on `github.event_name == 'workflow_dispatch'`. Tracked in issue #194 (comment dated 2026-07-11 has the full diagnosis + fix spec). Secondary has the identical latent bug (schedule currently commented out).

**Diagnostic tell:** a failing reusable-workflow call with `total_count: 0` jobs and empty logs = a workflow-file/instantiation error, NOT a runtime error. Check the `with:` expressions for undefined contexts on the trigger type. See [[project-workflow-status-jul-2026]].
