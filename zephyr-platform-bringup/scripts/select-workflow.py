#!/usr/bin/env python3
"""Read-only selection of a workflow subtree and external prerequisite IDs."""
import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path


def selection(plan, directory, node_id, instances=None):
    sys.dont_write_bytecode = True
    path = Path(__file__).resolve().parents[2] / 'workflow-tree-editor/scripts/validate-workflow-plan.py'
    spec = importlib.util.spec_from_file_location('workflow_validator', path)
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    validator.validate(plan, directory)
    nodes = {node['id']: node for node in plan['nodes']}
    if node_id not in nodes:
        raise ValueError(f'Unknown selected node: {node_id}')
    root = plan['entrypoint']
    root_config = validator.load_yaml(directory / nodes[root]['workflow_config'])
    root_order = [step['workflow'] for step in root_config['steps'] if step['action'] == 'workflow']
    allowed = []
    def descend(key):
        allowed.append(key)
        for child in (root_order if key == root else nodes[key].get('children', [])):
            descend(child)
    descend(node_id)
    ancestors = []
    parent = nodes[node_id]['parent_id']
    while parent is not None:
        ancestors.insert(0, parent)
        parent = nodes[parent]['parent_id']
    dependencies = set()
    for key in allowed + ancestors:
        dependencies.update(nodes[key].get('depends_on', []))
    # Root-local prerequisites are covered by bootstrap; workflow prerequisites
    # outside the selection need equivalent verified input evidence.
    by_step = {step['id']: step for step in root_config['steps']}
    relevant = set(allowed + ancestors)
    visited = set()
    def prerequisite(step_id):
        if step_id in visited:
            return
        visited.add(step_id)
        step = by_step[step_id]
        if step['action'] == 'workflow':
            dependencies.add(step['workflow'])
        for dep in step.get('depends_on', []):
            prerequisite(dep)
    for step in root_config['steps']:
        if step.get('workflow') in relevant:
            for dep in step.get('depends_on', []):
                prerequisite(dep)
    disabled = {}
    overrides = plan.get('execution_profile', {}).get('disabled', {})
    for key in allowed:
        ancestor = key
        while ancestor is not None:
            if ancestor in overrides:
                disabled[key] = {'disabled_by': ancestor, 'reason': overrides[ancestor]['reason'], 'status': 'disabled'}
                break
            ancestor = nodes[ancestor]['parent_id']
    # Retain selection membership for reporting, while exposing a distinct
    # executable set. Disabled prerequisites are never silently satisfied.
    def affected(key):
        ancestor = key
        while ancestor is not None:
            if ancestor in overrides:
                return True
            ancestor = nodes[ancestor]['parent_id']
        return any(affected(child) for child in nodes[key].get('children', []))
    blockers = []
    for key in allowed:
        if key in disabled:
            continue
        for dep in nodes[key].get('depends_on', []):
            if affected(dep):
                blockers.append({'node': key, 'dependency': dep})
    active = set(allowed) - set(disabled)
    relevant = active | (set(ancestors) if active else set())
    def affected_event(step_id):
        step = by_step[step_id]
        return ((step.get('workflow') is not None and affected(step['workflow'])) or
                any(affected_event(dep) for dep in step.get('depends_on', [])))
    for step in root_config['steps']:
        if step.get('workflow') in relevant:
            for dep in step.get('depends_on', []):
                if affected_event(dep):
                    blockers.append({'node': step['workflow'], 'dependency': dep})
    return {'mode': 'full' if node_id == root else 'scoped', 'selected_node': node_id,
            'allowed_node_ids': allowed, 'context_ancestors': ancestors,
            'executable_node_ids': [key for key in allowed if key not in disabled],
            'disabled_nodes': disabled, 'profile_blockers': blockers,
            'execution_profile': plan.get('execution_profile', {'name': 'default', 'disabled': {}}),
            'external_prerequisite_ids': sorted(dependencies - set(allowed) - set(ancestors)),
            'instance_filters': instances or {},
            'expansion_requirements': [{'id': key, 'expand_per': nodes[key]['expand_per']}
                                       for key in allowed if 'expand_per' in nodes[key]],
            'stop_after_selected_node': True, 'execution_ready': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan', type=Path)
    parser.add_argument('--node')
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--instance', action='append', default=[])
    args = parser.parse_args()
    if args.node and args.list:
        parser.error('Choose --node or --list')
    try:
        import yaml
    except ImportError:
        print('error: PyYAML required to validate and select workflows', file=sys.stderr)
        return 1
    try:
        # Parsing and duplicate-key rejection use the shared validator via selection.
        sys.dont_write_bytecode = True
        path = Path(__file__).resolve().parents[2] / 'workflow-tree-editor/scripts/validate-workflow-plan.py'
        spec = importlib.util.spec_from_file_location('workflow_validator', path)
        validator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(validator)
        plan = validator.load_yaml(args.plan)
        filters = {}
        for item in args.instance:
            key, separator, value = item.partition('=')
            if not separator or key not in ('application', 'platform', 'variant', 'peripheral', 'capability', 'domain') or not value.strip() or key in filters:
                raise ValueError('Use unique --instance <application|platform|variant|peripheral|capability|domain>=<value> selectors')
            filters[key] = value
        selected = selection(plan, args.plan.resolve().parent, args.node or plan['entrypoint'], filters)
        if args.list:
            selected = {'targets': [{'id': node['id'], 'kind': node['kind'], 'parent_id': node['parent_id']} for node in plan['nodes']]}
        else:
            selected['plan_sha256'] = hashlib.sha256(args.plan.read_bytes()).hexdigest()
        print(json.dumps(selected, indent=2))
    except (OSError, ValueError, TypeError, KeyError, ImportError, RuntimeError, yaml.YAMLError) as error:
        print(f'error: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
