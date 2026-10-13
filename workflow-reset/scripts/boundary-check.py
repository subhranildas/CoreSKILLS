#!/usr/bin/env python3
"""Check workflow write destinations against application and library boundaries."""
import argparse
import sys
from pathlib import Path


def within(path, root):
    return path == root or root in path.parents


def check(application, runtime, writes, protected):
    application, runtime = application.resolve(), runtime.resolve()
    protected = [root.resolve() for root in protected]
    if not application.is_dir():
        raise ValueError('Application workspace must exist')
    for root in protected:
        if within(application, root) or within(runtime, root):
            raise ValueError(f'Application/runtime points into protected library: {root}')
    for destination in writes:
        path = destination.resolve()
        if any(within(path, root) for root in protected):
            raise ValueError(f'Write targets protected library: {path}')
        if not within(path, application) and not within(path, runtime):
            raise ValueError(f'Write outside configured workspace/runtime: {path}')
        # A mutation of an ancestor could move/delete the library as well.
        if any(within(root, path) for root in protected):
            raise ValueError(f'Write targets ancestor of protected library: {path}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--application-root', required=True, type=Path)
    parser.add_argument('--runtime-root', required=True, type=Path)
    parser.add_argument('--write-path', action='append', required=True, type=Path)
    parser.add_argument('--protected-root', action='append', default=[], type=Path)
    args = parser.parse_args()
    try:
        check(args.application_root, args.runtime_root, args.write_path,
              [Path(__file__).resolve().parents[2]] + args.protected_root)
    except (OSError, ValueError, RuntimeError) as error:
        print(f'error: {error}', file=sys.stderr)
        return 1
    print('Write destinations respect workspace/library boundaries')
    return 0


if __name__ == '__main__':
    sys.exit(main())
