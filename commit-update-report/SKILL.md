---
name: commit-update-report
description: Generate a plain-text update report for each workflow-created Git commit, recording actual changes, validation, signoff, review state, and next actions in a resumable per-commit file.
---

# Commit update report

## Runtime workspace boundary

Read [workspace-boundaries.md](../zephyr-platform-bringup/references/workspace-boundaries.md) before any run mutation. This repository and installed skill definitions are read-only during execution. Resolve the separate application/runtime roots and saved protected roots; check every destination with the boundary helper. Templates, edits, reports, snapshots and commits target project copies only. If this library is selected as the application, stop and request a separate application path. Use `python -B` for library helpers.


Run as a child of `git-work-commit` immediately after a primary or correction commit exists, including recovered interrupted commits. Inputs: target repository, exact full commit SHA, work ID, session/review records, verification observations, and output directory. Do not report whichever commit happens to be HEAD instead of the requested SHA.

## Generate

Consume the report child's saved effective skip flag and policy source (leaf `completion.update_report.skippable` overrides the template unless null); never reread the template as the effective policy. Include run/work/attempt identity in the report and compare it with commit trailers. Historical legacy commits are explicitly labeled when no attempt identity can be verified.

1. Inspect the requested commit's full SHA, parent(s), subject/body, author/committer, signoff trailers, and actual changed paths/diff. Use Git argument separation and proper quoting. Summarize the recorded commit, not uncommitted changes. Do not infer a passing check from commit existence.
2. Read the work's success criteria, build/runtime results, evidence paths, review round, and acceptance state. Distinguish verified results, failures, pending checks, and skipped work. If information is unavailable, say unknown. Attribute measurements and commands to their recorded evidence.
3. Adapt [update-report.txt](assets/update-report.txt). Write UTF-8 plain text to `bringup/<platform>/updates/<full-sha>.txt` by default, or the project's explicitly selected report directory. For standalone use, default to `workflow-updates/<full-sha>.txt`. Include the work ID inside the report; use the full SHA as the filename to avoid collisions.
4. Write via a temporary sibling file and replace after a successful write when possible. Read it back and verify that its SHA/work ID and changed paths match Git, required sections are present, and validation/review claims match evidence. Record output path and file SHA-256 in the session. Return success only when the file exists and verification passes.

## Review, failure, and resume

Initial report generation happens before result acceptance, so label acceptance pending. Refresh the same SHA's report after acceptance, requested correction, amended/superseded status, or a newly resolved verification result. Save update events in session history; do not create duplicate reports for an unchanged SHA on resume. Reuse an existing file only after checking its contents and current review state.

Keep a separate report for every primary and correction commit. If an explicitly authorized amendment creates a new SHA, create its report too and identify the superseded SHA without deleting the earlier report. For an interrupted commit, recover its identity before generating a report. If technical verification fails after commit creation, still generate a factual report describing the failure; it is not a success claim.

On missing Git data, write/access failure, or inconsistent report content, save `awaiting_intervention` and explain the required fix. Do not complete the commit child or move to the next unit until the report is verified, unless its explicit skippable policy permits a user-requested skip. Pause/Stop retains pending report work for resume.

## No recursive report commits

This child writes local update artifacts; it does not create a commit, push, or stage its own report. Reports are excluded from automatically selected commit paths, even though they may remain untracked/modified. Do not change `.gitignore` without a project need. Export/transfer reports with the live session. If the user separately asks to version reports, use a deliberate finite batch of existing reports and document where the resulting commit's own report is stored; never automatically commit reports recursively.

Every report child has an explicit `skippable` flag, default false. A permitted skip is recorded with reason and missing report SHA; it does not fabricate a report. A skipped commit child creates no SHA and therefore no per-commit report obligation. The parent may still record a skipped work result separately.
