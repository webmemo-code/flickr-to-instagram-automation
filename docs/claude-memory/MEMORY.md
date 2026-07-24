# Memory Index

This directory contains memory files synced across the user's development machines. [CLAUDE.md](../../CLAUDE.md) instructs Claude to read this index on session start; leaf memory files are read on demand when the index suggests they're relevant.

Add a one-line entry per memory file, grouped under a section that fits the topic. Keep each line under ~150 characters: `- [Title](filename.md) — one-line hook`.

## User

<!-- e.g. - [Preferred name](user-name.md) — user goes by "Sam", not "Samuel" -->

## Feedback

<!-- e.g. - [Always branch + PR](feedback-pr-workflow.md) — never push to main directly; user works across machines -->

## Project

- [Stabilization refactor plan](project-refactor-stabilization-plan.md) — docs/refactor/ + issues #174-#182; Claude reviews WP PRs against scaffolded TDD tests
- [Workflow status Jul 2026](project-workflow-status-jul-2026.md) — snapshot of primary/secondary Flickr+Threads workflow health post-refactor
- [Threads schedule inputs bug](project-threads-schedule-inputs-bug.md) — why Threads workflows fail on schedule (0 jobs); issue #194

## Reference

<!-- e.g. - [Bug tracker](reference-linear.md) — pipeline bugs live in Linear project "INGEST" -->
