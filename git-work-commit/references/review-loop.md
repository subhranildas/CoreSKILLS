# Interactive commit review until accepted

This is an unbounded conversational review loop, not a busy loop or a series of automatic commits. Wait for feedback at each round. Silence never means acceptance. Parent Continue authorizes preparation of a candidate, not committing an unseen candidate under this user-requested policy.

## Candidate review

1. Prepare the exact owned patch, full message including expected signoff, identities, and validation results. Save round number, HEAD, intended paths, patch/message artifact paths and SHA-256 hashes. Keep review artifacts outside the proposed commit unless they are intended deliverables. Preserve earlier feedback and hashes in history.
2. Show the reviewable diff or an accessible diff artifact, complete message, identities/signoff, validation summary, and any excluded unrelated work. Ask: “Accept and commit this candidate, request changes, pause, or stop?” Save `awaiting_review` and wait.
3. For requested revisions, change only the requested content, update the work report, and rerun affected criteria. Failed validation enters user intervention; do not silently weaken criteria. Present the revised candidate as another round. Repeat without an arbitrary round limit.
4. On explicit acceptance, save the accepted round and hashes. Immediately before committing, recheck HEAD, exact patch, message, identities, and validation inputs. Material changes invalidate acceptance and require another round. Ambiguous acceptance requires a focused clarification.
5. Create the accepted commit using the commit skill, verify it, and record its SHA. Hooks that change actual content or the message require affected checks and review of the actual result.

## Result acceptance

After every created or recovered primary/correction commit, run `commit-update-report` and verify the SHA-specific `.txt` file before asking for result acceptance. Show its path with the commit result. Refresh the report when acceptance or correction state changes. A report failure is an intervention gate, even when the Git commit already succeeded; resume reporting without recreating the commit. Explicit permitted report skips remain disclosed.

Show the actual SHA, full final message, diff, and verification results. Ask: “Accept this result and return to the parent, request a correction, pause, or stop?” Save `awaiting_result_acceptance`. Only explicit acceptance of the verified result completes the commit child and allows the parent to offer its next work unit.

If the user requests a correction after commit, enter another candidate review round. Default to a scoped follow-up correction commit, preserving existing history. Track every resulting SHA under the work unit. Message-only corrections that require amending history need explicit authorization for that specific commit; never infer permission to rewrite history or force-push from dissatisfaction. Present the correction strategy and candidate before execution. Acceptance of a correct existing result ends the loop without another commit; do not manufacture changes.

## Pause, stop, failure, and resume

Persist create/amend mode and the expected parent list with the accepted candidate. Create recovery uses the saved previous HEAD; explicitly authorized amend recovery uses the replaced commit's parent list and `amended_from`. Never substitute the old HEAD for an amended commit's parents. Comma-separated expected parent SHAs support preserved merge ancestry; `none` represents an initial commit. Legacy records without mode/parent metadata require inspection and intervention, not guessed recovery.

Pause/Stop saves the current round, pending question, candidate artifacts, history, and existing SHAs, then ends workflow work. Neither action removes completed commits or discards changes. No reply leaves the saved question pending without polling.

Commit or verification failure enters `awaiting_intervention`; preserve evidence and await user input. Recover only the saved run/work/commit-attempt tuple and expected parent with `verify-recovery.py`, then verify candidate patch/signoff/checks. A work-ID-only match or an old reset attempt is not sufficient. Never duplicate a verified same-attempt commit merely because its success was not saved.

On resume, reconcile the saved review with current HEAD, candidate artifacts, user edits, identities, checks, and existing commits. Reuse feedback; changed content needs renewed candidate acceptance. A verified commit awaiting result acceptance resumes at the result question, not commit creation. A request to resume does not itself accept the saved candidate/result unless the user's instruction clearly says so.
