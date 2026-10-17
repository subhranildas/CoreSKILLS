---
name: zephyr-platform-bringup
description: Interactively add Zephyr platforms to projects with multiple applications and custom build commands, sequencing assessment, board integration, command registration, and build and hardware verification.
---

# Zephyr platform bringup

## Runtime workspace boundary

Read [workspace-boundaries.md](../zephyr-platform-bringup/references/workspace-boundaries.md) before any run mutation. This repository and installed skill definitions are read-only during execution. Resolve the separate application/runtime roots and saved protected roots; check every destination with the boundary helper. Templates, edits, reports, snapshots and commits target project copies only. If this library is selected as the application, stop and request a separate application path. Use `python -B` for library helpers.


Bring a specified application and hardware revision to a reproducible, evidence-backed working state. Distinguish build success, boot success, and verified peripheral behavior.

## On-demand lifecycle actions

Use [workflow-help](../workflow-help/SKILL.md) for onboarding or checkpoint explanations without changing state. Use [workflow-reset](../workflow-reset/SKILL.md) to archive and restart a run or subtree while preserving application changes, commits and configurations. Both return to a saved checkpoint and do not automatically start another unit.

## Interactive new-platform workflow

Read [execution-profiles.md](references/execution-profiles.md) when loading a project plan with development overrides. Honor the selector's executable IDs, disabled dispositions and dependency blockers for full and scoped runs. Profile edits require checkpoint reconciliation; disabled work never runs or counts as passed.

Support independent workflow/subworkflow/work-leaf entry through [scoped-execution.md](references/scoped-execution.md). An explicit named selection runs only that subtree with separate state/logs and prerequisite checks; it never advances into siblings or claims full bringup completion. Use `scripts/select-workflow.py` to validate and preview scope. Full-tree execution remains the default when no narrower selection is requested.

Use the [custom command tool](references/custom-command-tool.md) for configured `tool: custom_command` command steps and flow-log events. Initialize its installed script path and runtime log from the plan's tool registry. Append stage/work entry/return, verification outcomes, checkpoints and user decisions through event mode; command steps capture stdout/stderr and exit codes through run mode. Save state before execution and retain existing gates and resume rules.

The root uses its own editable [root-workflow.yaml](assets/root-workflow.yaml) to manage event sequence, actions, checks, and checkpoints. Follow [root-configuration.md](references/root-configuration.md); its workflow events define root child execution order while the plan defines membership. Copy this file with the plan/leaves and validate edits before resuming.

Execute each work leaf through its editable `work_config` using [leaf-configuration.md](references/leaf-configuration.md). Copy the plan's `leaves/` directory into the project along with the plan. Each leaf has independent ordered actions, success checks, step skip/checkpoint flags, and commit/report skip overrides. Read changed configs at checkpoints and reconcile saved step results before continuing.

When the user wants to add a workflow to the existing hierarchy, invoke [workflow-tree-editor](../workflow-tree-editor/SKILL.md) at a saved checkpoint. It reviews the proposed insertion, validates the plan, preserves resume/history, and uses the existing commit/report chain. Return to the parent only after its editing work is complete; do not automatically execute the new stage.

Enter through the `add-platform` root using [entrypoint-and-skips.md](references/entrypoint-and-skips.md) and the editable [workflow-plan.yaml](assets/workflow-plan.yaml). Every child workflow, work unit, and commit child has its own `skippable` flag. Load policy on start/resume and at checkpoints; offer Skip only where permitted and record its scope/dependency impact.

When adding a platform to a project with multiple applications or custom build commands, follow [nested-workflows.md](references/nested-workflows.md) for parent/child execution and checkpoint control, then [add-platform-workflow.md](references/add-platform-workflow.md) for stage procedures. A parent enters one child at a time and resumes after that child's result is saved. These are nested workflows within this skill, not separately installed skills or background agents.

Use [bringup-session.yaml](assets/bringup-session.yaml) to save the active workflow stack, checkpoints, decisions, and results. By default, ask Continue / Pause / Stop at each child boundary and meaningful child milestone; wait for an answer before starting dependent work. Preserve the project's existing build interface rather than introducing a parallel command system.

Read [work-units.md](references/work-units.md) to divide every leaf stage into verifiable work units. On a failed criterion, save state and wait for user intervention; reverify after the user fixes it. After each successful unit, invoke the companion [git-work-commit skill](../git-work-commit/SKILL.md) to create and verify a scoped signed-off commit before offering the next unit. Install the companion skill folders together. Parent workflows aggregate results and child commits.

## Establish the platform

Every workflow-created commit runs the companion [commit-update-report skill](../commit-update-report/SKILL.md) as a commit child, writing a verified SHA-specific `.txt` update before returning to the parent. Install all six supplied skill folders together, including editor, reset and help. Reporting is local artifact generation and does not recursively commit its own output.

Read [assessment.md](references/assessment.md) for a new platform or uncertain baseline. Copy [platform-profile.yaml](assets/platform-profile.yaml) into the application workspace and fill it from inspected sources and hardware documentation. Keep unknown values explicit; do not invent pins, clocks, memory ranges, or electrical characteristics.

Inspect the application's manifest, Zephyr revision, board target, overlays, configuration fragments, and existing build instructions. Use documentation matching the pinned release; `latest` documentation is a discovery aid, not a compatibility guarantee. Preserve vendor SDK conventions where the application depends on them.

## Choose the scope

- Existing supported board: prefer application overlays and configuration fragments for application-specific peripherals and behavior.
- Custom board on a supported SoC: read [board-porting.md](references/board-porting.md). Derive from a close board in the same Zephyr revision, then reconcile every hardware difference.
- Unsupported SoC or missing driver: identify that dependency explicitly and scope the SoC or driver work before treating it as a board-only port.

Keep board hardware descriptions separate from application policy. Explain pin multiplexing, clock, interrupt, partition, and runner choices using hardware or repository evidence.

## Bring up incrementally

Start with a clean minimal build and boot console; add one peripheral or subsystem at a time. Inspect generated devicetree and Kconfig when debugging configuration rather than relying only on source files. For each failure, record the observed symptom, the suspected layer, and the next discriminating check.

Read [verification.md](references/verification.md) to select checks and record results. Flash only the intended device with the confirmed runner and memory layout. Avoid mass erase, fuse writes, protection changes, or provisioning unless explicitly in scope. Do not claim hardware verification when only compilation or simulation was performed.

## Collect and hand off

Run the standard-library-only collector against an existing build:

```text
python scripts/collect-build-evidence.py --build-dir <build> --output <new-evidence-directory> --label <board-target> --log <build-log>
```

The script copies diagnostic artifacts and records hashes, missing artifacts, and selected CMake metadata. Repeat `--log` for explicit build or serial logs. It does not build, flash, or infer that a build passed. For sysbuild, collect each domain's build directory separately and retain the parent domain mapping.

Deliver the profile, source changes, exact commands and exit codes, evidence location, verified capabilities, and remaining blockers. Logs and configuration may contain paths or credentials; review evidence before sharing externally.
