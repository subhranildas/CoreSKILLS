# Verification and evidence

Define acceptance before executing each check. Track `pass`, `fail`, `blocked`, or `not_run`; include command, exit code, hardware revision, image identity, observation, and evidence path.

| Stage | Checks | Acceptance evidence |
| --- | --- | --- |
| Build | Pristine configuration, expected target, dependency warnings, link/memory usage | Exit code plus build log, merged DTS, `.config`, map |
| Boot | Flash result, cold reset, console or debugger observation | Image hash, runner/probe, boot log and expected signature |
| GPIO | Polarity, input/output, interrupt handling | Measured state or documented observable response |
| Buses | Device readiness, known register/transaction, error paths | Transaction results; trace where needed |
| Storage | Read/write persistence, partition bounds, reset behavior | Test data and recovery observations |
| Connectivity | Link establishment, application traffic, reconnect | Logs and measured transfer behavior |
| Application | Required workload, resource use, watchdog/recovery | Requirement-specific measurements and pass thresholds |

Only run destructive storage tests on an explicitly selected disposable region. Match test voltages and wiring to documented hardware limits.

Example build command shape, adapted to the actual repository:

```text
west build -p always -b <exact-target> -d <build-dir> <application> -- <required-CMake-options>
west flash -d <build-dir>
```

Capture shell exit codes immediately. A serial log alone does not establish which image was flashed. Record image hashes and the boot/reset procedure. Investigate faults with the same ELF used on the device.

Use Twister for existing sample or ztest coverage when appropriate. A build-only run proves compilation; hardware or simulator execution must be reported separately. Select tests supported by the target, inspect skips, and preserve Twister reports. Confirm CLI options through the installed version's help before using device-testing or hardware-map options.

For sysbuild, preserve the domain mapping and capture each domain's configuration and image identity. The collector accepts one build directory at a time. It records artifacts present at collection time, including partial or stale builds; pair it with the command log and exit code.

Handoff should state the reproducible build command, pinned revisions/toolchain, verified requirement results, known failures, untested capabilities, and next action for each blocker.

Source: [Twister test runner](https://docs.zephyrproject.org/latest/develop/twister/index.html).
