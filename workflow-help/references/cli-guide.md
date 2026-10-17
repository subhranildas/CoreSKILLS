# Native CoreSKILLS CLI

Experimental checkpoint: root-local events and workflow-return checks are not yet executed by this CLI; it currently schedules work leaves in selected order. Interrupted operations still require manual inspection and recovery, and per-leaf completion skip overrides are not yet implemented by the CLI. Use the skill-driven coordinator for the complete interactive workflow. The tests below cover the implemented lifecycle, not every full-bringup guarantee.

The Python CLI enforces lifecycle state changes and application-wide locking. Codex still interprets hardware requirements, performs edits/manual observations, and discusses choices. It does not automatically infer that descriptive checks passed or bypass user review.

## Install and preflight

From the library checkout, install with `python -m pip install -e .`. The `coreskills` entry is also available as `python -B -m coreskills` from this checkout. Wheels include the six sibling skill folders. Use `--library <path>` before a subcommand to select a source or installed library explicitly.

```text
coreskills doctor
coreskills tree
coreskills help usage
coreskills init --application /path/to/firmware --runtime /path/to/firmware/bringup/beta/run-001 --workflow inventory
coreskills doctor --session /path/to/firmware/bringup/beta/run-001/run.json
```

Initialization copies project definitions and creates a native `run.json` alongside editable YAML. Native schema 1 is distinct from the existing conversational session YAML; neither silently overwrites the other. Native commands only schedule the selected work scope. A full run can be initialized without `--workflow`; adapter expansion must be resolved before its expanded work executes.

## Lifecycle and evidence

```text
coreskills status --session <run.json>
coreskills run --session <run.json>
coreskills record-check --session <run.json> --check <check-id> --result pass --evidence <file>
coreskills record-criterion --session <run.json> --result pass --evidence <file>
coreskills pause --session <run.json>
coreskills resume --session <run.json>
coreskills resolve --session <run.json>
```

Inspect/edit/manual/ask/skill steps return the required action and checks. Codex or the user performs that action and records verifiable evidence; the CLI does not execute those descriptive actions itself. Command steps run inspected explicit argv through the logged command tool. Typed checks may automatically test exit code, file existence, hash, text content or a JSON numeric metric; descriptive checks still require observations.

A failed check blocks further work and review. After fixing it, resolve and run/recheck before recording a pass. Completing step checks is separate from passing the aggregate work criterion. Evidence hashes and config snapshots prevent accepting changed inputs silently. `reconcile` reopens the current work after config edits and clears its current check results; preserve any needed evidence before using it.

## Commit review

```text
coreskills review --session <run.json> --path <owned-file> --message "Describe the concrete change"
coreskills commit --session <run.json> --accept <exact-candidate-digest>
coreskills accept-result --session <run.json> --sha <verified-commit-sha>
```

Repeat review with the revised files/message until satisfied. Candidate acceptance binds explicit owned paths, content, Git identity and HEAD. The CLI refuses a preexisting staged index, preserves hooks/configured signing, and creates a signed-off commit with run/work/attempt trailers. It verifies the actual committed blobs, writes a txt update, then waits for result acceptance. Commits stay local. Report generation is not recursively committed.

Hooks, signing, unknown outcomes, or changed evidence enter intervention. Inspect those outcomes before retrying; the companion commit skill and recovery helper handle corrections/amendments with explicit authorization. The native CLI's commit command creates normal commits, never automatic amendments.

## Scope, prerequisites and reset

Scoped prerequisites can be supplied with `prerequisite --id <dependency> --evidence <file> --verification <inspection-description>`. They are inspected provenance claims, not proof that an outside workflow ran. Missing inputs block scheduling. `skip --reason <reason>` applies only to a ready skippable work unit and never counts as a passing dependency.

```text
coreskills reset --session <run.json> --confirm
```

Reset preserves project configs/source/commits, archives execution state, and starts fresh attempt identity in the same selection. Unknown operations block reset. To change a plan or scope, review it with the editor and initialize a new run rather than changing a live selected scope silently.

## Adapters, migrations, and docs

`init --adapter <yaml>` supplies repository-specific combinations, regressions, peripherals and capabilities. Each combination may carry an explicit command mapping. Without concrete rows, expanded work remains blocked instead of accepting an empty matrix.

```text
coreskills migrate --plan <old-plan.yaml> --application <firmware> --output <new-candidate-directory>
coreskills migrate --plan <old-plan.yaml> --application <firmware> --output <new-candidate-directory> --confirm
coreskills docs --output docs
coreskills docs --output docs --write
```

Migration previews first and writes validated candidate copies with an original backup; it never changes the input plan or imports unverified historic successes. Unknown schema versions are rejected. Documentation maintenance regenerates public guides from the canonical bundled help guides; it is an explicit source-maintenance command, never part of application workflow execution.

Application-wide locks serialize native mutation/command/commit/reset operations. External tools or manual editors must follow the same workspace discipline; these locks are not an operating-system sandbox. Stale locks are diagnosed, never automatically deleted. Library definitions remain read-only during runs.
