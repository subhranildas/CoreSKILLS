# Editable top-level event sequence

The root node's `workflow_config` points to `root-workflow.yaml` relative to the plan. Copy it beside the project plan and leaf directory. It supports the same ordered action/check format as leaf configs, plus `action: workflow` with a `workflow` child ID. Edit inputs, startup actions, stage order, dependencies, instructions, checks, commands, and checkpoints in your project's copy.

## One source of execution order

For the root, `steps` in this file is the authoritative event order. Root `children` in the plan declares membership, not a second execution order. Every direct root child must appear exactly once as a workflow event. Validate against the effective order from config, including cross-node dependencies. Do not omit a required child to skip it; use its explicit skip policy. Nested parents continue to use their plan child order.

Reordering events requires updating any `depends_on` step IDs so prerequisites still finish first. The validator rejects missing/duplicate child references, references to grandchildren, invalid step dependencies, and incompatible plan dependencies. It validates structure, not whether a new order is sensible for the hardware/application; review the proposed sequence and input contract before applying it.

Non-workflow actions use the leaf action format, including explicit argv or shell command, checks and step checkpoints. Root-local actions are orchestration activities such as loading, reconciliation and finalization. If an event performs substantial implementation requiring its own commit, add it as a child workflow/work unit through the tree editor rather than creating an untracked root-local implementation step.

## Gating and skip rules

Each event verifies its own checks. A workflow event waits for its child's required work, accepted commits and verified update reports before evaluating the event check. If the child includes permitted omissions, describe them accurately and check that agreed scope is still satisfied; do not infer a pass from returning control.

A successful event with `checkpoint_after: true` offers progression choices. Inner checkpoints still apply. Combine duplicate questions at coincident boundaries; false suppresses that event's extra question, not user intervention or commit acceptance. Failure always pauses for intervention. Parent automatic progression does not override commit review.

For local actions, `skippable` controls eligibility. For workflow events, both the event and referenced child must permit skipping; this is a restrictive event-level override. Record the skip and its acceptance/dependency impact; do not mutate the child's flag implicitly. A skipped event cannot fulfill a later required `depends_on`. Explicitly revise scope/dependencies with valid evidence if needed.

## Edits, migration, and resume

Before adopting a revision, save full-byte immutable root/plan/procedure snapshots with the editor's file-state helper. Store their paths/hashes in session history and event attempts. Compare old/new content against snapshots; missing/corrupt history prevents selective reuse and requires conservative revalidation. Preserve prior commits and snapshots.

Store root config hash, event cursor, per-event input/config identity and results in the session. Reload at checkpoints/resume, compare IDs/content/order, preserve unchanged valid results, and reopen changed events plus affected dependents. Never replay an unknown flash/commit or restart all children merely because the root resumed. Reconcile an active child before moving it in sequence; apply edits at a safe saved boundary, with a refreshed checkpoint.

For old project plans, create a root config matching the actual existing root child order rather than replacing it with the bundled sequence. Attach `workflow_config`, upgrade plan schema, validate, and preserve saved history. New children must be added to root event membership when inserted under the root. The tree editor reviews the root config diff and dependent resume impact together with plan changes.

This file configures Codex's conversational orchestration; it does not itself execute a background program.
