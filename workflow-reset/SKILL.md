---
name: workflow-reset
description: Interactively reset a bringup run's execution state while archiving progress and preserving application source, Git commits, hardware state, and editable project configurations.
---

# Reset workflow execution

Read [workspace boundaries](../zephyr-platform-bringup/references/workspace-boundaries.md) first. Reset only the selected run in the application's runtime directory; this skill never resets or cleans the skill-library repository.

Inspect the session, active operation, pending editor/commit/report reviews, scope and configured paths. If an operation is running or has unknown outcome, reconcile it or wait for a safe boundary before reset. Do not repeat flash/commit operations while resetting. Present these choices:

Preserve `workflow.execution` mode/selected scope during reset. Restarting a scoped run restarts only its selected subtree, never upgrades it to full mode. Keep parent return-session/checkpoint references without modifying that parent's records.

- **Restart execution:** archive state, preserve project plan/root/leaf configs/profile and evidence, start a new run at root initialization.
- **Restart selected subtree:** archive state, reopen the selected node and required affected dependents, preserve unrelated valid results and all history/commits.
- **Pause/Stop:** leave the run as it is.

Show affected record paths, scope, retained work and proposed starting point. Obtain explicit choice before applying. A bare request to reset uses restart execution as the proposal, not destructive deletion. Repeated refinements use the same review loop until the user accepts.

Before writing, run `scripts/boundary-check.py --application-root <app> --runtime-root <run-directory> --write-path <path>` for every archive and changed state path; supply additional protected roots from the session. Resolve absolute paths and symlinks/junctions. Archive full state and pending edit/review records to a new `archives/<unique-reset-id>/` directory; verify copies/hashes before replacing active records. Preserve snapshots, reports and evidence in place and link them from the archive.

For restart execution, create a new run ID and execution record from the current session schema with plan/profile/config references preserved. Clear active execution results/cursors, input responses requiring fresh confirmation, candidate/result approvals, and current operation fields. Preserve boundary fields and archive reference. Existing source/commits remain actual starting inputs; old results stay in the archive and are not automatically marked passed in the new run. Configuration snapshots remain available, with new adoption state captured at initialization.

Create fresh commit-attempt IDs for work reopened by either reset mode, even when subtree reset retains the run ID. Archive old attempt IDs/SHAs and exclude them from new-attempt recovery. Never reuse an old commit solely because its work ID matches. Only an uninterrupted resume of the same attempt retains its identity.

Archive the previous `flow_log` association and select a new run/reset-specific log path. Preserve the old log bytes; do not truncate or append a new run to it. Log the reset checkpoint into the new flow using the custom command tool's event mode after the new record is saved.

For subtree reset, clear/reopen only selected runtime records and dependent results; invalidate associated commit approvals but retain historical SHAs and reports. Root aggregate results reopen as needed. Preserve configuration and recorded scope decisions; ask again only for decisions changed by the reset. Mark the new checkpoint `awaiting_input` rather than scheduling work automatically.

Verify saved state and archive, then report the new run/checkpoint and resume instruction. Write/access/archive failure enters intervention without claiming reset success. Reset is lifecycle bookkeeping, not an implementation work unit, so it does not create a Git commit or a recursive reset-report commit. It does not run `git reset`, `git clean`, revert/amend commits, erase hardware, delete builds or modify templates. Those are separate explicit tasks.
