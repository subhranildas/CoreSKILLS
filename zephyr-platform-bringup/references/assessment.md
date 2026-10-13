# Platform assessment

Inspect the repository before selecting commands. Capture:

| Area | Evidence needed |
| --- | --- |
| Source baseline | Application commit and dirty state, manifest, Zephyr/vendor SDK revision, module revisions |
| Toolchain | Host, Python/west/CMake/Ninja versions, SDK and compiler versions |
| Target | Exact board target including qualifiers/revision, SoC, core, board hardware revision |
| Boot | Reset path, bootloader, image signing, load address, partition layout, multi-image dependencies |
| Hardware | Schematics, oscillator values, supply voltages, debugger, UART, pin mapping and peripheral wiring |
| Application | Required peripherals, configuration fragments, overlays, memory and timing constraints |
| Acceptance | Observable boot signature and measurable pass criteria for each required capability |

Classify every requirement as supported, needs application integration, needs board changes, needs driver/SoC work, or unknown. Identify the smallest useful milestone and the evidence needed to accept it.

Suggested sequence: toolchain and board discovery, minimal compile, console boot, GPIO, buses, storage, connectivity, application workload. Reorder to match the hardware: a board without an LED does not need blinky, and a console may require USB or RTT instead of UART.

Use `west boards`, `west build -h`, and checked-in build instructions to confirm target spelling and options in the installed version. Record the expanded build command, including CMake arguments, rather than just the sample name. When SDK setup is missing, report the missing component before changing the environment.

Authoritative starting points (select the matching release):

- [Application development](https://docs.zephyrproject.org/latest/develop/application/index.html)
- [West build, flash, and debug](https://docs.zephyrproject.org/latest/develop/west/build-flash-debug.html)
