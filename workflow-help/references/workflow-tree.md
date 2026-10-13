# Workflow tree for users

This is the bundled default tree. When asked about a user's configured tree, read that project's plan and root config instead. Root event order is authoritative; flags and steps may have been edited.

```text
Start / resume
|-- Validate separate application/runtime and protected library paths
|-- Load project plan, configs, profile, state and snapshots
|-- Reconcile stale results and interrupted operations
`-- Choose execution scope
    |-- Full: add-platform root
    |   |-- Initialize
    |   |-- Discovery and assessment
    |   |   |-- Discover: inventory -> trace commands
    |   |   |-- Assess: pin baseline -> reconcile hardware
    |   |   `-- Contract: select combinations -> define acceptance
    |   |-- Platform integration
    |   |   |-- Integrate: board support -> minimal compile -> peripheral config
    |   |   `-- Register: command mapping -> dispatch checks -> help/CI
    |   |-- Verification
    |   |   |-- Build matrix: each selected combination -> affected regressions
    |   |   `-- Hardware: flash/boot -> each required capability
    |   |-- Handoff: reconcile results -> handoff report
    |   `-- Finalize
    `-- Scoped: selected workflow/subworkflow/work leaf only
        |-- Verify existing prerequisite inputs; do not run outside siblings
        |-- Execute selected descendants / concrete instances
        `-- Save scoped result and stop / return to paused parent checkpoint
```

Each work leaf has independent editable YAML steps. The shared lifecycle is:

```text
Work step -> verify success checks
|-- Failed / blocked -> save evidence -> user intervention -> reverify
`-- Passed -> next configured step/checkpoint
    `-- Leaf aggregate criteria pass
        |-- Write pre-commit work report
        |-- Resolve effective commit/report skip policy
        `-- Commit child (unless explicitly permitted skip)
            |-- Review exact patch/message <-> revise and recheck
            |-- Accept candidate -> signed-off commit -> verify
            |-- Generate SHA-specific txt update
            |-- Accept result / request correction / Pause / Stop
            `-- Refresh update -> return to parent checkpoint
                |-- Continue -> next permitted work
                |-- Skip -> only if allowed; record reason/impact
                |-- Pause -> save for resume
                `-- Stop -> save and end this run
```

Commit/report defaults are required, with explicit leaf overrides. Skipping work never satisfies its checks. Parent skip excludes pending descendants but preserves completed results; missing prerequisite evidence can still block later work.

On-demand actions do not advance the selected workflow:

```text
workflow-help        -> Explain setup/config/tree/checkpoint read-only
workflow-tree-editor -> Review addition/edit -> validate/apply -> commit/report
workflow-reset       -> Review scope -> archive state -> restart selected execution
```

Custom command steps resolve their invocation first and run through the logged CLI tool when bound. Its event mode records workflow transitions/decisions; it does not automatically observe conversations. Raw bytes and decoded text are preserved. Incomplete capture, corrupted logs, failed checks, and commit/report failures require intervention.
