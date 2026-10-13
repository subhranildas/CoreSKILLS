# Top-level entry and editable skip policy

## Start everything through the parent

The root's `workflow_config` supplies the authoritative event order through [root configuration](root-configuration.md). Copy `root-workflow.yaml` with the plan and leaves. Validate its child membership and effective dependency order; do not schedule from the root's membership list alone.

Every work node's `work_config` defines its independent editable steps. Copy `assets/leaves/` beside the project plan and apply [leaf execution rules](leaf-configuration.md). Schema-version-2 plans require a valid config for every work leaf. Copy the leaf template for new work; preserve existing project configs on resume. Runtime step results/cursors belong in the session.

Invoking `zephyr-platform-bringup` defaults to the `add-platform` root, but an explicit selected workflow/subworkflow/work leaf uses [scoped execution](scoped-execution.md) and stops at that selection's return. Bootstrap boundaries/configs/prerequisites still apply. Read the execution/work-unit rules and copy the plan/session/profile into project records for a new run. Preserve existing records on resume; selection does not rewrite the plan root or skip siblings.

Load the plan before selecting work. Check unique IDs, valid parent/child references, an acyclic tree, and explicit Boolean `skippable` on every workflow/work entry. Expand per-combination/peripheral entries with unique IDs and their own copied `skippable` fields. Instantiate a commit child for each executed successful work, also with its own explicit `skippable`. Convert each criterion to a specific verification procedure before execution.

Show the planned hierarchy and required/optional work. Start the requested first unit; afterward use checkpoints. The full root or scoped coordinator schedules only its permitted sequence; children return results and never start siblings independently.

For each actual commit SHA, instantiate the plan's report-child template under the commit child with its own explicit `skippable` flag, default false. Skipping a permitted report child records the missing report and reason. Skipping a commit produces no SHA and requires no per-commit report.

## Policy fields on every entry

```yaml
id: hardware
parent_id: verification
kind: workflow
skippable: true
```

`skippable: false` means a Skip request is rejected with an explanation and offers Continue/Pause/Stop. `true` enables Skip as an additional choice; it is not a skip result or an instruction to skip automatically. Missing flags are treated as false until materialized explicitly. Defaults in the bundled plan are starting choices, not fixed project requirements.

At a skippable checkpoint, offer Continue / Skip / Pause / Stop. When asked to skip, record the node/unit ID, reason, user decision, source policy value, timestamp, and acceptance impact. If the reason is missing, ask for it. Skipped work has `outcome: skipped`, never `passed`, and no fabricated measurements or success commit.

Skipping a workflow excludes its pending descendants from scheduling and records them as skipped with `inherited_from` pointing to the ancestor. Their own flags remain unchanged; a non-skippable child is required when its parent executes, but does not override an explicit permitted skip of the whole parent. Preserve already completed descendants and their commits. Skipping does not revert partially completed work; identify retained changes and block any unsafe dependent use.

Check dependencies before advancing. A skipped prerequisite does not satisfy another unit's required input or criterion. Reuse independently verified equivalent evidence, or ask for an explicit scope/plan adjustment; otherwise enter intervention. For example, skipping hardware allows a build-only milestone, but cannot satisfy an agreed requirement to verify sensor behavior on a board. Deferred checks remain visible as pending scope, and the parent cannot claim full bringup completion.

## Change policy later

To add a workflow or subtree, use the companion [workflow-tree-editor](../../workflow-tree-editor/SKILL.md). It edits the project plan through an interactive proposal and apply cycle, retaining success criteria, failure intervention, commit/report children, and saved progress. A new required child reopens its completed parent; adding it never fabricates an executed result.

Optional `depends_on` lists reference nodes whose valid results must be complete before entry. They must finish earlier in the ordered traversal and cannot reference ancestors/descendants/self. Resolve expanded entries to concrete session prerequisites. Missing or skipped dependencies pause for intervention, even when their position precedes the active node.

Edit `skippable` in the project's plan or ask Codex: “Make boot-check non-skippable.” Do not edit status/outcome to simulate execution. Codex reloads the plan at checkpoints and on resume, records the policy diff in session history, and mirrors flags into instantiated records. A pending question based on an old flag must be refreshed before consuming a Skip answer. Reject malformed policy rather than guessing.

Changing true to false after a skip reopens the required work and invalidates dependent completion as appropriate. Changing false to true enables the option but does not skip anything until requested. Completed valid results remain reusable. Changing a parent's policy does not silently rewrite each child's flag.

The root defaults to non-skippable; skipping it, if the user explicitly changes its flag, means no work runs and is recorded as a skipped run, not a successful bringup. Commit children default to non-skippable. If their flag is explicitly changed and a commit child is skipped, record `commit.status: skipped`, no SHA, and `completed_without_commit` for the work result. This is an explicit exception to the per-work commit policy and must be disclosed in handoff; do not report a signed-off commit that does not exist. Review acceptance/signoff requirements still apply to any commit that actually runs.

For older sessions without a plan, create one reflecting the saved scope and stage, preserve historical results, and materialize flags before continuing. This is file-backed Codex orchestration, not an executable scheduler.
