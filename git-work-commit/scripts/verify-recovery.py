#!/usr/bin/env python3
"""Verify exact workflow attempt identity before reusing an existing commit."""
import argparse
import re
import subprocess
import sys


def identity_matches(message, run_id, work_id, attempt_id):
    expected = {'Workflow-Run': run_id, 'Workflow-Work': work_id, 'Workflow-Attempt': attempt_id}
    if any(not isinstance(value, str) or not value.strip() or '\n' in value or '\r' in value for value in expected.values()):
        raise ValueError('Nonempty single-line run/work/attempt IDs required')
    # Identity must be in the trailing trailer block, not quoted in the body.
    block = message.rstrip().split('\n\n')[-1]
    actual = {key: [] for key in expected}
    for line in block.splitlines():
        key, sep, value = line.partition(':')
        if sep and key in actual:
            actual[key].append(value.strip())
    return all(actual[key] == [value] for key, value in expected.items())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', required=True)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--work-id', required=True)
    parser.add_argument('--attempt-id', required=True)
    parser.add_argument('--expected-parent', required=True)
    parser.add_argument('--mode', choices=['create', 'amend'], default='create')
    parser.add_argument('--amended-from', help='Original commit SHA for an explicitly authorized amend')
    args = parser.parse_args()
    expected = [] if args.expected_parent == 'none' else args.expected_parent.split(',')
    if any(not re.fullmatch(r'[0-9a-fA-F]{40}|[0-9a-fA-F]{64}', value) for value in [args.commit] + expected):
        parser.error('Commit and expected parent must be full object IDs')
    if (args.mode == 'amend') != bool(args.amended_from) or (args.amended_from and not re.fullmatch(r'[0-9a-fA-F]{40}|[0-9a-fA-F]{64}', args.amended_from)):
        parser.error('amend mode requires --amended-from with a full SHA; create mode does not accept it')
    try:
        message = subprocess.run(['git', '-C', args.repository, 'show', '-s', '--format=%B', args.commit], check=True, capture_output=True, text=True, encoding='utf-8').stdout
        parents = subprocess.run(['git', '-C', args.repository, 'show', '-s', '--format=%P', args.commit], check=True, capture_output=True, text=True).stdout.split()
        expected = [value.lower() for value in expected]
        if args.mode == 'amend':
            original_parents = subprocess.run(['git', '-C', args.repository, 'show', '-s', '--format=%P', args.amended_from], check=True, capture_output=True, text=True).stdout.split()
            if original_parents != expected or args.commit.lower() == args.amended_from.lower():
                raise ValueError('Amend recovery must preserve the recorded original parent list and create a new SHA')
        if parents != expected or not identity_matches(message, args.run_id, args.work_id, args.attempt_id):
            raise ValueError('Commit does not match saved run/work/attempt and parent')
        print('Commit recovery identity matches; patch, signoff, validation and acceptance still require verification')
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f'error: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
