# Editable execution for every leaf

The plan defines hierarchy, ordering, dependencies, and node skip flags. Each `kind: work` node points to its own `work_config` YAML file, relative to the plan directory. Copy the plan **and its `leaves/` directory** into the application. Edit the project copies. The bundled files supply distinct starting instructions; they are not configured hardware/build commands.

## What you can edit

Each leaf config defines inputs, ordered steps, action instructions or commands, step-level skip flags, dependencies, success checks, evidence outputs, interaction checkpoints, and completion child overrides. Use [leaf-work.yaml](../assets/leaf-work.yaml) as the template for a new leaf. Existing configs are in `assets/leaves/`.

Example custom build step:

```yaml
id: build
action: command
skippable: false
depends_on: []
instructions: Build the selected application with the project's public wrapper
command:
  argv: [python, build.py, --app, sensor, --platform, beta, --variant, debug]
  shell: null
  shell_command: null
  working_directory: .
  environment_variable_names: []
success_checks:
  - id: successful-build
    expected: Build exits zero and produces the selected domain ELF
    verification: Record exit code and verify the expected ELF belongs to this run
    evidence: [build.log, build/sensor-beta-debug/zephyr/zephyr.elf]
checkpoint_after: true
```

`argv` is preferred when an executable accepts arguments directly. If shell syntax is actually needed, use `shell_command` and an explicit `shell` instead; never both forms. Commands are inspected and executed by Codex, not evaluated automatically from YAML. List environment variable names, not credentials. Resolve relative working/evidence paths against the application repository, not the installed skill directory. Inputs are recorded values, not executable template expressions; ask for unresolved required inputs before using them.

Supported actions are `inspect`, `edit`, `command`, `ask`, `manual`, and `skill`. Instructions describe the specific work. A skill action names the accessible skill in `skill`. Manual actions wait for user observations, clearly distinguishing reported measurements from independently checked results. An ask action records the answer and validates it against its stated check.

## Execution and policy

`tool: custom_command` binds a command step to the plan's tool registry and [logged CLI runner](custom-command-tool.md). Resolve the underlying command as usual, then wrap it with the runner using saved application/runtime/context values. Do not execute both the wrapper and underlying command separately. Without a tool binding the command uses the ordinary inspected execution path. Tool IDs must exist in the plan; direct leaf validation checks syntax and plan validation checks registry membership.

Readiness checks target the current step and its transitive prerequisites using `--require-ready --step <current-step-id>`. Future command inputs may remain unresolved until their own resolution step. Root events use `--root-config <path> --workflow-id <root-id> --require-ready --step <event-id>`. All definitions still receive structural validation; readiness does not assert checks passed or execute commands.

Build leaves start with `resolve-command`, followed by a `command` action referencing `inputs.build_command` through `command_ref`. Codex resolves and inspects the invocation into the project config; null is unresolved and cannot run. Before the command step, run the validator with `--leaf-config <config> --work-id <base-work-id> --require-ready`; failure blocks execution. Plan validation checks structure, not readiness of future commands. Repeated combinations keep distinct resolved project configs/input identities; never overwrite another instance's command.

Execute steps in list order. `depends_on` may refer only to earlier step IDs in the same leaf; plan-level dependencies connect other leaves/workflows. Each step has explicit `skippable`, at least one observable `success_checks` entry, and explicit Boolean `checkpoint_after`. Skipping a step never satisfies its checks or dependencies. The leaf's aggregate criterion must still be met by valid evidence or an explicitly revised scope.

After each step verify its checks. Failure enters user intervention regardless of checkpoint settings. A successful step with `checkpoint_after: true` offers Continue/Skip-if-permitted/Pause/Stop before the next step. At leaf completion, verify the plan's aggregate criterion; passing isolated steps alone is insufficient.

`completion.commit` and `completion.update_report` can override their child skip flags per leaf; `null` inherits the plan templates and true/false overrides them. Other commit/report rules, including review acceptance and signoff, remain in their skills. Inner steps do not automatically make separate commits: the leaf commits once after success, plus requested corrections. To give a step its own commit boundary, turn it into a separate work leaf with the editor.

Resolve each effective flag with `scripts/workflow-policy.py` before child entry and persist the value plus `policy_source`. Children use that saved effective policy exclusively. Editing an override/template invalidates pending Skip choices and requires recomputation; policy changes never silently skip or retroactively approve work.

## Safe edits and resume

Before adopting a revision, snapshot its full bytes using the companion editor's `scripts/file-state.py capture`. Record immutable snapshot paths/hashes in session history and each step attempt for the plan, root/leaf configs and referenced procedures. Compare edits against saved content, not just hashes. Keep prior snapshots. Missing/corrupt historical content marks affected results stale and requires intervention rather than assumed reuse. Snapshot definitions only, not credentials or secret-bearing environment values.

Reload and validate a config at leaf entry, each checkpoint, and resume. Store config SHA-256, step cursor, resolved nonsecret inputs, step results/evidence, skips, and history in the session. Track step input/config identity, not just the leaf ID. A running operation must reach a safe boundary before adopting edited instructions.

When a config changes, compare old/new steps by ID and content. Reuse unchanged valid results; mark edited steps and affected downstream steps stale. Inserting/reordering a step before completed work may reopen that work. Do not automatically weaken acceptance, skip a failed check, or reuse commit approval for a changed patch. Show the impact and refreshed checkpoint before continuing. Preserve previous attempts and commits.

The workflow editor creates/edits leaf configs as part of the reviewed proposal and validates them with the candidate plan. Config changes are source changes eligible for the normal reviewed commit. Runtime result fields belong in the session, not the editable definition. This is a Codex-driven configuration format, not a standalone task executor.
