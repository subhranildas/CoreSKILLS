# Custom command and workflow-flow logging

`scripts/run-custom-command.py` is a standard-library CLI tool with two modes. `run` executes an explicit argv command, streams merged stdout/stderr, and appends structured UTF-8 JSON Lines to a `.log` file. `event` appends a checkpoint/decision/status entry without executing a command. All entries contain run, workflow path, work, step and command-attempt IDs and UTC timestamps.

## Example from the application repository

```text
python -B .agents/skills/zephyr-platform-bringup/scripts/run-custom-command.py run --application-root . --runtime-root bringup/beta --cwd . --log bringup/beta/workflow-flow.log --run-id beta-run-001 --workflow-path add-platform/verification/build-matrix --work-id build.sensor.beta.debug --step-id perform --attempt-id command-001 -- python -c "print('Custom command example')"
```

Replace the command after `--` with your public build wrapper. Arguments are passed literally, with `shell=False`. To use shell syntax, explicitly pass its executable and flags as the command, for example `powershell -NoProfile -Command <reviewed-command>` or `bash -lc <reviewed-command>`. Codex must inspect the command and its write destinations; this logger is not a sandbox.

Record a workflow checkpoint in the same file:

```text
python -B .agents/skills/zephyr-platform-bringup/scripts/run-custom-command.py event --application-root . --runtime-root bringup/beta --log bringup/beta/workflow-flow.log --run-id beta-run-001 --workflow-path add-platform/verification/build-matrix --work-id build.sensor.beta.debug --step-id perform --attempt-id command-001 --event awaiting_input --message "Build passed; waiting for Continue"
```

## Attach it to configured leaves

The plan's `tools.custom_command` entry points to this script and defines the default runtime-relative log path. During initialization, save the absolute accessible script path and log path in the session. Root/leaf checkpoints and user responses use event mode; run mode handles selected command steps. Lifecycle code is still driven by Codex, so the tool does not observe unreported conversational events automatically.

Build leaves include `tool: custom_command` on their `perform` step. For those steps, resolve the actual public build command as before, then invoke it **through this runner**, not twice. Convert a reviewed shell command into an explicit shell executable argv; do not evaluate strings from YAML. The runner's context uses the concrete expanded work ID and a unique **command** attempt ID, distinct from the commit attempt. Save run/attempt, log path, and operation state before executing it.

A `command_end` with child exit code zero, `capture_complete: true`, successful runner exit, and the step's artifact/check criteria is required for a pass. Nonzero exit goes to intervention. Code 125 includes incomplete output capture/tool failure, even when the child exited zero; 130 is interruption. Actual child failures retain their code, so classify outcomes using log event/fields as well as the numeric return. Reports reference the flow log; evidence collection copies it through `--log` at collection time.

Checkpoint and response logging failures also require intervention; do not claim complete flow coverage when an event was not recorded. Help queries need not log because help is read-only. Reset archives the previous log association and selects a new run-specific flow log; it never truncates the prior run log.

## Boundaries and recovery

Before appending, the runner validates complete JSONL records. An incomplete final record is preserved in a verified `.partial-<timestamp>` copy of the original log, then the valid prefix is restored and a `log_tail_quarantined` event records the archive. A valid final record missing only its newline receives that newline. Corruption in a complete record blocks execution without changing the log. Quarantine indicates historical events may be missing; reconcile prior attempts rather than claiming their success.

Output text defaults to UTF-8; use `--encoding cp1252` (or another text encoding) for the command's actual output. Every chunk also includes `raw_base64`, retaining original merged stdout/stderr bytes even if display decoding replaces invalid characters. Concatenate those decoded raw chunks to reconstruct exact captured bytes. Unknown/non-text codecs fail before launch.

The reader drains output for at most `--drain-timeout` seconds after the direct child exits (default 1 second). If an inherited pipe remains open or output cannot finish within that bound, the runner logs child exit plus `capture_complete: false`, returns 125, and requests intervention. It does not claim successful evidence or silently rerun/kill background descendants. Increase the drain bound deliberately for unusually large output; an active direct command is not limited by it.

The tool verifies application/cwd/runtime paths with the boundary helper and refuses a log inside the library or outside the runtime directory. Pass every additional saved `protected_root`. It records argv and output, but not environment variable values: keep credentials out of argv/output. Logs can contain sensitive application output; inspect before sharing.

A lock file prevents concurrent log writers. On interruption the tool attempts to stop the process; Windows descendants may remain and are reported as such. A crash may leave the lock or a missing terminal event. Reconcile process and output state before removing a stale lock or retrying; the tool does not auto-retry or replay commands. This example tool has no timeout or automatic process-tree supervisor. Use it for finite commands and preserve the existing safe handling for flashing operations that should not be interrupted.
