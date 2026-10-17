"""Read-only scoped selection and prerequisite regression checks."""
import copy
import importlib.util
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
LIBRARY = Path(__file__).resolve().parents[2]
ASSETS = LIBRARY / 'zephyr-platform-bringup/assets'
spec = importlib.util.spec_from_file_location('selector', LIBRARY / 'zephyr-platform-bringup/scripts/select-workflow.py')
selector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(selector)
validator_spec = importlib.util.spec_from_file_location('validator', LIBRARY / 'workflow-tree-editor/scripts/validate-workflow-plan.py')
validator = importlib.util.module_from_spec(validator_spec)
validator_spec.loader.exec_module(validator)


class ScopeTests(unittest.TestCase):
    def setUp(self):
        self.plan = validator.load_yaml(ASSETS / 'workflow-plan.yaml')

    def test_subworkflow_does_not_include_siblings(self):
        result = selector.selection(self.plan, ASSETS, 'register')
        self.assertEqual(result['allowed_node_ids'], ['register', 'command-mapping', 'dispatch-checks', 'help-ci'])
        self.assertNotIn('integrate', result['allowed_node_ids'])
        self.assertNotIn('verification', result['allowed_node_ids'])
        self.assertEqual(result['mode'], 'scoped')
        self.assertTrue(result['stop_after_selected_node'])
        self.assertFalse(result['execution_ready'])

    def test_single_leaf_and_filters(self):
        filters = {'application': 'sensor', 'platform': 'beta', 'variant': 'debug'}
        result = selector.selection(self.plan, ASSETS, 'build-combination', filters)
        self.assertEqual(result['allowed_node_ids'], ['build-combination'])
        self.assertEqual(result['instance_filters'], filters)
        self.assertEqual(result['expansion_requirements'][0]['expand_per'], 'selected-combination')

    def test_full_selection_uses_root_config_order(self):
        self.plan['nodes'][0]['children'].reverse()
        result = selector.selection(self.plan, ASSETS, 'add-platform')
        self.assertEqual(result['mode'], 'full')
        self.assertEqual(len(result['allowed_node_ids']), 30)
        self.assertLess(result['allowed_node_ids'].index('discovery-and-assessment'), result['allowed_node_ids'].index('verification'))
        self.assertEqual(result['external_prerequisite_ids'], [])

    def test_inherited_external_prerequisites_are_not_scheduled(self):
        result = selector.selection(self.plan, ASSETS, 'build-combination')
        self.assertEqual(result['external_prerequisite_ids'], ['discovery-and-assessment', 'platform-integration'])
        self.assertTrue(set(result['external_prerequisite_ids']).isdisjoint(result['allowed_node_ids']))

    def test_explicit_leaf_dependency_is_preserved(self):
        candidate = copy.deepcopy(self.plan)
        next(node for node in candidate['nodes'] if node['id'] == 'command-mapping')['depends_on'] = ['board-support']
        result = selector.selection(candidate, ASSETS, 'register')
        self.assertIn('board-support', result['external_prerequisite_ids'])
        self.assertNotIn('board-support', result['allowed_node_ids'])

    def test_unknown_node_rejected_and_plan_not_modified(self):
        before = copy.deepcopy(self.plan)
        with self.assertRaisesRegex(ValueError, 'Unknown selected node'):
            selector.selection(self.plan, ASSETS, 'missing')
        selector.selection(self.plan, ASSETS, 'register')
        self.assertEqual(self.plan, before)

    def disable(self, **entries):
        self.plan['execution_profile'] = {'name': 'development', 'disabled': {key: {'reason': reason} for key, reason in entries.items()}}

    def test_disabled_workflow_excludes_subtree_without_mutating_plan(self):
        self.disable(hardware='No board')
        before = copy.deepcopy(self.plan)
        result = selector.selection(self.plan, ASSETS, 'verification')
        self.assertNotIn('hardware', result['executable_node_ids'])
        self.assertNotIn('boot-check', result['executable_node_ids'])
        self.assertIn('build-combination', result['executable_node_ids'])
        self.assertEqual(result['disabled_nodes']['boot-check']['disabled_by'], 'hardware')
        self.assertEqual(result['disabled_nodes']['boot-check']['status'], 'disabled')
        self.assertEqual(self.plan, before)

    def test_disabled_required_leaf_and_scoped_parent_override(self):
        self.disable(inventory='Testing another stage')
        result = selector.selection(self.plan, ASSETS, 'inventory')
        self.assertEqual(result['executable_node_ids'], [])
        self.disable(discover='Testing another stage')
        result = selector.selection(self.plan, ASSETS, 'inventory')
        self.assertEqual(result['executable_node_ids'], [])

    def test_disabled_dependency_blocks(self):
        next(n for n in self.plan['nodes'] if n['id'] == 'trace-commands')['depends_on'] = ['inventory']
        self.disable(inventory='Development')
        result = selector.selection(self.plan, ASSETS, 'discover')
        self.assertIn({'node': 'trace-commands', 'dependency': 'inventory'}, result['profile_blockers'])

    def test_disabled_root_predecessor_blocks_scoped_descendant(self):
        self.disable(**{'platform-integration': 'Development'})
        result = selector.selection(self.plan, ASSETS, 'build-combination')
        self.assertTrue(result['profile_blockers'])

    def test_invalid_profile_rejected(self):
        for profile in ({'name': 'dev', 'disabled': {'missing': {'reason': 'test'}}},
                        {'name': 'dev', 'disabled': {'add-platform': {'reason': 'test'}}},
                        {'name': 'dev', 'disabled': {'inventory': {'reason': ''}}},
                        {'name': 'dev', 'disabled': []}, {'name': '', 'disabled': {}}):
            self.plan['execution_profile'] = profile
            with self.assertRaises(ValueError):
                selector.selection(self.plan, ASSETS, 'inventory')

    def test_absent_or_empty_profile_preserves_selection(self):
        self.plan.pop('execution_profile', None)
        result = selector.selection(self.plan, ASSETS, 'add-platform')
        self.assertEqual(result['allowed_node_ids'], result['executable_node_ids'])
        self.assertEqual(result['disabled_nodes'], {})
        self.assertEqual(result['profile_blockers'], [])


if __name__ == '__main__':
    unittest.main()
