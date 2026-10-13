# Run one workflow or work leaf independently

The bringup entry supports `full` (default) and `scoped` execution. A scoped run selects one existing node ID and executes only its subtree. Selecting a work leaf executes its configured steps and commit/report children. Selecting a workflow executes its descendants in their existing order. It does not modify the plan's root, membership, flags or procedures.

## Select and bootstrap

Ask for the application workspace, selected node ID and any application/platform/variant instance filters not established by context. Use the read-only `scripts/select-workflow.py <project-plan> --node <id>` helper to validate the full plan and display selected nodes, ancestry, expansion requirements and external prerequisites. `--list` lists valid targets. `--instance application=sensor --instance platform=beta --instance variant=debug` records explicit instance selectors; the helper does not invent or instantiate combinations.

Always perform workspace/boundary checks, accessible tool checks, config validation/snapshots, source/toolchain identity and interrupted-operation reconciliation before execution. These are bootstrap checks even when the root's initialize event is outside the selected scope. Do not run arbitrary root-local commands or its entire event sequence as a shortcut to starting one child.

Create a separate run/session and log under a unique runtime directory such as `bringup/<platform>/scoped/<node>/<run-id>/`. Copy editable project configs or reference the user's project-owned definitions; never edit installed/source templates. If invoked from a paused full run, save its checkpoint and use that run as a read-only evidence source; do not reset or overwrite its execution records.

## Prerequisites and instance selection

Evaluate explicit plan dependencies on selected nodes and their ancestors, and inherited root event dependencies. The helper lists outside-scope dependency IDs. Check actual input contracts too: build work still needs exact commands/configs, hardware work needs verified image/device identity, and registration needs platform support. Structural selection is not proof of execution readiness.

Prerequisites may be satisfied by current verified source/configuration/artifacts or recorded results from another run. Record provenance and input identity. Merely existing files, skipped checks, or a prior stale pass are insufficient. Do not require the historical workflow itself to rerun when equivalent inspected evidence supplies the needed inputs.

If required inputs are absent, stop for intervention and offer providing/fixing inputs, explicitly expanding the requested scope, Pause, or Stop. Never silently schedule an outside-scope predecessor. An explicit scope expansion creates/reviews a new selection and invalidates affected checkpoints; it is not permission to bypass checks.

For `expand_per` leaves, resolve concrete instances from the agreed combination/peripheral set and intersect with the supplied selectors. Ask about missing selectors when several choices exist. Reject unknown/mismatched filters and a required selection with zero instances; never silently mark an empty matrix passed. Save concrete instance IDs and distinct configs/commands. A nonexpanded leaf may still consume relevant context filters, but do not invent a cross-product.

## Execute, stop, and resume

Persist `workflow.execution` with mode, selected node, allowed static IDs, concrete instances, filters, prerequisite evidence and stop boundary. The scoped coordinator enters the selected node and schedules only allowed descendants plus required commit/report children. Plan ancestry is context, not permission to run those ancestors/siblings. Use the same per-step checks, user intervention, Continue/Skip/Pause/Stop, effective skip policy, commit review/signoff, recovery identities, and flow logging.

Mark nonselected work `not_selected` in scope reporting, not skipped/passed and not modified in another run. Completing a scoped run means the selected acceptance criteria are met; it does not mean the complete platform bringup succeeded. The selected subtree may be skipped only under its explicit policy, with the run outcome then skipped rather than passed.

After the selected node returns and its commit/report obligations finish, save the scoped result and stop. Never fall through to the next sibling or root handoff. Return a saved parent checkpoint if one exists, without consuming Continue. Results can be imported into a full run only after checking identities, criteria and acceptance; import does not advance the full run automatically.

On resume, reload selection/config hashes, intersect the saved scope with the current plan, reconcile inputs and operations, and refresh affected checks. Plan edits adding selected descendants require explicit scope review before running them. Preserve IDs/attempts for an interrupted same-run resume. Unknown/deleted selected IDs require intervention rather than switching to full mode.

Examples:

```text
Use $zephyr-platform-bringup in scoped mode. Run only register for beta
in my firmware repository. Inspect prerequisites; do not run siblings.

Use $zephyr-platform-bringup to run only build-combination for
application sensor, platform beta, variant debug, with a separate session.

Resume my scoped register session at <session-path>; keep the same scope.
```
