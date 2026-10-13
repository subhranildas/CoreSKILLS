# Nested workflow execution and resume

## Execution model

An explicitly selected subtree uses [scoped execution](scoped-execution.md), with a coordinator limited to that selection. Ancestors are context/prerequisite sources rather than scheduled stages. Normal child/work-unit rules still apply, and the coordinator stops when the selected result returns.

Start and select children through [the root entry and skip policy](entrypoint-and-skips.md). The editable plan defines each node's `skippable` flag. The required-success and commit rules below apply to executed required work; explicit permitted skips are recorded separately and never count as passed criteria.

The `add-platform` parent enters child workflows sequentially using the procedures in [add-platform-workflow.md](add-platform-workflow.md):

```text
add-platform
  discovery-and-assessment
    discover
    assess
    contract
  platform-integration
    integrate
    register
  verification
    build-matrix
      build one application/platform/variant at a time
    hardware (if in scope)
      boot
      required peripheral checks
  handoff
```

“Spawn” means enter a child procedure in the current conversation. This instruction does not launch agents, new chats, or a scheduler. The user can request those separately. Child workflows may have their own children; only the active leaf performs work. Parents wait for a saved child result before selecting the next child.

## Child contract

For every leaf, apply [work-units.md](work-units.md): decompose it into work units with explicit success criteria and a commit child. Required unit completion means both verified criteria and a verified signed-off commit. Parents wait for all required units, not just the last command's result.

Before entering a child, record its unique ID, parent ID, procedure reference, scope, inputs, next milestone, and acceptance conditions in `workflow.nodes`. Use unique IDs for repeated builds, such as `build.sensor.beta.debug`. Record input versions: source revision and dirty state, toolchain identity, target, and relevant configuration. Do not treat a commit alone as proof that uncommitted inputs are unchanged.

Append the node ID to `workflow.active_stack` in root-to-leaf order. The child returns a saved result containing outcome, evidence, changed files, unresolved questions, blockers, and next action. Outcomes are `passed`, `failed`, `blocked`, or `skipped`; skipped requires a recorded scope decision and cannot satisfy a required check.

A failed attempt is recorded as an outcome; the required child remains `awaiting_intervention` until the user fixes the issue and verification succeeds, or chooses Pause/Stop. A parent may advance only when required children and their commits are complete. Optional work may be skipped by an explicit scope choice. Do not mark the overall session complete until the agreed acceptance criteria are met.

## Interactive checkpoints

Default `interaction_mode` is `checkpointed`. Checkpoint after each successful work unit's commit and before starting the next unit or sibling. A failed check instead creates an intervention checkpoint immediately. Combine coincident checkpoints into one question. Do not interrupt for every file edit or routine command.

Finish the currently authorized milestone and prepare a reviewable result before asking. Persist the checkpoint before presenting it. Show the result, evidence, unresolved issues, and exact next milestone, then ask:

> Discovery is complete. The next step is assessing beta's hardware and toolchain. Continue, pause here, or stop this session?

Use a question tool available in the host, or a direct question at the end of the turn when none is available. A new session begins with the user's requested first milestone; asking to start the workflow authorizes that milestone. For a checkpoint awaiting an answer:

- **Continue:** Save the answer, clear the pending checkpoint, and run only the stated next milestone. It does not approve unrelated side effects.
- **Pause:** Save `session.status: paused` and `workflow.status: paused`, retain the stack/cursor, report the session path and resume instruction, and end workflow work.
- **Stop:** Save `session.status: stopped` and `workflow.status: stopped`, retain changes and evidence, and end workflow work. Stop does not roll back changes or delete records. It may later be resumed by explicit request.
- **No answer:** Keep `awaiting_input`; do not interpret elapsed time as Continue.

Answers to hardware or scope questions do not implicitly answer a pending Continue checkpoint unless the user's intent is clear. Preserve previous execution authorizations while respecting this user-requested pacing. If the user explicitly switches to automatic progression, record `interaction_mode: automatic`; keep unresolved-input and actual execution-permission checks, and restore checkpointed mode when requested.

## Save points and interruption

Write the session after decisions, milestone results, and child entry/return, and before each external command. For a command record the operation, inputs, log/output locations, and `execution_state: running`; afterward record its exit code and result. Maintain a chronological `workflow.history` with checkpoint IDs and responses. Never store secrets.

Use a temporary sibling file and replace the session file after a successful write when tooling allows. Keep a single writer for a session. If saving fails, report it and stop before starting the next operation; do not claim that a resume point exists.

If Pause/Stop arrives during a command, stop scheduling further commands. Terminate the active command only when the host supports doing so safely; a flash already underway may need to finish to avoid corrupting the device. Record its actual state and explain any operation still running. A saved `running` entry after an interrupted conversation is an unknown outcome, not evidence of success.

## Resume algorithm

1. Read the saved session, plan, and profile. Upgrade older records by preserving existing data and adding missing policy/work-unit/review/report fields; initialize the stack at the recorded stage without inventing passed criteria or commits. Preserve historical results; apply current policies to new/resumed units.
2. Inspect source/configuration/toolchain identity and output/log locations. Resolve interrupted operation state from available evidence. Never automatically repeat a flash, erase, provisioning, or publishing action with unknown outcome.
3. Mark affected results stale when inputs changed. Preserve prior evidence/history and choose the earliest affected node. For a completed valid child, reuse its result rather than rerunning it.
4. Show the saved checkpoint, active child, completed results, stale results, and proposed next milestone. An explicit request to resume and perform that milestone authorizes it; a generic resume request gets a Continue / Pause / Stop checkpoint before execution.
5. Save the resumed state and continue at the active unit. An unresolved failure resumes at revalidation after user intervention; an interrupted commit resumes with commit recovery. Once a child returns, its parent consumes the result and offers the next checkpoint. Do not restart the entire parent unless its inputs require it.

Workflow state is descriptive YAML maintained by Codex. This bundle is not a durable workflow engine: it requires an active Codex session and accessible project records. It does not wake itself or resume background work automatically.
