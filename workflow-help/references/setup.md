# Set up on Windows, macOS, or Linux

## Prerequisites

- A working Codex installation with access to the application repository and a terminal execution environment.
- Local copies of all six skill folders: `zephyr-platform-bringup`, `git-work-commit`, `commit-update-report`, `workflow-tree-editor`, `workflow-reset`, and `workflow-help`.
- An initialized application Git repository with the user's correct author/committer identity, and any signing tools required by that repository.
- Python 3.9 or newer to run helpers. The evidence collector uses only the standard library; the workflow editor validator also requires PyYAML (`python -m pip install PyYAML` in the chosen environment).
- For builds: the target project's required Zephyr/vendor SDK, modules, compiler, and build tools. Follow its pinned setup instructions.
- For hardware verification: the runner tools, probe drivers, serial access, and target hardware required by the project.

Use the [official Codex CLI guide](https://learn.chatgpt.com/docs/codex/cli) or your installed Codex client's setup instructions to install and sign in. Skill installation does not install the firmware toolchain.

## Choose a skill location

Codex discovers repository skills in `.agents/skills` and personal skills in `~/.agents/skills`. Explicit invocation uses `$` in Codex CLI/IDE; the desktop selector may use `@`. Restart Codex if a copied skill does not appear. These conventions follow [official skill documentation](https://learn.chatgpt.com/docs/build-skills), checked on 2026-10-12.

Choose one location to avoid duplicate skill names:

| Scope | Destination | Use |
| --- | --- | --- |
| Repository | `<application-repo>/.agents/skills/zephyr-platform-bringup` | Team workflow, optionally committed with the application |
| Personal | `<user-home>/.agents/skills/zephyr-platform-bringup` | Reuse across application repositories |

The folders at this project's root are distribution sources. Keeping them there alone does not place them in a discovery directory. Copy all six complete folders into the same skill parent, not just their `SKILL.md` files.

## Windows: PowerShell

Replace the two example paths. This installs into the application repository:

```powershell
$skillsSource = 'C:\path\to\CoreSIILLS'
$applicationRepo = 'C:\path\to\firmware'
$skillParent = Join-Path $applicationRepo '.agents\skills'
foreach ($skillName in @('zephyr-platform-bringup', 'git-work-commit', 'commit-update-report', 'workflow-tree-editor', 'workflow-reset', 'workflow-help')) {
  if (Test-Path -LiteralPath (Join-Path $skillParent $skillName)) { throw 'Skill already exists; review it before updating.' }
}
New-Item -ItemType Directory -Path $skillParent -Force | Out-Null
foreach ($skillName in @('zephyr-platform-bringup', 'git-work-commit', 'commit-update-report', 'workflow-tree-editor', 'workflow-reset', 'workflow-help')) {
  Copy-Item -LiteralPath (Join-Path $skillsSource $skillName) -Destination (Join-Path $skillParent $skillName) -Recurse
}
```

For personal installation, replace the `$skillParent` assignment with:

```powershell
$skillParent = Join-Path ([Environment]::GetFolderPath('UserProfile')) '.agents\skills'
```

## macOS/Linux: bash or zsh

Replace the example paths:

```bash
skills_source='/path/to/CoreSIILLS'
application_repo='/path/to/firmware'
skill_parent="$application_repo/.agents/skills"
if [ -e "$skill_parent/zephyr-platform-bringup" ] || [ -e "$skill_parent/git-work-commit" ] || [ -e "$skill_parent/commit-update-report" ] || [ -e "$skill_parent/workflow-tree-editor" ] || [ -e "$skill_parent/workflow-reset" ] || [ -e "$skill_parent/workflow-help" ]; then
  echo 'Skill already exists; review it before updating.'
else
  mkdir -p "$skill_parent"
  for skill_name in zephyr-platform-bringup git-work-commit commit-update-report workflow-tree-editor workflow-reset workflow-help; do
    cp -R "$skills_source/$skill_name" "$skill_parent/$skill_name"
  done
fi
```

For personal installation, use `skill_parent="$HOME/.agents/skills"` before the existence check.

## Open the application workspace

Open the firmware repository in your Codex client. With the CLI, change to that repository and run `codex`. Run it in the same environment that can execute the custom build commands.

For WSL or containers, install the skill where that environment can read it and use paths valid inside that environment. Confirm that its compiler, Python, and build outputs are accessible there. USB/debugger access is a separate hardware setup step.

Check Python and the collector without building anything:

```text
python --version
python -B .agents/skills/zephyr-platform-bringup/scripts/collect-build-evidence.py --help
```

Use `python3` on macOS/Linux or `py -3` on Windows if that is the installed launcher. For a personal installation, substitute its full script path.

## Check that Codex can use it

Send this prompt:

```text
Use the zephyr-platform-bringup skill. Confirm git-work-commit and
commit-update-report, workflow-tree-editor, workflow-reset and workflow-help are accessible and summarize the workflow gates. Do not change
the application yet.
```

If discovery fails, give Codex the absolute path to the installed `SKILL.md` and ask it to read that file and follow its linked workflow. Check for an extra nested folder, missing references/assets, disabled skill settings, and access restrictions.

## Updates and remote environments

Review changes in the distribution source, then update the installed copy deliberately. Preserve edited project session/profile files separately; they should live in the application project, not inside the installed templates. Avoid merging old and new copies blindly, which can leave obsolete files.

For remote execution, make the skill and application available on the execution host and install the required build environment there. Without target-device access, complete assessment and build verification and leave hardware results pending. This bundle is a standalone local skill, not an installable plugin package.
