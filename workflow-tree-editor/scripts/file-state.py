#!/usr/bin/env python3
"""Capture immutable file snapshots and verify multi-file approval manifests."""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path


def relative(path, root):
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        raise ValueError(f'Path outside manifest root: {path}') from None


def local(root, value):
    if not isinstance(value, str) or not value or Path(value).is_absolute() or '..' in Path(value).parts:
        raise ValueError(f'Invalid root-relative path: {value}')
    return root / value


def capture(paths, snapshot_dir, root=None):
    protect_output(snapshot_dir)
    paths = [Path(os.path.abspath(path)) for path in paths]
    snapshot_dir = Path(os.path.abspath(snapshot_dir))
    root = Path(root).resolve() if root else Path(os.path.commonpath([str(snapshot_dir)] + [str(p.parent) for p in paths])).resolve()
    relative(snapshot_dir.resolve(), root)
    entries, seen = [], set()
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    for path in paths:
        key = relative(path, root)
        if key in seen:
            raise ValueError(f'Duplicate source path: {path}')
        seen.add(key)
        resolved = relative(path.resolve(), root)
        if not path.exists():
            entries.append({'path': key, 'resolved_path': resolved, 'exists': False, 'sha256': None, 'snapshot_path': None})
            continue
        data = path.read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        target = snapshot_dir / (sha + '.snapshot')
        relative(target.resolve(), root)
        if target.exists():
            if target.read_bytes() != data:
                raise ValueError(f'Snapshot corrupted: {target}')
        else:
            with target.open('xb') as stream:
                stream.write(data)
        if relative(path.resolve(), root) != resolved:
            raise ValueError(f'Source link changed during capture: {path}')
        entries.append({'path': key, 'resolved_path': resolved, 'exists': True, 'sha256': sha, 'snapshot_path': relative(target, root)})
    return {'schema_version': 2, 'root': str(root), 'files': entries, 'requires_reapproval': False}


def protect_output(path):
    path = path.resolve()
    library = Path(__file__).resolve().parents[2]
    if path == library or library in path.parents or path in library.parents:
        raise ValueError(f'Output must be outside protected skill library: {path}')


def check(manifest):
    if not isinstance(manifest, dict) or type(manifest.get('schema_version')) is not int or manifest.get('schema_version') != 2 or not isinstance(manifest.get('files'), list):
        raise ValueError('Manifest schema 2 required; migrate legacy absolute-path manifests explicitly')
    if not isinstance(manifest.get('root'), str) or not Path(manifest['root']).is_absolute():
        raise ValueError('Manifest root must be absolute')
    root, seen = Path(manifest['root']).resolve(), set()
    for entry in manifest['files']:
        if not isinstance(entry, dict) or type(entry.get('exists')) is not bool:
            raise ValueError('Invalid file-state entry')
        path = local(root, entry.get('path'))
        if entry['path'] in seen:
            raise ValueError('Duplicate manifest source')
        seen.add(entry['path'])
        if relative(path.resolve(), root) != entry.get('resolved_path'):
            raise ValueError(f'Source path/link target changed: {path}')
        if path.exists() != entry['exists']:
            raise ValueError(f'File existence changed: {path}')
        if entry['exists']:
            sha = entry['sha256']
            if hashlib.sha256(path.read_bytes()).hexdigest() != sha:
                raise ValueError(f'File changed: {path}')
            snapshot = local(root, entry.get('snapshot_path'))
            relative(snapshot.resolve(), root)
            if hashlib.sha256(snapshot.read_bytes()).hexdigest() != sha:
                raise ValueError(f'Snapshot missing or corrupted: {path}')


def relocate(manifest, new_root):
    candidate = dict(manifest, root=str(new_root.resolve()), requires_reapproval=True)
    check(candidate)
    return candidate


def write_manifest(path, manifest):
    protect_output(path)
    if path.exists():
        raise ValueError('Manifest already exists; use a new path per revision')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(manifest, stream, indent=2)
        stream.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='mode', required=True)
    capture_args = sub.add_parser('capture')
    capture_args.add_argument('--snapshot-dir', required=True, type=Path)
    capture_args.add_argument('--root', type=Path)
    capture_args.add_argument('--output', required=True, type=Path)
    capture_args.add_argument('files', nargs='+', type=Path)
    check_args = sub.add_parser('check')
    check_args.add_argument('manifest', type=Path)
    move_args = sub.add_parser('relocate')
    move_args.add_argument('manifest', type=Path)
    move_args.add_argument('--root', required=True, type=Path)
    move_args.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.mode == 'capture':
            protect_output(args.output)
            if args.output.exists():
                raise ValueError('Manifest already exists; use a new path per revision')
            manifest = capture(args.files, args.snapshot_dir, args.root)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open('x', encoding='utf-8') as stream:
                json.dump(manifest, stream, indent=2)
                stream.write('\n')
            print(f'Captured {len(manifest["files"])} file states: {args.output}')
        else:
            manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
            if args.mode == 'relocate':
                write_manifest(args.output, relocate(manifest, args.root))
                print('Relocated and verified; pending editor/commit approvals must be renewed')
            else:
                check(manifest)
                print('All source paths, file states and snapshots match')
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as error:
        print(f'error: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
