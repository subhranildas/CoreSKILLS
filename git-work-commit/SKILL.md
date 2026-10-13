---
name: git-work-commit
description: Interactively review and revise a validated work unit's patch and commit message until the user accepts, then create and verify a scoped signed-off Git commit with resumable review state.
---

# Commit a validated work unit

## Runtime workspace boundary

Read [workspace-boundaries.md](../zephyr-platform-bringup/references/workspace-boundaries.md) before any run mutation. This repository and installed skill definitions are read-only during execution. Resolve the separate application/runtime roots and saved protected roots; check every destination with the boundary helper. Templates, edits, reports, snapshots and commits target project copies only. If this library is selected as the application, stop and request a separate application path. Use `python -B` for library helpers.


Use after a work unit passes its recorded success criteria. Inputs are the target repository, work ID, owned changes, validation results, and work report. Return the commit SHA, subject, signoff identity, committed paths, and verification result. Do not push unless separately requested.

## Prepare

When nested, consume the instantiated child's effective `skippable` and policy source from the session, not the template flag alone: a non-null leaf completion override takes precedence; null inherits the plan template. The parent resolves it with `workflow-policy.py`, saves it before entry, and refreshes it on policy edits. For standalone use, use the review record's flag. Offer Skip only if the effective flag is true and explicitly requested; record its reason and return `skipped` with no SHA. Pause/Stop do not imply Skip. Executed commits still require acceptance and signoff.

First read [the interactive review loop](references/review-loop.md). There is no fixed round limit: revise and recheck until the user explicitly accepts the candidate, then create the commit and obtain acceptance of the verified result before returning success. Pause and Stop remain available. Parent automatic progression does not bypass commit review. Save state in the parent unit's `commit.review` or use [commit-review.yaml](assets/commit-review.yaml) for standalone use. The commit creation instructions below apply only to an explicitly accepted, unchanged candidate.

Inspect repository instructions and contribution guidance, branch/HEAD, `git status --short`, staged/unstaged diffs, and recent commit subjects. Confirm this is the intended Git repository. If there is no repository, a merge conflict, ambiguous ownership, or missing committer identity, save the blocker and request user intervention. Do not initialize a repository or change identity merely to bypass the blocker.

Use `git var GIT_AUTHOR_IDENT` and `git var GIT_COMMITTER_IDENT` to check the actual identities, including environment overrides. Use the configured identity; never invent a name, email, signoff, or coauthor. The workflow user's request for signed-off commits authorizes adding the configured committer's signoff; unresolved contributor requirements still need clarification.

Check that criteria were actually verified and that the intended patch matches the tested content. Material edits since validation require affected checks again. For assessment or hardware-only work, commit a concise work report containing the observations and evidence references. Exclude credentials, generated build trees, and large firmware/log files unless the repository explicitly tracks them.

## Scope and message

Save a unique run ID, concrete work ID (including expanded combination), and commit attempt ID before creation. Each primary/correction/amendment attempt has a distinct ID; interruption/resume retains the same attempt, while reset creates a new run. Include `Workflow-Run`, `Workflow-Work`, and `Workflow-Attempt` trailers in the reviewed message alongside signoff. Standalone use creates a run identity too. Existing legacy commits lacking these trailers are historical evidence, never automatic recovery candidates.

Before creation save `commit_mode` and `expected_parents`: a normal commit uses `[head_before]` (or [] for an unborn branch); an explicitly authorized amend saves `amended_from: head_before` and that original commit's actual parent list, not head_before itself. Record the specific amend authorization. The reviewed candidate binds this metadata.

For interrupted recovery, use `scripts/verify-recovery.py` with run/work/attempt, `--mode create|amend`, and the saved parent list in `--expected-parent` (comma-separated full SHAs, or `none`). Amend mode also requires `--amended-from <original-sha>`, verifies its parent list and a new candidate SHA, and never grants amendment authorization itself. Then verify candidate patch/signoff/checks before result acceptance. Work-ID-only matches or ambiguous evidence require intervention.

Stage explicit paths or selected hunks belonging to the work. Never use `git add .`, `git add -A`, or `git commit -a` for this workflow. Existing staged user changes must remain out of this commit. If unrelated staged paths exist, a reviewed explicit-path `git commit --only` can preserve them; if the same file mixes owned and unrelated changes, isolate reviewed hunks with an appropriate index method or ask for intervention. Do not silently unstage, overwrite, or commit others' work.

Inspect the exact proposed commit diff and whitespace checks. Write the message to a temporary file outside tracked work. Follow repository conventions; otherwise use a concise imperative subject and a body explaining the concrete change and validation. Include the work ID in the body for recovery. Do not claim tests passed if they were not run.

Create the commit with `git commit --signoff --file <message-file>` using the reviewed index, or the reviewed explicit-path `--only` mode. Preserve hooks and configured cryptographic signing. Do not bypass failed hooks with `--no-verify` or disable signing. `--signoff` adds a committer trailer; it is distinct from cryptographic signing with `-S`. Honor any repository requirement for both. See [Git commit documentation](https://git-scm.com/docs/git-commit).

## Verify and return

For every actual primary/correction commit, invoke the companion [commit-update-report skill](../commit-update-report/SKILL.md) before presenting result acceptance. Record and verify its `<full-sha>.txt` artifact; refresh it after user acceptance or a correction decision. Report failures pause for intervention. Install this skill alongside the commit and bringup skills. Report generation is a child workflow with its own editable `skippable: false` default, and never creates another commit.

Confirm the command exit code and inspect the new commit's SHA, full message, author/committer identities, parent, and actual diff. Verify the expected `Signed-off-by` trailer and exact intended paths/content. Check signature verification when repository policy requires a cryptographic signature. Confirm unrelated changes remain preserved.

If hooks changed committed content, rerun affected criteria before declaring success. If commit creation or verification fails, return a blocker and wait for intervention; do not automatically amend or rewrite history. Inspect HEAD and the work ID before retrying an interrupted commit to avoid duplicates.

Create one primary commit per successful leaf work unit, plus explicitly requested correction commits when needed. Return success only after technical verification and user result acceptance. Parents aggregate accepted child commits and do not create empty rollup commits. For a work unit with no source changes, its report supplies a meaningful commit. If neither changes nor a new report exists, record `no_changes` and ask the parent to resolve scope rather than fabricate an empty commit.
