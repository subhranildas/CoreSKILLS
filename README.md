# CoreSKILLS

Interactive Codex skills for Zephyr platform bringup, configurable workflows, scoped execution, signed-off commits, update reports, and CLI command logging.

## Included skills

- `zephyr-platform-bringup`: full or scoped bringup with editable root and leaf configurations.
- `git-work-commit`: iterative commit review, signoff, verification, and recovery.
- `commit-update-report`: per-commit plain-text update reports.
- `workflow-tree-editor`: interactive workflow insertion and configuration validation.
- `workflow-reset`: archive and restart execution while preserving source and commits.
- `workflow-help`: bundled on-demand setup, usage, and workflow-tree guides.

Start with [setup](docs/setup.md) and [usage](docs/usage.md), or invoke `$workflow-help` after installing all six skill folders.

The library is read-only during workflow execution. Run workflows in a separate application workspace; keep state, logs, reports, and editable project configurations there.

## Verification

Python 3.9+ and PyYAML are required for workflow validation. Git is required for commit-recovery integration tests.

```text
python -B zephyr-platform-bringup/tests/test_custom_command.py
python -B zephyr-platform-bringup/tests/test_scoped_execution.py
python -B workflow-tree-editor/tests/test_workflow_validation.py
python -B workflow-tree-editor/scripts/validate-workflow-plan.py zephyr-platform-bringup/assets/workflow-plan.yaml
```
