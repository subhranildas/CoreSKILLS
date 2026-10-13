#!/usr/bin/env python3
"""Collect existing Zephyr build evidence without executing build tools."""

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ARTIFACTS = (
    "CMakeCache.txt", "build_info.yml", "domains.yaml",
    "zephyr/.config", "zephyr/zephyr.dts", "zephyr/zephyr.map",
    "zephyr/runners.yaml",
)
IMAGES = ("zephyr/zephyr.elf", "zephyr/zephyr.hex", "zephyr/zephyr.bin")
CACHE_KEYS = {"BOARD", "BOARD_REVISION", "BOARD_QUALIFIERS", "ZEPHYR_BASE",
              "APPLICATION_SOURCE_DIR", "ZEPHYR_TOOLCHAIN_VARIANT", "ZEPHYR_SDK_INSTALL_DIR"}


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def collect(args):
    build = args.build_dir.resolve()
    output = args.output.resolve()
    library = Path(__file__).resolve().parents[2]
    if output == library or library in output.parents or output in library.parents:
        raise ValueError('Evidence output must be outside the protected skill library')
    if not build.is_dir():
        raise ValueError(f"Build directory does not exist: {build}")
    if output == build or output in build.parents or build in output.parents:
        raise ValueError("Output and build directories must not contain one another")
    if output.exists():
        raise ValueError(f"Output already exists; choose a new directory: {output}")
    logs = [path.resolve() for path in args.log]
    for path in logs:
        if not path.is_file():
            raise ValueError(f"Log does not exist: {path}")
    report = {
        "schema_version": 1,
        "collected_at_utc": datetime.now(timezone.utc).isoformat(),
        "build_directory": str(build), "label": args.label,
        "build_result": "unknown", "artifacts": [], "missing": [], "cmake": {},
    }
    output.mkdir(parents=True, exist_ok=False)

    def record(source, relative, copy):
        entry = {"source": str(source), "bytes": source.stat().st_size,
                 "sha256": digest(source), "copied": copy}
        if copy:
            destination = output / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            if digest(destination) != entry["sha256"]:
                raise ValueError(f"Artifact changed during collection: {source}")
            entry["path"] = relative.as_posix()
        report["artifacts"].append(entry)

    for name in ARTIFACTS + IMAGES:
        source = build / name
        if not source.is_file():
            report["missing"].append(name)
            continue
        if not source.resolve().is_relative_to(build):
            raise ValueError(f"Artifact resolves outside build directory: {source}")
        record(source, Path("build") / name, name in ARTIFACTS or args.include_images)
    for index, path in enumerate(logs, 1):
        record(path, Path("logs") / f"{index:02d}-{path.name}", True)
    cache = output / "build/CMakeCache.txt"
    if cache.is_file():
        for line in cache.read_text(encoding="utf-8", errors="replace").splitlines():
            key_type, separator, value = line.partition("=")
            key = key_type.partition(":")[0]
            if separator and key in CACHE_KEYS:
                report["cmake"][key] = value
    (output / "evidence.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Collected {len(report['artifacts'])} artifacts; "
          f"{len(report['missing'])} missing. Manifest: {output / 'evidence.json'}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True,
                        help="New directory outside the build tree; never overwritten")
    parser.add_argument("--label", default=None, help="User-supplied target or run label")
    parser.add_argument("--log", type=Path, action="append", default=[])
    parser.add_argument("--include-images", action="store_true",
                        help="Copy firmware images in addition to recording their hashes")
    args = parser.parse_args()
    try:
        collect(args)
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
