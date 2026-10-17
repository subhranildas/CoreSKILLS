# Development execution profiles

Edit `execution_profile` in the application's copy of `workflow-plan.yaml`, never the library template during execution:

```yaml
execution_profile:
  name: development
  disabled:
    hardware:
      reason: Board unavailable during workflow testing
    help-ci:
      reason: Testing build integration only
```

An absent section means no overrides. Use `disabled: {}` to restore all work. IDs must exist in the plan; the entrypoint cannot be disabled. Each entry requires a nonempty reason. This profile is an explicit development scope override, independent of `skippable`; it can exclude normally required work, and the run must disclose that reduced scope.

Disabling a workflow disables its whole subtree, including the commit/report obligations belonging to excluded work. Disabling a leaf excludes that leaf. Existing commits and evidence are preserved. Neither case counts as a pass or satisfies success checks. A scoped selection inside a disabled parent remains disabled; it cannot bypass the profile.

Preview with `python -B <CoreSKILLS>/zephyr-platform-bringup/scripts/select-workflow.py <project-plan> --node <node-id>`. `allowed_node_ids` retains structural membership for reporting. Schedule only `executable_node_ids`. Save `disabled_nodes` with inherited reasons, and display `profile_blockers` before executing. Selection is a preview, not evidence of readiness.

Dependencies on disabled work, or a workflow containing disabled required results, block progress. This includes inherited root event dependencies. Do not auto-run excluded work or accept disabled work as evidence. Explicitly revise the project scope/dependencies and verify replacement inputs before continuing. Merely marking a predecessor skippable does not satisfy its dependents.

At start/resume and checkpoints, compare the plan/profile with the saved selection. If changed, pause and show the added/removed work and dependency effects. Preserve history and reconcile affected results; never rewrite passed work as disabled or silently advance the cursor. The native CLI binds its snapshot to a plan hash: create a reviewed new run for plan/profile changes; `reconcile` only adopts the current leaf configuration. The skill-driven coordinator may reconcile a saved session at a user-reviewed checkpoint, recording both selections and invalidated results.

Reports list disabled IDs, reasons and profile name separately from passed, failed and skipped work. Completion means the enabled development scope finished, not that full platform acceptance passed. A selection with no executable work has outcome `disabled` and creates no commits. Unmodified profiles preserve existing behavior.
