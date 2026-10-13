# Board and application integration

Use the hardware model supported by the pinned Zephyr tree. Do not transplant a current board layout into an older release unchanged. Inspect a nearby in-tree board for exact naming and required files.

## Hardware description

For a custom board, reconcile SoC variant, cores, flash/RAM, oscillator sources, pinctrl, console, debug interface, and boot configuration against schematics and datasheets. Define board identity, targets, revisions, devicetree, defaults, and runner support using that release's conventions. Preserve licensing for reused files.

For out-of-tree boards, expose the directory through the application's established `BOARD_ROOT` or module mechanism. Verify discovery from a clean build. A root is the parent containing `boards/`, not the board directory itself. Follow release-specific conventions for SoC and devicetree roots if those are also external.

## Devicetree and Kconfig

- Describe wiring and enabled devices in devicetree; use bindings with the required properties and compatible strings.
- Put application wiring additions in overlays when they are not fixed board hardware.
- Reconcile pinctrl, GPIO polarity, interrupt lines, bus frequency, chip select, and device addresses. Check shared-pin conflicts.
- Set driver and subsystem configuration through Kconfig. Check dependency warnings and generated `.config` before concluding a symbol is enabled.
- Inspect `zephyr.dts` for merged node status, chosen console, aliases, memory regions, partitions, and peripheral properties.
- Treat generated files as evidence, not editable source. Resolve errors in the board, overlay, binding, or configuration fragment.

## Boot, images, and runners

Confirm which image owns each memory region. Check bootloader offsets, signing requirements, secure/nonsecure boundaries, and sysbuild domains before flashing. Use the configured runner; record probe/device selection when multiple targets are connected. Keep production keys outside the skill and evidence bundle.

Build the smallest appropriate sample first, then the application. Use a new build directory or a deliberate pristine build when changing targets or cached configuration. Diagnose errors by layer: target discovery, devicetree/bindings, Kconfig, compilation, linking, runner, reset/boot, then runtime behavior.

Sources:

- [Board porting guide](https://docs.zephyrproject.org/latest/hardware/porting/board_porting.html)
- [Devicetree documentation](https://docs.zephyrproject.org/latest/build/dts/index.html)
- [Kconfig documentation](https://docs.zephyrproject.org/latest/build/kconfig/index.html)
