# docs/claude-memory/

Cross-machine memory for Claude Code sessions in this repo. Committed so every machine that clones the repo gets the same context — no per-machine setup beyond `git pull`.

## How sessions pick this up

[CLAUDE.md](../../CLAUDE.md) at the repo root instructs Claude to read [MEMORY.md](MEMORY.md) on session start. `MEMORY.md` is a one-line index pointing to per-topic memory files in this directory.

The harness-managed per-machine memory dir (`~/.claude/projects/<encoded-path>/memory/`) is **separate** and is allowed to drift between machines. Only the in-repo copy here is canonical. Don't try to sync the two.

## When to add a new memory

Add a file here when a session learns something **durable** that future sessions on any machine should know:

| Type | Examples |
| --- | --- |
| `user` | Spelling preferences, role/expertise, working style. |
| `feedback` | Explicit corrections ("don't do X"), validated approaches ("yes, that bundled PR was right"). Lead with the rule, then **Why:** and **How to apply:** lines. |
| `project` | SDK gotchas, undocumented platform behavior, why a workaround exists. |
| `reference` | Pointers to external systems — Linear projects, Grafana dashboards, Slack channels. |

**Do NOT add memory for:** code patterns or architecture (read the code instead), git history (use `git log`), debugging recipes (the fix is in the code), anything already in CLAUDE.md, or in-progress task state (use tasks/plans, not memory).

## How to add or edit a memory

1. **Branch.** Even one-line memory updates go through a feature branch. `git checkout -b docs/memory-<short-description>`.
2. **Create or edit the memory file** in `docs/claude-memory/`. Use kebab-case filenames matching the `name:` slug.
3. **Frontmatter format:**
   ```yaml
   ---
   name: <kebab-case-slug>
   description: <one line — used to judge relevance in future sessions>
   metadata:
     type: <user | feedback | project | reference>
   ---
   ```
4. **Body:** for `feedback` and `project` types, lead with the rule/fact, then `**Why:**` (the reason, often a past incident) and `**How to apply:**` (when/where the rule kicks in). Knowing why helps future-you judge edge cases.
5. **Cross-references:** link related memories with `[[other-name-slug]]` matching the other file's `name:` field. Liberal linking is fine — a `[[]]` that doesn't match an existing memory yet just marks something worth writing later.
6. **Update [MEMORY.md](MEMORY.md)** to add a one-line entry under the appropriate section. Keep entries short (~150 chars).
7. **Open a PR** against `main` like any other code change.

## Why not just edit the harness memory dir?

Two reasons:

- The harness's `~/.claude/projects/<encoded-path>/memory/` is **per-machine**. Edits there don't reach your other machines.
- The harness post-processes every saved memory file with internal metadata (e.g. `node_type: memory`, `originSessionId: <uuid>`). Committing those decorations would create churn-prone diffs on every session. By keeping the canonical copy in `docs/claude-memory/` and only editing it via deliberate commits, the in-repo files stay clean.
