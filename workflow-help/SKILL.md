---
name: workflow-help
description: Provide on-demand user guides for setup, full or scoped bringup runs, workflow configuration, custom CLI tools, checkpoints, commits/reports, resume, reset, and troubleshooting without changing execution state.
---

# On-demand workflow help

Read-only assistance: do not create sessions, edit configs, commit, install, reset, build or flash just to explain the workflow. Read relevant sibling skills and the user's selected project records when accessible. If no project/run is identified, explain the defaults rather than inventing an active state.

## Bundled user-guide routing

The full user guides are included with this skill; do not depend on the source repository's `docs/` being installed. Read only the sections needed for the question, using headings/search within the guide. For an overview, present a short topic menu before loading all detail.

| User question | Guide and sections |
| --- | --- |
| What is included? | [Overview](references/overview.md) |
| Install on Windows/macOS/Linux, personal/repo scope, prerequisites | [Setup](references/setup.md) |
| Explain the tree and how children return | [Workflow tree](references/workflow-tree.md) and user guide: What happens in sequence |
| Start a complete bringup | [User guide](references/user-guide.md): Protect the library; Start a platform addition |
| Run one workflow/subworkflow/leaf or select an instance | User guide: Run one workflow independently; [scoped execution](../zephyr-platform-bringup/references/scoped-execution.md) |
| Continue/Skip/Pause/Stop, optional versus required work | User guide: Nested workflows and checkpoint control |
| Temporarily disable work during development/testing | [Development execution profiles](../zephyr-platform-bringup/references/execution-profiles.md) |
| Success criteria, failed checks, user intervention | User guide: Work units, failures, and commits |
| Review loop, signoff, correction/amend, recovery | User guide: Work units, failures, and commits; [commit skill](../git-work-commit/SKILL.md) |
| Per-commit txt updates and report failures | User guide: Per-commit update reports; [report skill](../commit-update-report/SKILL.md) |
| Change root order, steps, criteria, flags, dependencies | User guide: Customize the top-level sequence; Customize individual leaves |
| Insert a new workflow interactively | User guide: Add a workflow to the tree; [editor skill](../workflow-tree-editor/SKILL.md) |
| Run custom commands, flow logs, raw output, encoding/drain settings | User guide: Run and log a custom command; [tool reference](../zephyr-platform-bringup/references/custom-command-tool.md) |
| Evidence artifacts, hashes, multiple domains | User guide: Collect evidence manually |
| Resume, reset, transfer machines, snapshots/migration | User guide: Resume or move to another machine; On-demand help and reset; [reset skill](../workflow-reset/SKILL.md) |
| Hardware follow-up and unverified capabilities | User guide: Hardware follow-up |
| Common errors or current checkpoint | User guide: Troubleshooting; inspect selected session read-only |

Use bundled guides for user-facing examples and the linked operational skills/references for precise current rules. If they disagree, explain the operational rule rather than copying stale examples. Future workflow capability changes should update these bundled guides and this routing table along with the public docs. Help never executes the commands shown as examples unless the user separately requests that action.

Offer the topic matching the question, or a short menu: getting started, tree/sequence, configuring root/leaves, Continue/Skip/Pause/Stop, failure intervention, commit review/reports, resume, reset, or current status. Ask one concise question if the topic is unclear. Explain required versus skippable steps and pending versus passed results in plain language.

For independent runs, explain [scoped execution](../zephyr-platform-bringup/references/scoped-execution.md), list/select valid node IDs read-only, and distinguish selected-scope completion from full bringup. Help previews never schedule the selected node.

For a new user, explain the read-only skill library, writable application and runtime records, then give an example starting prompt from the bundled setup/user guide. Consult [root config](../zephyr-platform-bringup/references/root-configuration.md), [leaf config](../zephyr-platform-bringup/references/leaf-configuration.md), and [workspace boundaries](../zephyr-platform-bringup/references/workspace-boundaries.md) for exact rules. Setup and usage guides are inside this skill's references, so help works when the six skill folders are installed without `docs/`.

For active-run help, summarize current node/step, last verified result, pending review/intervention, and exact next choices. Help does not consume the pending Continue/acceptance answer or move a cursor. Return to the unchanged checkpoint after answering. If the user explicitly asks for action, route to the appropriate bringup/editor/reset skill; do not treat a help question as execution approval.

Useful prompts:

```text
Use $workflow-help. I am new; explain how to start with my firmware repo.
Use $workflow-help to explain the checkpoint in <session-path>.
Use $workflow-help to explain reset versus reverting application changes.
```
