---
name: workflow-tree-editor
description: Interactively add a nested workflow and its work units to an existing workflow plan, reviewing placement, success criteria, dependencies, skip flags, and resume impact before applying validated changes.
---

# Add a workflow to an existing tree

## Runtime workspace boundary

Read [workspace-boundaries.md](../zephyr-platform-bringup/references/workspace-boundaries.md) before any run mutation. This repository and installed skill definitions are read-only during execution. Resolve the separate application/runtime roots and saved protected roots; check every destination with the boundary helper. Templates, edits, reports, snapshots and commits target project copies only. If this library is selected as the application, stop and request a separate application path. Use `python -B` for library helpers.


Edit orchestration definitions, not the application behavior the new workflow will later implement. Start by reading the active plan, session, repository instructions, and linked procedures. For this bundle use [entry/skip rules](../zephyr-platform-bringup/references/entrypoint-and-skips.md), [nested execution](../zephyr-platform-bringup/references/nested-workflows.md), [work units](../zephyr-platform-bringup/references/work-units.md), and the commit/report skills. Do not reset the existing tree or execute a newly added workflow merely because its definition is approved.

## Inspect and discover

Locate the project's plan through `session.workflow_plan` or the user's supplied path. Distinguish a project copy from the bundled default. Ask which to edit if both are plausible; default to the project copy when an active session identifies it. Read the entire tree, templates, active stack, outstanding questions, completed/skipped work, and commit/report state. Show the relevant branch and existing order.

Save editing state using [workflow-edit-session.yaml](assets/workflow-edit-session.yaml). Record the original plan hash, paths, source identity, and return checkpoint. If the parent has an operation running, finish or safely suspend it before applying plan changes; never run the editor and parent as concurrent writers.

## Interactive design loop

For top-level additions or sequence changes, also review the root's `workflow_config` using [root configuration](../zephyr-platform-bringup/references/root-configuration.md). Every direct root child appears once as a workflow event; update that event sequence and dependencies together with root membership. Include root event checks/checkpoints and resume impact in the candidate diff.

Every added work leaf must have its own `work_config` file. Follow [leaf configuration](../zephyr-platform-bringup/references/leaf-configuration.md) to ask about ordered actions, commands, inputs, step checks, skip/checkpoint flags, and completion overrides. Include these config files in the candidate diff and preserve step-level resume state when editing existing leaves.

Ask small groups of questions and retain answers. Discover values from the repository where possible. Establish:

- Workflow purpose and inputs/outputs; parent and position before/after a specific sibling.
- Child workflows and concrete leaf work units, each with a unique ID and explicit Boolean `skippable`.
- Observable success criteria and verification procedure for every added leaf, and aggregate acceptance for every added workflow.
- `depends_on` IDs, required input evidence, and behavior if a prerequisite is skipped or blocked.
- Procedure reference or existing skill to use; application/platform/variant expansion if needed.
- Impacts on active/completed work and where execution should resume.

Use [node schema](references/node-schema.md) for fields and dependency semantics. New work inherits the existing failure-intervention, commit review/signoff, update-report, and checkpoint policies. Instantiate commit/report children through the existing templates, preserving their explicit skip flags. Adding a definition does not itself generate nested work commits for each future work unit.

Draft a candidate plan and procedure in separate editing artifacts. A new reusable skill is optional: usually a focused project procedure is enough. Show the before/after tree, exact file diff, criteria, skip flags, dependencies, and affected resume position. Ask “Apply this addition, request changes, pause, or stop?” Repeat revisions without a fixed round limit. Never treat silence or a Continue in the parent as approval of an unseen edit.

## Validate and apply

Only plan schema 3 and root/leaf schema 1 are supported. For declared older plans, follow [explicit migration](references/migration.md) before current validation; never downgrade a version to bypass config requirements. Invalid current versions remain intervention blockers.

Validate the existing and candidate plans using `scripts/validate-workflow-plan.py <plan.yaml>` (Python 3.9+ and PyYAML required). Resolve existing invalid structure before applying a candidate; do not silently rewrite unrelated definitions. The validator checks tree shape, IDs, flags, leaf criteria, procedure paths when supplied, template wiring, and dependencies compatible with sequential ordering. It does not verify the meaning of criteria or an executable procedure. Review those manually and verify companion skills are accessible.

Before review, capture manifests for the complete target and candidate file sets with `scripts/file-state.py capture --snapshot-dir <snapshots> --output <new-manifest.json> <files...>`. Include the plan, referenced root/leaf configs and procedures, all affected files, and absent target paths for newly created files. Preserve target/candidate path mappings. Hash the candidate manifest itself and save that hash with acceptance. Plan hashes alone do not authorize changes to other files.

Immediately before applying, verify the accepted manifest hash and run `file-state.py check` on both original and candidate manifests; reconcile the current session separately. File edits, deletion/creation, corrupted snapshots, or changed candidates invalidate approval: rebuild and ask again. Back up each target and apply only accepted mappings. Validate/read back all resulting files, preserving per-file recovery state; stop for intervention on failure. Save the entire apply record, not only `plan_written`.

Pin the original manifest's SHA-256 at capture and the exact target/candidate mapping hash at acceptance as well. Recheck both before apply; a changed mapping or rewritten baseline manifest invalidates approval even when candidate bytes are unchanged. Apply from verified snapshot bytes rather than re-reading mutable candidate files between verification and write. Use a single writer and recheck each target immediately before replacing it; unexpected concurrent changes stop the apply for intervention.

Reconcile the session without fabricating progress: add pending records for new IDs, mirror flags, retain history/results/commits for existing IDs, and mark only affected results stale. Adding required work to a completed parent reopens that parent. Do not rename/remove/move existing nodes as a side effect of an insertion. Refresh pending checkpoints whose next action changed. If already-completed work must be revisited, show that impact during design and obtain agreement.

Treat the applied definition/report change as one editor work unit. Its success criteria are accepted design, valid/read-back plan, accessible procedure, consistent saved resume state, and preserved existing history. When these pass, invoke [git-work-commit](../git-work-commit/SKILL.md) interactively, then [commit-update-report](../commit-update-report/SKILL.md) through the commit child. Git identity/repository or commit/report failures save intervention state. Do not initialize Git, bypass commit review, or create recursive editor work to commit its bookkeeping. Resume records and report artifacts may remain modified/untracked by design.

Only after required commit/report completion return to the saved parent and offer its updated Continue/Skip/Pause/Stop checkpoint. Approval to insert is not authorization to run new hardware, provisioning, publishing, or other side effects.

## Pause and resume

For scoped runs, preview how edits affect the selected allowed IDs and instances. Adding descendants to the selected subtree requires explicit selection review before they can run. Preserve the parent return checkpoint, and do not expand execution into siblings just because the plan changed.

File-state manifests use schema 2: source, resolved target and snapshot paths are root-relative; only the workspace root is absolute. Capture with an explicit `--root <application>` covering the project/candidate/snapshot files. Original path and resolved target are both verified, so retargeted links/junctions invalidate review even with matching bytes.

When transferring a run, copy the full root-relative tree and run `file-state.py relocate <manifest> --root <new-root> --output <new-manifest>`. Relocation checks source/snapshot hashes and link targets at the destination and sets `requires_reapproval`. Archive original manifests, update project boundaries/path mappings, clear pending editor/commit approvals, and obtain a new review of the relocated mapping/manifest hashes. Do not clear the flag to reuse an old approval. Historical results remain evidence, subject to input reconciliation. Legacy schema-1 manifests require explicit recapture/migration from verified old files; their old approvals never transfer automatically.

Pause/Stop saves the proposal, decisions, hashes, pending question, application state, and commit/report progress. Leave the live plan unchanged if it has not been applied. Resume by reading the edit record and reconciling its hashes with actual files; retain feedback but reapprove changed candidates. If the plan was already applied, complete reconciliation/commit/report recovery instead of inserting duplicate IDs. Restore the parent at its saved or explicitly revised checkpoint, not at the beginning of the whole bringup.
