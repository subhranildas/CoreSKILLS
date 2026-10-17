# Use the interactive workflow

## Protect the library and choose the application

Workflow runs treat this entire skill repository and installed skill definitions as read-only. Select a separate firmware repository and use its project-owned bringup directory for state, editable configs, build evidence, reports and snapshots. The library can be read from Codex, but it is never a run destination. See [workspace boundaries](../../zephyr-platform-bringup/references/workspace-boundaries.md). External tools still need a read-only mount/permission profile for OS-level enforcement.

## On-demand help and reset

```text
Use $workflow-help. I am new; explain setup and how to start safely.
Use $workflow-help to explain the pending checkpoint in <session-path>.
Use $workflow-reset to restart <session-path>; preserve configs and source.
```

Help reads and explains without moving workflow state. Reset reviews the scope, archives old state, and starts a new execution record or reopens a selected subtree. Source changes, Git commits, reports/evidence, and editable configs are preserved. Reset does not run git reset/clean, erase hardware or reset this library. After reset, Continue is still required to start work.

## Start a platform addition

Open the application repository after [setup](setup.md). Mention `$zephyr-platform-bringup` through the CLI/IDE skill selector, or select the skill in your client. A plain prompt naming the skill and its path also makes the intended workflow explicit.

Example prompt; replace names and hardware details with your own:

```text
Use $zephyr-platform-bringup to add platform beta to this project.
The project has multiple applications and custom build commands.
Inspect the existing commands and platform definitions first.
Use alpha as a reference if it is compatible with the new hardware.
Initially support the sensor application in debug and release variants.
Guide me interactively through unresolved hardware and product decisions.
Preserve the current command interface and record the session in
bringup/beta/bringup-session.yaml and platform-profile.yaml.
Build verification is in scope; hardware is not available yet.
```

If application names or the reference platform are unknown, omit those sentences. Codex should discover existing choices and ask which combinations you need. You do not need to invent a new build command before starting.

## Run one workflow independently

To turn work off during development, edit `execution_profile.disabled` in your project plan. For example, `hardware: {reason: Board unavailable}` disables that subtree. Disabled work is recorded separately from passed/skipped work; unresolved dependencies block execution. See [development profiles](../../zephyr-platform-bringup/references/execution-profiles.md) for configuration, previews and resume rules.

Select an existing node ID to run just that workflow, subworkflow, or work leaf:

```text
Use $zephyr-platform-bringup in scoped mode: run only register for beta.
Use a separate session/log. Inspect prerequisites and stop before siblings.
```

For one build instance:

```text
Use $zephyr-platform-bringup to run only build-combination for sensor,
platform beta, variant debug. Keep success checks and commit/report review.
```

Preview the exact selection without executing anything:

```text
python -B .agents/skills/zephyr-platform-bringup/scripts/select-workflow.py bringup/beta/workflow-plan.yaml --node register
python -B .agents/skills/zephyr-platform-bringup/scripts/select-workflow.py bringup/beta/workflow-plan.yaml --list
```

Scoped sessions live separately and preserve a parent run's checkpoint. Outside-scope prerequisites need verified existing inputs or explicit intervention; they are never silently executed. Selecting a leaf includes its commit/report children, and selection completes only that scope. Use [scoped execution rules](../../zephyr-platform-bringup/references/scoped-execution.md) for instance filters and resume behavior.

## What happens in sequence

| Stage | Codex does | You provide when unresolved |
| --- | --- | --- |
| Discover | Trace wrappers, registries, variants, outputs, and CI | New platform identity and application scope |
| Assess | Inspect pinned source/toolchain and compare hardware | Hardware revision, schematics, missing wiring facts |
| Contract | Record selected combinations and public commands | Product choices and acceptance criteria |
| Integrate | Add required board and application configuration | Facts blocking a hardware-dependent change |
| Register | Extend existing custom command mappings | Decisions where several interfaces are plausible |
| Build | Run selected commands, collect evidence, check affected existing combinations | Environment prerequisites that are unavailable |
| Hardware | Verify boot and required peripheral behavior | Intended device/probe and hardware availability |
| Handoff | Report supported combinations and remaining blockers | Any revised scope |

The parent runs children sequentially, and a child can enter its own children. At each stage boundary and meaningful milestone, Codex saves a checkpoint and asks Continue / Pause / Stop. Answers are recorded and reused. Dependent work waits for Continue; Pause and Stop end workflow work while preserving the resume point. Unverified pins, memory ranges, and device identities remain explicit unknowns.

## Nested workflows and checkpoint control

With full execution, invoking the bringup skill starts the `add-platform` root. Scoped execution schedules only the selected subtree. On a new session, Codex copies `workflow-plan.yaml` into the project's bringup records. Each workflow, work unit, and generated commit child has an editable `skippable: true` or `false` entry. Missing flags default to false. The plan is policy; the session is execution state.

Set true to permit Skip, false to require the work when its parent executes. True does not skip automatically. Defaults permit skips for hardware verification, existing board support work, optional peripheral integration, help/CI, and regression work; core discovery, scope, command integration, builds, handoff, and commit children default to required. Actual dependency/acceptance checks still apply.

At a permitted checkpoint, choose Skip and provide a reason. Skipping a parent excludes its pending descendants, even when a descendant would be required if that parent ran. Skips remain visible in handoff and never become passed results. To change policy later, edit your project's plan or say:

```text
Make hardware non-skippable and keep boot-check skippable.
Reload the plan and explain any previously skipped work that must reopen.
```

Policy is reloaded at checkpoints and resume. Skipped prerequisites may block dependent work; skipping hardware cannot satisfy a hardware acceptance criterion. Commit skips require explicitly changing that child's default false flag and are reported as work completed without a commit. See [full skip rules](../../zephyr-platform-bringup/references/entrypoint-and-skips.md).

The parent runs discovery/assessment, then integration, then verification, then handoff. Verification contains individual build and hardware children. Each child returns its result to the parent before the next child starts. See [nested workflow rules](../../zephyr-platform-bringup/references/nested-workflows.md).

Example starting prompt:

```text
Use $zephyr-platform-bringup to add beta. Run nested workflows in
checkpointed mode. Start with discovery. At each child boundary and
meaningful milestone, save the session and ask Continue, Pause, or Stop.
Use bringup/beta/bringup-session.yaml as the durable record.
```

Say `Continue` to execute the proposed next milestone, `Pause` to save and wait, or `Stop` to end this run while preserving changes. Neither Pause nor Stop undoes completed work. A generic resume request first reviews the saved state and asks whether to proceed. To explicitly authorize a known milestone, say:

```text
Resume bringup/beta/bringup-session.yaml and continue the saved
register-platform milestone. Keep checkpointed mode for later children.
```

The session stores the active parent/child stack, child outcomes, pending question, command state, and history. After an interruption, Codex checks unknown command outcomes and stale inputs before proceeding. This is a conversational workflow backed by files; it is not a background scheduler or an automatic multi-agent system.

## Work units, failures, and commits

Each leaf workflow is divided into work units with explicit checks. For example, command registration contains mapping, dispatch/rejection verification, and help/CI updates. Build verification contains one unit per selected application/platform/variant. See [the work-unit criteria](../../zephyr-platform-bringup/references/work-units.md).

The unit sequence is:

```text
Execute -> verify success criteria
  Fail/blocked -> save -> user intervenes -> reverify
  Pass -> report -> candidate review <-> revise/recheck
       -> accept candidate -> commit/verify -> txt update report
       -> accept result -> refresh report -> Continue/Pause/Stop
```

When a check fails, Codex explains the expected and observed result, points to evidence, and asks you to investigate. Fix it yourself and reply `Fixed, continue`, or ask Codex to help. Codex reruns the failed check and any checks affected by the fix before proceeding. A bare Continue does not override a failure.

Each successful unit gets a scoped commit with `Signed-off-by`, repository message conventions, and validation details. Signoff is a trailer, distinct from a cryptographic signature; configured signing and hooks are preserved. Missing identity, hook failures, or unclear ownership pause for intervention. Commits stay local unless pushing is explicitly requested.

The commit child repeats review rounds until you are satisfied, with no fixed limit. Review the patch and full message, request changes as needed, then reply `Accept and commit`. After the commit is verified, reply `Accept result` to return to the parent. Pause/Stop and resume work during either review. Changed candidates need renewed acceptance; the skill does not assume silence means yes. Corrections after commit normally become reviewed follow-up commits; amending history needs explicit authorization. See [commit review rules](../../git-work-commit/references/review-loop.md).

For units without code changes, Codex commits a concise work report. Failed attempts are saved but do not receive a success commit. Parent workflows reuse child commit results without creating empty rollup commits. The live session records the SHA afterward and may remain modified; a commit cannot include its own SHA.

Example prompt:

```text
Use $zephyr-platform-bringup with its companion git-work-commit skill.
Divide each stage into work units with observable success criteria.
On failure, save the session and wait for me to investigate and fix it.
After I reply, reverify before continuing. Commit each successful unit
with signoff, then ask Continue/Pause/Stop for the next unit.
```

## Per-commit update reports

Install all six companion skill folders, including `commit-update-report`. After every primary or correction commit, Codex generates `bringup/<platform>/updates/<full-sha>.txt` containing the actual change summary, author/committer/signoff, success criteria, checks and evidence, review state, blockers, and next action. It refreshes acceptance state after your answer.

The report child defaults to `skippable: false`, with an editable entry like other children. Report generation/verification failures pause for intervention. Resume retries reporting for the existing SHA rather than creating another commit. An explicitly permitted skip is disclosed as a missing report.

These post-commit reports are local artifacts and are not automatically committed, which prevents an endless report/commit cycle. Transfer them with your live session when moving machines. Pre-commit work reports remain part of their work commits.

## Customize the top-level sequence

Copy `root-workflow.yaml` beside your project's plan and `leaves/` directory. The root node points to it using `workflow_config`. Edit its ordered `steps` to change startup, child-workflow order, local actions, checks, dependencies, and checkpoints.

The default events are initialize -> discovery -> integration -> verification -> handoff -> finalize. Workflow events reference direct child IDs. Every root child must appear once; the root's plan `children` list is membership while this file defines event order. Reordering also requires compatible dependencies; skipping cannot bypass required criteria.

```text
Use $workflow-tree-editor to customize my root-workflow.yaml.
Guide me through event order, dependencies, checks and checkpoints.
Show the proposed sequence and saved-progress impact before applying it.
```

Root event state and config identity are saved for resume. Changes reopen affected results while retaining valid completed work. See [root configuration rules](../../zephyr-platform-bringup/references/root-configuration.md). The same plan validator checks root and leaf configs.

## Customize individual leaves

Build configs now resolve the command explicitly, then Codex executes it. Before execution, the following readiness check must pass (ordinary plan validation permits unresolved future commands):

```text
python -B .agents/skills/workflow-tree-editor/scripts/validate-workflow-plan.py --leaf-config bringup/beta/leaves/build-combination.yaml --work-id build-combination --require-ready --step perform
```

Immutable snapshots preserve definitions for comparing resume changes. Editor approval covers all original/candidate files; independent config edits require new review. Older plans require [explicit migration](../../workflow-tree-editor/references/migration.md), not merely a schema-number change.

Each of the 18 work leaves has its own file under the plan's `leaves/` directory, linked through `work_config`. Copy that directory together with the plan into your project's bringup records. Edit the project files to define unique steps rather than changing a shared procedure for all work.

You can add/remove/reorder steps, choose inspect/edit/command/ask/manual/skill actions, supply commands and inputs, and edit each step's skip flag, success checks, evidence locations, and checkpoint setting. Leaf-specific commit/report skip overrides are also available. See [the format and command example](../../zephyr-platform-bringup/references/leaf-configuration.md).

The starting configs use descriptive actions; fill in project-specific commands and measurable checks before execution. Commands are inspected and run by Codex, not automatically evaluated by YAML. Configs reload at checkpoints/resume; edited steps invalidate affected results and refresh the next checkpoint. One leaf remains one commit boundary; use separate leaves if each step needs its own commit.

```text
Customize leaves/build-combination.yaml for my beta sensor build.
Ask me about the command, ordered steps, success checks and checkpoints.
Preserve other leaves and show the config diff before applying it.
```

## Add a workflow to the tree

Use the companion `workflow-tree-editor` skill to extend your project's existing plan:

```text
Use $workflow-tree-editor to add a resource-analysis workflow under
verification, after build-matrix and before hardware. Guide me through
its work units, success criteria, skip flags, and dependencies. Show
the proposed tree and diff before applying it. Preserve saved progress.
```

The editor inspects the tree, asks for unresolved choices, and repeats proposal review until you approve. Each added workflow/work has an explicit editable skip flag; new work retains failure intervention, interactive commits, and per-commit txt reports. The insertion is committed as one definition change after validation; the future workflow work is not executed during editing.

Pause/Stop preserves the draft in a separate edit record. Resume with its path:

```text
Use $workflow-tree-editor and resume bringup/beta/workflow-edit-session.yaml.
```

After application, existing history/commits remain intact and newly required work is pending. Changed plan files invalidate old candidate approval. The editor returns to the parent checkpoint after its commit/report completes.

Validate a plan manually (requires PyYAML):

```text
python -B .agents/skills/workflow-tree-editor/scripts/validate-workflow-plan.py bringup/beta/workflow-plan.yaml
```

The validator checks structure and dependency ordering; Codex also reviews the meaning of criteria and the accessible procedures. Editing session records and plan backups should travel with the live bringup session.

## Understand the two records

`platform-profile.yaml` describes the hardware, source baseline, and baseline build. `bringup-session.yaml` describes the workflow state and each application/platform/variant combination. Copy the supplied assets before editing them; keep the original templates reusable.

For each combination, keep the exact public command, working directory, shell, environment variable names, output directory, build result, exit code, and evidence location. Store credentials outside these records. YAML command fields are documentation, not a task runner.

## Run and log a custom command

The runner now preserves raw output bytes in `raw_base64` fields; choose a text encoding with `--encoding` when UTF-8 is inappropriate. It validates existing logs and quarantines incomplete tails before appending. Output draining after parent exit is bounded by `--drain-timeout`; incomplete capture returns 125 and requires intervention even if the child exited successfully. See the tool reference for recovery details.

Build leaves now bind `tool: custom_command` to the plan's CLI runner. It captures the workflow path, run/work/step/attempt IDs, argv, timestamps, output and exit code in the run's `workflow-flow.log`.

From your application repository, try:

```text
python -B .agents/skills/zephyr-platform-bringup/scripts/run-custom-command.py run --application-root . --runtime-root bringup/beta --cwd . --log bringup/beta/workflow-flow.log --run-id beta-run-001 --workflow-path add-platform/verification/build-matrix --work-id build.sensor.beta.debug --step-id perform --attempt-id command-001 -- python -c "print('Custom command example')"
```

Replace the argv after `--` with your custom build command. The runner executes it once and returns its exit code. Codex records checkpoints/decisions in the same log through event mode; it does not log conversations automatically. Reports reference this flow log and evidence collection can copy it. See [tool usage and event example](../../zephyr-platform-bringup/references/custom-command-tool.md).

## Collect evidence manually

Run this after a build, from the application repository. These examples assume repository installation and an existing `build/sensor-beta-debug` directory:

```text
python -B .agents/skills/zephyr-platform-bringup/scripts/collect-build-evidence.py --build-dir build/sensor-beta-debug --output bringup/beta/evidence/sensor-debug-001 --label sensor-beta-debug --log bringup/beta/logs/sensor-debug.log
```

The log must already exist. Omit `--log` if you have none; repeat it to include additional logs. Quote paths containing spaces. Choose a fresh evidence directory outside the build directory each time. Add `--include-images` if the bundle should contain the ELF/HEX/BIN files as well as their hashes.

The collector writes `evidence.json`, copies configuration/diagnostic artifacts and supplied logs, and lists expected files that are missing. It never infers build success, executes a custom command, or flashes a device. Record the build command's exit code separately in the session. Partial and stale build outputs can be collected, so associate every run with its source revision and actual command result.

For sysbuild, collect each domain directory separately and retain the parent domain mapping. Build success, simulator success, and verified behavior on physical hardware are distinct results.

## Resume or move to another machine

Snapshot manifests now use root-relative file/target/snapshot paths. Copy the associated tree and explicitly relocate each manifest:

```text
python -B .agents/skills/workflow-tree-editor/scripts/file-state.py relocate <old-manifest.json> --root <new-application-root> --output <new-manifest.json>
```

Relocation verifies copied content and link targets, but invalidates pending editor/commit approvals. Update session paths/boundaries and review the new mappings before mutations. Old absolute-path manifests require explicit migration/recapture. Readiness checks use `--step` so future unresolved commands do not block the current step. Commit recovery matches run/work/attempt trailers plus the saved parent, preventing reset runs from reusing old attempts. Effective child skip policy uses the leaf override when set, otherwise its plan template.

Transfer the source changes, session/profile records, and any needed evidence through your normal repository/artifact process. Recreate the pinned SDK and module environment on the new machine. Update machine-specific working directories, probe IDs, and paths; do not transfer local credentials.

Start a new Codex conversation in the application workspace:

```text
Use $zephyr-platform-bringup and resume from
bringup/beta/bringup-session.yaml. Read the platform profile too.
Compare the recorded source and toolchain with this machine's state.
Reuse settled decisions, identify stale evidence, and continue from the
earliest affected stage. Hardware verification is still pending.
```

The session record carries the workflow context without requiring the original chat. A changed revision, toolchain, target, or configuration can require affected checks to run again.

## Hardware follow-up

Once software integration is ready, identify the hardware and scope explicitly:

```text
Resume beta bringup. The intended beta revision B board is connected
through probe <device-id>. Flashing this device and checking boot,
GPIO, and the required sensor are in scope. Record the flashed image
hash and runtime evidence. Do not perform mass erase or provisioning.
```

Replace the probe placeholder with a real identity before execution. Platform support is complete only when the agreed acceptance criteria are met; a build-only milestone can finish with hardware checks clearly pending.

## Troubleshooting

| Symptom | Next check |
| --- | --- |
| Skill missing | Verify discovery location, complete folder copy, access, and restart if needed |
| Skill found but helper missing | Check for copied `scripts`, `references`, and `assets` directories |
| Python command missing | Use the available launcher and ensure Python is at least 3.9 |
| Custom command unavailable | Confirm working directory, environment setup, wrapper path, and required tools |
| Wrong configuration in output | Check command dispatch, exact target, fragments, overlays, and cached build directory |
| Collector refuses output | Choose a new directory that neither contains nor sits inside the build directory |
| Build passes but board fails | Verify flashed image identity, runner, boot layout, reset procedure, and console wiring |
| Remote run cannot see probe | Perform hardware verification on a host with configured device access |

For the full agent procedure, see [the workflow reference](../../zephyr-platform-bringup/references/add-platform-workflow.md).
