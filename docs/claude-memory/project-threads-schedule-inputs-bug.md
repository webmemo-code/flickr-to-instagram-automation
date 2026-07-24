---
name: project-threads-schedule-inputs-bug
description: RESOLVED — Threads delayed cross-post workflows failed on schedule (0 jobs) due to the inputs-context bug; fix is live in both callers. Durable part: the 0-jobs diagnostic tell
metadata:
  type: project
---

**RESOLVED.** The Threads delayed cross-post caller workflows used to fail on **scheduled** runs with 0 jobs / ~2s / "workflow file issue," while manual dispatch worked. The fix below is now live in both caller workflows; this file is kept for the diagnostic pattern, which generalizes.

**Root cause (historical):** `primary-threads-delayed.yml` (and `secondary-threads-delayed.yml`) passed `dry_run: ${{ inputs.dry_run || false }}` and `threads_limit: ${{ inputs.threads_limit || 1 }}` into the reusable `threads-cross-post.yml`, whose inputs are typed (`boolean`/`number`). On a `schedule` trigger the `inputs` context does not exist, so the value fails type-coercion at reusable-workflow instantiation — the run died before any job spawned. Manual `workflow_dispatch` worked because `inputs` was populated.

**Fix (now live):** both callers gate the expressions — `${{ github.event_name == 'workflow_dispatch' && inputs.dry_run || false }}` (and likewise `threads_limit`). Diagnosed and specced in issue #194 (comment dated 2026-07-11). Secondary's schedule remains commented out for an unrelated reason (secondary Threads env not yet populated), but it carries the same fixed expressions for when it's enabled.

**Diagnostic tell:** a failing reusable-workflow call with `total_count: 0` jobs and empty logs = a workflow-file/instantiation error, NOT a runtime error. Check the `with:` expressions for undefined contexts on the trigger type. See [[project-workflow-status-jul-2026]].
