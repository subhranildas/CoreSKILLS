# Interactive workflow: add a platform

## Sequence and interaction

Use this sequence: discover commands → assess target → define supported combinations → integrate hardware → register commands → verify builds → verify hardware → hand off.

Apply [nested-workflows.md](nested-workflows.md) to execute these stages as children of the add-platform parent. Read the named resource when entering its stage. Ask focused questions for missing decisions and reuse answers across stages. At checkpoints, save state and ask Continue / Pause / Stop; dependent work waits for an explicit answer. Independent inspection may continue while an information question is pending, but no workflow work continues after Pause or Stop. If a decision changes downstream assumptions, invalidate the affected results and resume from that stage.

Keep a session record using `assets/bringup-session.yaml` and one platform profile using `assets/platform-profile.yaml`. Store them in the project's established documentation/configuration location; if none exists, use a clearly named bringup directory. Record commands as data, not executable session content.

## 1. Discover the existing build interface

Inspect repository instructions, build wrappers, task runners, manifests, application directories, platform registries, and CI. Trace each public custom command to its underlying build invocation. Do not execute an unfamiliar wrapper before inspecting its side effects.

Produce a compact matrix with application, platform, variant, public command, working directory, required environment variable names, build output directory, and definition location. Record unsupported combinations explicitly. Distinguish platform identifiers accepted by wrappers from Zephyr board targets and hardware revisions.

Identify where a new platform must be registered and whether commands also flash, erase, provision, download, or publish. Preserve quoting and shell semantics; do not split arbitrary command text on whitespace or run session strings through `eval`.

If the repository does not resolve the target, ask: “What is the new platform name and exact board/SoC or hardware revision?” Present discovered applications and ask which must support it. Do not ask the user to restate command details already found in source.

Exit: known command entry points, candidate reference platform, and target application list.

## 2. Assess the target

Read [assessment.md](assessment.md). Fill the platform profile from the pinned source and hardware evidence. Compare the candidate reference platform with the new one: SoC/core, memory, boot chain, peripherals, toolchain, and application requirements.

Ask only unresolved hardware questions that block the next change, such as console wiring or bootloader ownership. Missing optional peripherals can remain blocked while minimal compilation proceeds. For unknown memory or electrical values, obtain evidence before using them.

Exit: supported-board, custom-board, or SoC/driver-work classification; explicit unknowns; smallest bringup milestone.

## 3. Define the application/platform contract

Show the proposed combinations, using the existing command interface. For example, a discovered `python build.py --app sensor --platform alpha --variant debug` interface might gain `--platform beta`; this is an illustration, not a mandated command shape.

For each selected combination, record:

- Application, platform identifier, exact board target, and variant.
- Public command, shell, working directory, environment prerequisites, and output directory.
- Configuration fragments, overlays, sysbuild domains, and expected artifacts.
- Required capabilities and measurable acceptance criteria.

Ask about ambiguous product choices: “Should the new platform support both sensor and gateway, or sensor only?” If only one combination is established by the request and source, proceed and state that assumption. Do not silently enable every application on the new hardware.

Exit: decided scope and build contract. A platform added for one application need not become globally supported.

## 4. Integrate hardware and application configuration

Read [board-porting.md](board-porting.md). Add only the board/SoC/driver changes required by the classification. Reuse shared configuration where hardware and policy match; keep application-specific overlays and features scoped to their application/platform pair.

Obtain a minimal build before layering in required peripherals. If the project supplies a smoke application, use its custom command. Otherwise use a suitable sample with the same board roots and toolchain, recording why a direct build is needed.

Exit: target discovery and minimal compilation, or a precisely identified blocking dependency. Boot can remain pending when hardware is unavailable.

## 5. Register the platform in custom commands

Extend the existing registry, wrapper, presets, or task definitions at their established extension points. Preserve existing defaults and existing public commands. Keep board target, application configuration, and build directory mapping consistent with the contract.

Unsupported application/platform combinations should produce a clear failure before building. Avoid shared cached build directories across different combinations unless the existing wrapper deliberately cleans or reconfigures them. Do not add an automatic flash or erase step to a build-only command.

Update help and CI matrix entries where the repository maintains them. Check command selection, argument forwarding, and unsupported-combination behavior with the project's existing tests or a safe dry run when supported. Do not assume a wrapper supports `--dry-run`.

Exit: reviewable source changes and exact public commands for the new combinations.

## 6. Verify the application build matrix

Read [verification.md](verification.md). Build each agreed combination through the public custom command, using its specified working directory and environment. Capture command, exit code, log, output path, and image identity for each run.

Use `scripts/collect-build-evidence.py` separately for each build/domain. Its `--label` can identify the application/platform/variant/run; keep exit codes in the session result. Separate run evidence directories prevent overwrites.

Check representative existing combinations affected by shared wrapper or configuration edits. Expand regression coverage only where the change warrants it. For a failure, identify the layer and save an intervention checkpoint; wait for the user to fix it or request Codex's help, then rerun affected checks. Do not repeatedly rebuild an unchanged external dependency failure.

Exit: each requested combination is passed, failed, blocked, or not run with a reason. Compilation does not establish hardware support.

## 7. Verify on hardware interactively

Use the verification reference to check boot and required capabilities. If device identity or hardware access is unresolved, ask for the device/probe and readiness for the hardware step. Reuse explicit authorization already given for flashing the intended device.

Run one bringup milestone at a time and use observed results to select the next check. Record serial logs, flashed image hashes, cold-reset behavior, and peripheral measurements. When hardware is unavailable, finish the software integration and clearly leave hardware checks pending rather than claiming full bringup.

Exit: evidence-backed runtime results or specific pending hardware work.

## 8. Hand off and resume

Present the supported combinations, commands, changed registration/configuration files, validation results, and remaining blockers. Mark the session complete only when agreed acceptance criteria are satisfied. A software-only request may complete with hardware checks explicitly out of scope.

On resume, read the session and inspect current source revisions and build outputs. Reuse recorded decisions, but rerun evidence made stale by source, toolchain, target, or configuration changes. Start at the earliest affected stage; do not repeat settled questions.
