# Work units, success criteria, and failure intervention

Every leaf stage must be divided into concrete work units before execution. Each unit belongs to one workflow node and has a unique ID, prerequisites, owned files, a verifiable success criterion, verification procedure, report path, and next unit. Choose a size that produces a meaningful reviewable result and commit. Do not make each command or file edit a work unit.

Use the following starting decomposition and adapt it to the actual project. Expand rows per application, variant, domain, or required peripheral where needed. A scope decision must be recorded before dropping a required unit.

| Stage | Work units | Success criteria |
| --- | --- | --- |
| Discover | Inventory applications/platforms; trace custom commands | Matrix lists supported combinations and each public command maps to inspected definitions, target, and output path |
| Assess | Pin source/toolchain; reconcile hardware | Revisions/tool requirements are recorded; hardware values needed for the next unit have cited evidence; unresolved dependencies have an explicit disposition |
| Contract | Select supported combinations; define acceptance | User scope is captured; each combination has an executable command contract and observable pass criteria |
| Integrate | Add/discover board target; minimal compile; integrate each required peripheral | Target is discoverable; minimal build exits zero with expected configuration; each peripheral's configuration check passes, without claiming unperformed runtime tests |
| Register | Add command mapping; verify dispatch and rejection; update help/CI | New mapping resolves correctly, unsupported combinations fail clearly, and affected existing mappings retain expected behavior |
| Build | Build each combination; check affected regressions | Command exits zero, expected artifacts exist, generated config matches contract, and associated evidence is captured |
| Hardware | Flash/boot; test each required capability | Intended image/device are identified; boot signature and each capability meet measured acceptance thresholds |
| Handoff | Reconcile results; publish local handoff report | All agreed criteria are satisfied or explicitly removed from scope; commands, evidence, limitations, and commits are traceable |

## Unit lifecycle

Before executing a unit, apply its explicit `skippable` flag and [skip policy](entrypoint-and-skips.md). An allowed skip records the reason and acceptance/dependency impact instead of executing or creating a success commit. Commit children have their own flags, default false; an explicitly permitted commit skip is disclosed as `completed_without_commit`, an exception to the default lifecycle below.

1. Save the unit's criterion before starting. Specify what will be observed, how, and where its evidence goes. For example: “sensor/beta/debug public command exits 0, produces the intended domain ELF, and generated DTS enables the sensor at its documented address.” Avoid “works” or “looks correct.”
2. Perform only the authorized unit, then execute its verification. Save observations, exit codes, and evidence; criteria are `pending`, `pass`, `fail`, or `blocked`.
3. If any required criterion fails or cannot be checked, enter `awaiting_intervention`. Save the failure, affected unit, diagnostic evidence, user action needed, and exact recheck. Stop scheduling workflow work, including commits and dependent units. Do not silently repair and retry in this mode.
4. Explain the failure and ask the user to investigate/fix it and reply when ready, or choose Pause/Stop. User reports of a fix are a cue to reverify, not proof of success. If the user requests Codex's help fixing it, act within that request, preserve the failure history, then rerun the criterion. Otherwise wait while the user fixes it.
5. On `fixed, continue`, inspect changed inputs and rerun the failed criterion plus affected previous checks. Persist another failure and wait if the check still fails. Never bypass the gate on a bare Continue. A changed acceptance criterion requires an explicit recorded scope decision, not an automatic weakening of the test.
6. When criteria pass, write the unit report and enter its commit child using [git-work-commit](../../git-work-commit/SKILL.md). The companion skill must be installed alongside this skill, or its supplied path must be accessible. If unavailable, ask to restore it; do not mark the unit complete without its required commit.
7. The commit skill loops through candidate review and revisions until accepted, creates/verifies the commit, then waits for user acceptance of the result. Only after that acceptance record SHA/signoff/result, mark the unit completed, return to the parent, and offer Continue/Pause/Stop for the next unit. Commit failure is also an intervention gate. Automatic progression does not disable failure gates, commit review, or required commits.

Each successful leaf unit produces a signed-off commit, including discovery and measurement units: commit their concise reports when they have no code changes. Failed attempts remain saved in the session; this policy commits after success rather than publishing failed implementation as complete.

## Reports and commit bookkeeping

The pre-commit work report is distinct from the post-commit `.txt` update. Each actual primary/correction SHA runs `commit-update-report` before commit-child completion, then refreshes acceptance state as needed. Store verified report paths/hashes per SHA. Post-commit reports are local artifacts excluded from automatic staging, so reporting never triggers recursive commits. A report failure pauses at reporting, not at repeating a successful commit.

Create a project report such as `bringup/<platform>/work/<work-id>.md` with scope, criteria, inputs, observed verification results, evidence references, and owned changes. Include a portable, sanitized session snapshot through that unit's passed criteria when needed for cross-machine resume. Large logs and firmware can remain external with hashes/locations in the report.

Commit the report with the unit's validated changes. Then write its commit SHA into the live session. A commit cannot contain its own SHA; do not create a second bookkeeping commit or amend endlessly. The live session may therefore remain modified after a successful unit. Preserve it on transfer; prior reports/snapshots and Git history can recover the last committed success if the live session is lost.

Record HEAD before commit, intended paths, run ID, concrete work ID, unique commit-attempt ID and `commit.status: running`. On interruption, verify that exact identity tuple and parent with the recovery helper, then the patch/signoff/checks. A verified same-attempt commit may satisfy creation but still needs result acceptance; other runs/attempts are historical only. User fixes may already be committed: record their SHAs and create the reviewed verification/report commit without amending user commits.

## Resume state

An existing verified commit completes the commit step only when user result acceptance is recorded. Resume pending candidate/result reviews without duplicating commits. Track primary and correction SHAs together; amendments require explicit authorization.

Keep work units under `workflow.work_units`, linked to nodes. The active stack can include the active unit and its commit child. Save attempts and interventions append-only. Resume at verification after a reported fix, or at commit recovery when a validated unit has an unknown commit outcome. Revalidate any checks made stale by user edits. Pause and Stop retain the active unit and unresolved intervention.
