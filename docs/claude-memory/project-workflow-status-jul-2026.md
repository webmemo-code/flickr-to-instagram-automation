---
name: project-workflow-status-jul-2026
description: "(snapshot 2026-07) Snapshot of primary/secondary workflow status as of 2026-07-11 after the WP5-7 refactor"
metadata:
  type: project
---

Status of the revamped Flickr→Instagram/Threads automation as of **2026-07-11** (after WP5/WP6/WP7 refactor merges):

- **Test suite:** green — `154 passed, 3 skipped, 8 deselected` (deselected = `live_api`). Codebase healthy.
- **Primary Flickr→Insta:** `disabled_manually` — album auto-completed 2026-04-25 (workflow disables its own schedule on completion; not a bug). Restart = set new `FLICKR_ALBUM_ID` + re-enable.
- **Secondary (reisememo) Flickr→Insta:** WORKING — manual dispatch succeeded 2026-07-10 after IGAA creds added to the `secondary-account` environment. Schedule still commented out (WP8 activation pending).
- **Primary Threads delayed:** FAILING every scheduled run (live bug, not historical) — see [[project-threads-schedule-inputs-bug]] / issue #194.
- **Secondary Threads delayed:** never run (schedule commented out); has the same latent inputs bug.

Open issues to finalize: #192 (primary EAA→IGAA / WP7), #193 (SMTP alert auth), #194 (Threads schedule inputs bug — root-caused), #181 (WP8 reisememo activation), #182 (WP9 docs sync).

Primary uses legacy `EAA` token; secondary uses `IGAA`. Token refresh (`token-refresh.yml`) only rotates `IGAA` tokens.
