---
name: project-refactor-stabilization-plan
description: "Targeted stabilization refactor (2026-07) — plan in docs/refactor/, issues"
metadata:
  type: project
---

Approved 2026-07-06 by Walter: targeted stabilization refactor before activating the Reisememo account. Plan lives in `docs/refactor/` (branch `refactor/planning`, PR #173); work packages are GitHub issues #174 (WP1) through #182 (WP9), label `refactor`. Scaffolded TDD skeletons (37 xfail tests + conftest fixture stubs) are in `test_suite/`.

**Locked decisions:** targeted scope only (no storage redesign, no blog-extractor rewrite); keep both Facebook Page and Threads cross-posters; automate IGAA token refresh and migrate Travelmemo EAA→IGAA (pure token swap — domain routing is prefix-based in `config.py`); Sonnet 5 executes most WPs, Opus 4.8 executes WP3 (state-layer safety).

**Claude's standing role:** planner + reviewer. When developers finish a WP PR, review it against the scaffolded tests and the acceptance criteria in `docs/refactor/01-work-packages.md`; approve or file change-request issues. Key invariants to enforce in review: posts.json/metadata.json schema unchanged; state reads fail loud (never return empty on error); regression tests pass before AND after; no scope creep into the explicitly-deferred list in `docs/refactor/99-risks-and-sequencing.md`.

**Progress:** WP1 (#174) done — PR #183 merged 2026-07-07, reviewed and approved post-merge (CI gate `tests.yml` live on main, root pytest.ini, live_api markers applied). Next: WP2 (#175), Sonnet 5.

**Known env quirk:** Walter's local venv is missing `grapheme` (declared in requirements.txt line 6 — CI has it), which fails one Threads caption test locally; fix is `pip install -r requirements.txt`. Root pytest.ini now sets `pythonpath = .`, so tests run from repo root without PYTHONPATH juggling.
