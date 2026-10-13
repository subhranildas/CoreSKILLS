# Zephyr platform bringup with Codex

This project contains bringup, commit, and commit-update-report skills for adding a platform to a Zephyr project that has several applications and custom build commands. They guide Codex through interactive decisions, verified work units, signed-off commits, and plain-text updates while preserving the project's build interface.

Start here:

For interactive assistance, invoke `$workflow-help`. Its bundled [user guide](../workflow-help/references/user-guide.md), [setup guide](../workflow-help/references/setup.md), and [tree guide](../workflow-help/references/workflow-tree.md) cover the whole flow even when only the six skill folders are installed.

1. [Set up on your machine](setup.md): install the skill for one repository or your user account.
2. [Run the workflow](usage.md): start, answer questions, collect evidence, and resume on another machine.

## What is included

| File | Purpose |
| --- | --- |
| [SKILL.md](../zephyr-platform-bringup/SKILL.md) | Skill entry point and routing |
| [add-platform-workflow.md](../zephyr-platform-bringup/references/add-platform-workflow.md) | Interactive sequence for multiple applications and custom commands |
| [nested-workflows.md](../zephyr-platform-bringup/references/nested-workflows.md) | Parent/child execution, Continue/Pause/Stop checkpoints, and resume |
| [work-units.md](../zephyr-platform-bringup/references/work-units.md) | Success criteria, user intervention on failure, and commit gates |
| [workflow-plan.yaml](../zephyr-platform-bringup/assets/workflow-plan.yaml) | Editable root hierarchy and skip flags for every work/workflow |
| [root-workflow.yaml](../zephyr-platform-bringup/assets/root-workflow.yaml) | Editable startup, stage sequence, checks, checkpoints, and finalization |
| [scoped-execution.md](../zephyr-platform-bringup/references/scoped-execution.md) | Run an individual workflow/subworkflow/work leaf without sibling execution |
| [leaf-configuration.md](../zephyr-platform-bringup/references/leaf-configuration.md) | Independent editable steps, commands, checks, and checkpoints for each leaf |
| [entrypoint-and-skips.md](../zephyr-platform-bringup/references/entrypoint-and-skips.md) | Starting the parent and changing skip policy |
| [git-work-commit/SKILL.md](../git-work-commit/SKILL.md) | Scoped, validated Git commits with signoff |
| [commit-update-report/SKILL.md](../commit-update-report/SKILL.md) | Verified plain-text update for every workflow-created commit |
| [workflow-tree-editor/SKILL.md](../workflow-tree-editor/SKILL.md) | Interactively insert workflows with validated placement and resume handling |
| [workflow-reset/SKILL.md](../workflow-reset/SKILL.md) | Archive/restart execution without reverting source or commits |
| [workflow-help/SKILL.md](../workflow-help/SKILL.md) | Read-only onboarding and checkpoint assistance on demand |
| [assessment.md](../zephyr-platform-bringup/references/assessment.md) | Source, toolchain, hardware, and acceptance assessment |
| [board-porting.md](../zephyr-platform-bringup/references/board-porting.md) | Board, devicetree, Kconfig, and application integration |
| [verification.md](../zephyr-platform-bringup/references/verification.md) | Build and hardware verification |
| [platform-profile.yaml](../zephyr-platform-bringup/assets/platform-profile.yaml) | Hardware and baseline build template |
| [bringup-session.yaml](../zephyr-platform-bringup/assets/bringup-session.yaml) | Decisions and results per application/platform/variant |
| [collect-build-evidence.py](../zephyr-platform-bringup/scripts/collect-build-evidence.py) | Collect existing build artifacts, logs, and hashes |
| [run-custom-command.py](../zephyr-platform-bringup/scripts/run-custom-command.py) | Execute custom commands and record workflow flow/output in JSONL logs |

Install all six supplied skill folders together. The bringup skill runs nested stages, invokes the commit skill after successful work, and generates a txt update for each resulting commit. References are loaded as needed; templates become project records. The Python script performs evidence collection only. No connector or external account integration is required by this bundle.

The instructions can be copied between machines. Actual builds still require the application's pinned toolchain and dependencies; hardware tests require access to the correct device.
