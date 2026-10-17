#!/usr/bin/env python3
"""Read-only validation of a sequential workflow YAML plan (requires PyYAML)."""
import argparse
import sys
from pathlib import Path


def load_yaml(path):
    import yaml
    class UniqueLoader(yaml.SafeLoader):
        pass
    def mapping(loader, node, deep=False):
        result = {}
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node, deep=deep)
            if key in result:
                raise ValueError(f'Duplicate YAML key: {key}')
            result[key] = loader.construct_object(value_node, deep=deep)
        return result
    UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)
    return yaml.load(path.read_text(encoding='utf-8'), Loader=UniqueLoader)


def schema(data, version, label):
    if type(data.get('schema_version')) is not int or data['schema_version'] != version:
        raise ValueError(f'{label}: supported schema_version is {version}; migrate older files explicitly')


def string_list(value, label):
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(f'{label}: list of nonempty strings required')


def validate_command(command, label):
    if not isinstance(command, dict):
        raise ValueError(f'{label}: command mapping required')
    argv, shell_text = command.get('argv'), command.get('shell_command')
    argv_valid = isinstance(argv, list) and bool(argv) and all(isinstance(a, str) for a in argv) and bool(argv[0].strip())
    shell_valid = isinstance(shell_text, str) and bool(shell_text.strip())
    if argv_valid == shell_valid or (argv is not None and not argv_valid) or (shell_text is not None and not shell_valid):
        raise ValueError(f'{label}: use exactly one valid argv or shell_command with a nonempty executable')
    shell = command.get('shell')
    if shell is not None and (not isinstance(shell, str) or not shell.strip()):
        raise ValueError(f'{label}: shell must be a nonempty string or null')
    if shell_valid and shell is None:
        raise ValueError(f'{label}: explicit shell required')
    if not isinstance(command.get('working_directory'), str) or not command['working_directory'].strip():
        raise ValueError(f'{label}: working_directory required')
    string_list(command.get('environment_variable_names', []), f'{label}: environment_variable_names')


def validate_leaf(config, work_id, allow_workflow=False, require_ready=False, step_id=None):
    if not isinstance(config, dict) or config.get('work_id') != work_id:
        raise ValueError(f'{work_id}: work_config ID mismatch')
    schema(config, 1, work_id)
    if not isinstance(config.get('inputs'), dict):
        raise ValueError(f'{work_id}: inputs must be a mapping')
    steps = config.get('steps')
    if not isinstance(steps, list) or not steps:
        raise ValueError(f'{work_id}: ordered steps required')
    ready_steps = None
    if step_id is not None:
        by_id = {s['id']: s for s in steps if isinstance(s, dict) and isinstance(s.get('id'), str)}
        if step_id not in by_id:
            raise ValueError(f'{work_id}: unknown selected step {step_id}')
        ready_steps = set()
        def include(key):
            if key in ready_steps:
                return
            if key not in by_id:
                raise ValueError(f'{work_id}: missing dependency {key}')
            ready_steps.add(key)
            deps = by_id[key].get('depends_on', [])
            string_list(deps, f'{work_id}/{key}: depends_on')
            for dep in deps:
                include(dep)
        include(step_id)
    seen = set()
    for step in steps:
        if not isinstance(step, dict):
            raise ValueError(f'{work_id}: step must be a mapping')
        key = step.get('id')
        if not isinstance(key, str) or not key.strip() or key in seen:
            raise ValueError(f'{work_id}: invalid/duplicate step ID')
        for flag in ('skippable', 'checkpoint_after'):
            if type(step.get(flag)) is not bool:
                raise ValueError(f'{work_id}/{key}: {flag} must be Boolean')
        deps = step.get('depends_on', [])
        if not isinstance(deps, list) or any(not isinstance(d, str) or d not in seen for d in deps):
            raise ValueError(f'{work_id}/{key}: dependencies must identify earlier steps')
        if len(deps) != len(set(deps)):
            raise ValueError(f'{work_id}/{key}: duplicate step dependency')
        action = step.get('action')
        if 'tool' in step and (action != 'command' or not isinstance(step['tool'], str) or not step['tool'].strip()):
            raise ValueError(f'{work_id}/{key}: tool binding requires a command action and nonempty tool ID')
        actions = ('inspect', 'edit', 'command', 'ask', 'manual', 'skill') + (('workflow',) if allow_workflow else ())
        if action not in actions:
            raise ValueError(f'{work_id}/{key}: unsupported action')
        if action == 'workflow' and (not isinstance(step.get('workflow'), str) or not step['workflow'].strip()):
            raise ValueError(f'{work_id}/{key}: workflow ID required')
        if not isinstance(step.get('instructions'), str) or not step['instructions'].strip():
            raise ValueError(f'{work_id}/{key}: instructions required')
        if action == 'skill' and (not isinstance(step.get('skill'), str) or not step['skill'].strip()):
            raise ValueError(f'{work_id}/{key}: skill name required')
        if action == 'command':
            ref = step.get('command_ref')
            if ref is not None:
                if 'command' in step or not isinstance(ref, str) or ref not in config['inputs']:
                    raise ValueError(f'{work_id}/{key}: command_ref must name an input and cannot accompany command')
                if config['inputs'][ref] is not None:
                    validate_command(config['inputs'][ref], f'{work_id}/{key}')
                elif require_ready and (ready_steps is None or key in ready_steps):
                    raise ValueError(f'{work_id}/{key}: command input {ref} is unresolved')
                if not deps:
                    raise ValueError(f'{work_id}/{key}: referenced command requires an earlier resolution step')
            else:
                validate_command(step.get('command'), f'{work_id}/{key}')
        checks = step.get('success_checks')
        if not isinstance(checks, list) or not checks:
            raise ValueError(f'{work_id}/{key}: success_checks required')
        check_ids = set()
        for check in checks:
            if not isinstance(check, dict) or any(not isinstance(check.get(f), str) or not check[f].strip() for f in ('id', 'expected', 'verification')):
                raise ValueError(f'{work_id}/{key}: check id/expected/verification required')
            if check['id'] in check_ids:
                raise ValueError(f'{work_id}/{key}: duplicate check ID')
            string_list(check.get('evidence', []), f'{work_id}/{key}: evidence')
            check_ids.add(check['id'])
        seen.add(key)
    completion = config.get('completion', {})
    if not isinstance(completion, dict):
        raise ValueError(f'{work_id}: completion must be a mapping')
    for kind in ('commit', 'update_report'):
        entry = completion.get(kind, {})
        if not isinstance(entry, dict) or (entry.get('skippable') is not None and type(entry['skippable']) is not bool):
            raise ValueError(f'{work_id}: completion {kind} override must be null/Boolean')


def validate(plan, directory):
    if not isinstance(plan, dict) or not isinstance(plan.get('nodes'), list):
        raise ValueError('Plan must contain a nodes list')
    schema(plan, 3, 'plan')
    tools = plan.get('tools', {})
    if not isinstance(tools, dict):
        raise ValueError('tools must be a mapping')
    for tool_id, tool in tools.items():
        if not isinstance(tool_id, str) or not tool_id.strip() or not isinstance(tool, dict):
            raise ValueError('Invalid tool registry entry')
        for field in ('script', 'log_path'):
            value = tool.get(field)
            if not isinstance(value, str) or not value.strip() or Path(value).is_absolute() or '..' in Path(value).parts:
                raise ValueError(f'{tool_id}: {field} must be a nonempty relative path')
    def bindings(config):
        for step in config['steps']:
            if 'tool' in step and step['tool'] not in tools:
                raise ValueError(f'Unknown command tool: {step["tool"]}')
    nodes = {}
    for node in plan['nodes']:
        if not isinstance(node, dict):
            raise ValueError('Each node must be a mapping')
        key = node.get('id')
        if not isinstance(key, str) or not key.strip() or key in nodes:
            raise ValueError(f'Invalid or duplicate node ID: {key}')
        if node.get('kind') not in ('workflow', 'work'):
            raise ValueError(f'{key}: kind must be workflow or work')
        if type(node.get('skippable')) is not bool:
            raise ValueError(f'{key}: skippable must be explicit true/false')
        children = node.get('children', [])
        if not isinstance(children, list) or any(not isinstance(c, str) for c in children):
            raise ValueError(f'{key}: children must be a list of IDs')
        if len(children) != len(set(children)):
            raise ValueError(f'{key}: duplicate child')
        if node['kind'] == 'work':
            if children or not isinstance(node.get('criterion'), str) or not node['criterion'].strip():
                raise ValueError(f'{key}: work requires a criterion and cannot have children')
            if plan.get('schema_version', 1) >= 2 or 'work_config' in node:
                config_path = node.get('work_config')
                if not isinstance(config_path, str) or not config_path or not (directory / config_path).is_file():
                    raise ValueError(f'{key}: existing work_config file required')
                config = load_yaml(directory / config_path)
                validate_leaf(config, key)
                bindings(config)
        elif not children:
            raise ValueError(f'{key}: workflow requires at least one child')
        if 'procedure' in node:
            procedure = node['procedure']
            if not isinstance(procedure, str) or not procedure or not (directory / procedure).is_file():
                raise ValueError(f'{key}: procedure file does not exist')
        deps = node.get('depends_on', [])
        if not isinstance(deps, list) or any(not isinstance(d, str) for d in deps):
            raise ValueError(f'{key}: depends_on must be a list of IDs')
        if len(deps) != len(set(deps)):
            raise ValueError(f'{key}: duplicate dependency')
        nodes[key] = node
    root = plan.get('entrypoint')
    profile = plan.get('execution_profile', {'name': 'default', 'disabled': {}})
    if not isinstance(profile, dict) or set(profile) - {'name', 'disabled'}:
        raise ValueError('execution_profile supports only name and disabled')
    if not isinstance(profile.get('name'), str) or not profile['name'].strip():
        raise ValueError('execution_profile requires a nonempty name')
    disabled = profile.get('disabled', {})
    if not isinstance(disabled, dict):
        raise ValueError('execution_profile.disabled must map node IDs to reasons')
    for key, entry in disabled.items():
        if key not in nodes or key == root:
            raise ValueError(f'Invalid disabled node: {key}; the root cannot be disabled')
        if not isinstance(entry, dict) or set(entry) != {'reason'} or not isinstance(entry['reason'], str) or not entry['reason'].strip():
            raise ValueError(f'{key}: disabled entry requires only a nonempty reason')
    if not isinstance(root, str) or root not in nodes or nodes[root].get('parent_id') is not None:
        raise ValueError('Entrypoint must identify the root with null parent')
    root_children = nodes[root].get('children', [])
    if plan.get('schema_version', 1) >= 3 or 'workflow_config' in nodes[root]:
        config_path = nodes[root].get('workflow_config')
        if not isinstance(config_path, str) or not config_path or not (directory / config_path).is_file():
            raise ValueError('Root requires an existing workflow_config file')
        config = load_yaml(directory / config_path)
        if not isinstance(config, dict) or config.get('workflow_id') != root:
            raise ValueError('Root workflow_config ID mismatch')
        validate_leaf(dict(config, work_id=root), root, allow_workflow=True)
        bindings(config)
        sequence = [step['workflow'] for step in config['steps'] if step['action'] == 'workflow']
        if len(sequence) != len(set(sequence)) or set(sequence) != set(root_children):
            raise ValueError('Root events must reference every direct child exactly once')
        root_children = sequence
    visited, visiting, starts, ends = set(), set(), {}, {}
    counter = 0

    def walk(key):
        nonlocal counter
        if key in visiting or key in visited:
            raise ValueError(f'{key}: cycle or multiple parents')
        visiting.add(key)
        starts[key] = counter
        counter += 1
        for child in (root_children if key == root else nodes[key].get('children', [])):
            if child not in nodes or nodes[child].get('parent_id') != key:
                raise ValueError(f'{key}: missing child or inconsistent parent: {child}')
            walk(child)
        ends[key] = counter
        counter += 1
        visiting.remove(key)
        visited.add(key)

    walk(root)
    if visited != set(nodes):
        raise ValueError('Unreachable nodes: ' + ', '.join(sorted(set(nodes) - visited)))
    for key, node in nodes.items():
        for dep in node.get('depends_on', []):
            if dep not in nodes or ends[dep] >= starts[key]:
                raise ValueError(f'{key}: dependency must finish earlier in sequential order: {dep}')
    for field in ('commit_child_template', 'report_child_template'):
        template = plan.get(field)
        if not isinstance(template, dict) or type(template.get('skippable')) is not bool:
            raise ValueError(f'{field}: explicit skippable required')
        if template.get('kind') != 'workflow' or not template.get('skill') or not template.get('criterion'):
            raise ValueError(f'{field}: kind, skill, criterion required')
    if plan['commit_child_template'].get('children') != ['update-report']:
        raise ValueError('Commit template must retain its update-report child')
    return len(nodes)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan', type=Path, nargs='?')
    parser.add_argument('--leaf-config', type=Path)
    parser.add_argument('--work-id')
    parser.add_argument('--root-config', type=Path)
    parser.add_argument('--workflow-id')
    parser.add_argument('--step', help='Current step/event; readiness includes only its dependencies')
    parser.add_argument('--require-ready', action='store_true', help='Reject unresolved referenced commands in leaf mode')
    args = parser.parse_args()
    if sum(bool(p) for p in (args.plan, args.leaf_config, args.root_config)) != 1:
        parser.error('Choose plan, --leaf-config, or --root-config')
    if (args.leaf_config and (not args.work_id or args.workflow_id)) or (args.root_config and (not args.workflow_id or args.work_id)) or (args.plan and (args.require_ready or args.work_id or args.workflow_id or args.step)):
        parser.error('Config modes require their matching ID; plan mode checks structure only')
    if args.require_ready and not args.step:
        parser.error('--require-ready requires --step to identify the current event')
    try:
        import yaml
    except ImportError:
        print('error: PyYAML required; install it in your selected environment with python -m pip install PyYAML', file=sys.stderr)
        return 1
    try:
        if args.leaf_config or args.root_config:
            config = load_yaml(args.leaf_config or args.root_config)
            key = args.work_id or args.workflow_id
            if args.root_config:
                if not isinstance(config, dict) or config.get('workflow_id') != key:
                    raise ValueError('Root workflow_config ID mismatch')
                config = dict(config, work_id=key)
            validate_leaf(config, key, allow_workflow=bool(args.root_config), require_ready=args.require_ready, step_id=args.step)
            print('Valid ' + ('root' if args.root_config else 'leaf') + ' configuration' + ('; selected step and prerequisite commands ready' if args.require_ready else '; referenced commands may need resolution'))
            return 0
        plan = load_yaml(args.plan)
        count = validate(plan, args.plan.resolve().parent)
    except (OSError, ValueError, TypeError, RecursionError, yaml.YAMLError) as error:
        print(f'error: {error}', file=sys.stderr)
        return 1
    print(f'Valid sequential workflow plan: {count} nodes; referenced commands may need resolution')
    return 0


if __name__ == '__main__':
    sys.exit(main())
