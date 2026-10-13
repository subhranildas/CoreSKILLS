#!/usr/bin/env python3
"""Resolve the skip flag inherited by a commit or report child."""
import argparse


def resolve_skippable(template, override):
    if type(template) is not bool or (override is not None and type(override) is not bool):
        raise ValueError('Template must be Boolean and override null/Boolean')
    return {'skippable': template if override is None else override,
            'source': 'template' if override is None else 'leaf_override'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--template', required=True, choices=['true', 'false'])
    parser.add_argument('--override', default='inherit', choices=['inherit', 'true', 'false'])
    args = parser.parse_args()
    import json
    print(json.dumps(resolve_skippable(args.template == 'true', None if args.override == 'inherit' else args.override == 'true')))


if __name__ == '__main__':
    main()
