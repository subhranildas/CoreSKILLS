"""Regression checks for schema, command readiness, and approval snapshots."""
import copy
import importlib.util
import tempfile
import unittest
import shutil
import subprocess
import sys
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / 'zephyr-platform-bringup/assets'


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'workflow-tree-editor/scripts' / filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


validator = module('validator', 'validate-workflow-plan.py')
files = module('files', 'file-state.py')
boundary_spec = importlib.util.spec_from_file_location('boundary', ROOT / 'workflow-reset/scripts/boundary-check.py')
boundary = importlib.util.module_from_spec(boundary_spec)
boundary_spec.loader.exec_module(boundary)
recovery_spec = importlib.util.spec_from_file_location('recovery', ROOT / 'git-work-commit/scripts/verify-recovery.py')
recovery = importlib.util.module_from_spec(recovery_spec)
recovery_spec.loader.exec_module(recovery)
policy_spec = importlib.util.spec_from_file_location('policy', ROOT / 'zephyr-platform-bringup/scripts/workflow-policy.py')
policy = importlib.util.module_from_spec(policy_spec)
policy_spec.loader.exec_module(policy)


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.leaf = validator.load_yaml(ASSETS / 'leaves/build-combination.yaml')
        self.plan = validator.load_yaml(ASSETS / 'workflow-plan.yaml')

    def test_bundled_tree(self):
        self.assertEqual(validator.validate(self.plan, ASSETS), 30)

    def test_schema_cannot_bypass_config_requirements(self):
        for version in (1, 2, 999, True, None, '3'):
            with self.subTest(version=version):
                candidate = copy.deepcopy(self.plan)
                candidate['schema_version'] = version
                for node in candidate['nodes']:
                    node.pop('work_config', None)
                    node.pop('workflow_config', None)
                with self.assertRaises(ValueError):
                    validator.validate(candidate, ASSETS)
        for version in (999, True, None):
            candidate = copy.deepcopy(self.leaf)
            candidate['schema_version'] = version
            with self.assertRaises(ValueError):
                validator.validate_leaf(candidate, 'build-combination')

    def test_command_readiness(self):
        validator.validate_leaf(self.leaf, 'build-combination')
        with self.assertRaisesRegex(ValueError, 'unresolved'):
            validator.validate_leaf(self.leaf, 'build-combination', require_ready=True)
        self.leaf['inputs']['build_command'] = {'argv': ['python', 'build.py', ''], 'working_directory': '.', 'shell': None}
        validator.validate_leaf(self.leaf, 'build-combination', require_ready=True)

    def test_invalid_commands(self):
        cases = [
            {'argv': [''], 'working_directory': '.'},
            {'argv': ['  '], 'working_directory': '.'},
            {'shell_command': 'echo ok', 'shell': True, 'working_directory': '.'},
            {'argv': ['python'], 'shell_command': 'python', 'shell': 'bash', 'working_directory': '.'},
            {'argv': ['python'], 'working_directory': '.', 'environment_variable_names': 'TOKEN'},
        ]
        for command in cases:
            with self.subTest(command=command), self.assertRaises(ValueError):
                validator.validate_command(command, 'test')

    def test_ready_current_command_ignores_unresolved_future_command(self):
        self.leaf['inputs']['build_command'] = {'argv': ['python', 'build.py'], 'working_directory': '.'}
        self.leaf['inputs']['later_command'] = None
        resolve = copy.deepcopy(self.leaf['steps'][0])
        resolve.update(id='resolve-later', depends_on=['perform'])
        run = copy.deepcopy(self.leaf['steps'][1])
        run.update(id='run-later', depends_on=['resolve-later'], command_ref='later_command')
        self.leaf['steps'].extend([resolve, run])
        validator.validate_leaf(self.leaf, 'build-combination', require_ready=True, step_id='perform')
        with self.assertRaisesRegex(ValueError, 'unresolved'):
            validator.validate_leaf(self.leaf, 'build-combination', require_ready=True, step_id='run-later')
        with self.assertRaisesRegex(ValueError, 'unknown selected step'):
            validator.validate_leaf(self.leaf, 'build-combination', require_ready=True, step_id='missing')

    def test_inputs_and_evidence_types(self):
        candidate = copy.deepcopy(self.leaf)
        candidate['inputs'] = 'not a mapping'
        with self.assertRaises(ValueError):
            validator.validate_leaf(candidate, 'build-combination')
        candidate = copy.deepcopy(self.leaf)
        candidate['steps'][0]['success_checks'][0]['evidence'] = 'not a list'
        with self.assertRaises(ValueError):
            validator.validate_leaf(candidate, 'build-combination')


class FileStateTests(unittest.TestCase):
    def test_library_outputs_rejected(self):
        with self.assertRaises(ValueError):
            files.capture([], ROOT / 'runtime-snapshots')
        with self.assertRaises(ValueError):
            files.protect_output(ROOT / 'manifest.json')

    def test_detects_leaf_change_with_unchanged_plan(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plan, leaf = root / 'plan.yaml', root / 'leaf.yaml'
            plan.write_text('plan unchanged')
            leaf.write_text('old steps')
            manifest = files.capture([plan, leaf], root / 'snapshots')
            files.check(manifest)
            leaf.write_text('new steps')
            with self.assertRaisesRegex(ValueError, 'File changed'):
                files.check(manifest)
            self.assertEqual((Path(manifest['root']) / manifest['files'][1]['snapshot_path']).read_text(), 'old steps')

    def test_creation_and_snapshot_corruption_invalidate_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            new = root / 'new.yaml'
            manifest = files.capture([new], root / 'snapshots')
            files.check(manifest)
            new.write_text('created concurrently')
            with self.assertRaisesRegex(ValueError, 'existence changed'):
                files.check(manifest)
            manifest = files.capture([new], root / 'snapshots')
            (Path(manifest['root']) / manifest['files'][0]['snapshot_path']).write_text('corrupt')
            with self.assertRaisesRegex(ValueError, 'Snapshot'):
                files.check(manifest)

    def test_manifest_relocation_verifies_copy_and_requires_new_approval(self):
        with tempfile.TemporaryDirectory() as temp:
            old, new = Path(temp) / 'old', Path(temp) / 'new'
            old.mkdir()
            source = old / 'config.yaml'
            source.write_text('saved config')
            manifest = files.capture([source], old / 'snapshots', old)
            shutil.copytree(old, new)
            source.unlink()
            moved = files.relocate(manifest, new)
            self.assertTrue(moved['requires_reapproval'])
            self.assertEqual(moved['files'], manifest['files'])
            files.check(moved)
            (new / 'config.yaml').write_text('changed')
            with self.assertRaises(ValueError):
                files.relocate(manifest, new)

    def test_retarget_detected_even_with_identical_file_bytes(self):
        # Simulate resolve() changing like a junction; Windows privilege is not needed.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            alias, target = root / 'alias.yaml', root / 'target.yaml'
            alias.write_text('same'); target.write_text('same')
            manifest = files.capture([alias], root / 'snapshots', root)
            original_resolve = Path.resolve
            def changed(path, *args, **kwargs):
                return target if path == alias else original_resolve(path, *args, **kwargs)
            with patch.object(Path, 'resolve', changed), self.assertRaisesRegex(ValueError, 'link target changed'):
                files.check(manifest)


class CommitPolicyTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('git'), 'Git unavailable')
    def test_git_recovery_cli_rejects_another_run_and_wrong_parent(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            def git(*args):
                return subprocess.run(['git', '-C', str(repo), *args], check=True, capture_output=True, text=True).stdout.strip()
            git('init')
            git('config', 'user.name', 'Workflow Test')
            git('config', 'user.email', 'workflow-test@example.invalid')
            git('config', 'commit.gpgSign', 'false')
            source = repo / 'work.txt'
            source.write_text('baseline')
            git('add', '--', 'work.txt')
            git('commit', '-m', 'Baseline')
            parent = git('rev-parse', 'HEAD')
            source.write_text('updated')
            git('add', '--', 'work.txt')
            message = repo / 'message.txt'
            message.write_text('Update\n\nWorkflow-Run: current-run\nWorkflow-Work: build.beta\nWorkflow-Attempt: attempt1\n')
            git('commit', '--signoff', '--file', str(message))
            sha = git('rev-parse', 'HEAD')
            command = [sys.executable, '-B', str(ROOT / 'git-work-commit/scripts/verify-recovery.py'), '--repository', str(repo), '--commit', sha, '--run-id', 'current-run', '--work-id', 'build.beta', '--attempt-id', 'attempt1', '--expected-parent', parent]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            command[command.index('--run-id') + 1] = 'old-run'
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            command[command.index('--run-id') + 1] = 'current-run'
            command[-1] = sha
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            message.write_text('Amended update\n\nWorkflow-Run: current-run\nWorkflow-Work: build.beta\nWorkflow-Attempt: amend1\n')
            git('commit', '--amend', '--signoff', '--file', str(message))
            amended_sha = git('rev-parse', 'HEAD')
            command[command.index('--commit') + 1] = amended_sha
            command[command.index('--attempt-id') + 1] = 'amend1'
            command[-1] = parent
            command += ['--mode', 'amend', '--amended-from', sha]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            command[command.index('--expected-parent') + 1] = sha
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)

    def test_run_work_attempt_identity_is_exact_and_unique(self):
        message = 'Change\n\nWorkflow-Run: run2\nWorkflow-Work: build.beta\nWorkflow-Attempt: attempt2\nSigned-off-by: User <u@example.com>\n'
        self.assertTrue(recovery.identity_matches(message, 'run2', 'build.beta', 'attempt2'))
        self.assertFalse(recovery.identity_matches(message, 'run1', 'build.beta', 'attempt2'))
        self.assertFalse(recovery.identity_matches(message, 'run2', 'build.beta', 'attempt1'))
        self.assertFalse(recovery.identity_matches(message + 'Workflow-Run: run2\n', 'run2', 'build.beta', 'attempt2'))

    def test_leaf_override_wins_and_null_inherits(self):
        for template in (False, True):
            self.assertEqual(policy.resolve_skippable(template, None), {'skippable': template, 'source': 'template'})
            for override in (False, True):
                self.assertEqual(policy.resolve_skippable(template, override), {'skippable': override, 'source': 'leaf_override'})
        with self.assertRaises(ValueError):
            policy.resolve_skippable(False, 'true')


class BoundaryTests(unittest.TestCase):
    def test_library_is_not_an_application_or_write_destination(self):
        with tempfile.TemporaryDirectory() as temp:
            app = Path(temp)
            runtime = app / 'bringup'
            boundary.check(app, runtime, [runtime / 'session.yaml'], [ROOT])
            for path in (ROOT / 'SKILL.md', ROOT / 'new/session.yaml', ROOT.parent):
                with self.assertRaises(ValueError):
                    boundary.check(app, runtime, [path], [ROOT])
            with self.assertRaises(ValueError):
                boundary.check(ROOT, ROOT / 'bringup', [ROOT / 'session.yaml'], [ROOT])
            with self.assertRaises(ValueError):
                boundary.check(app, ROOT / 'runtime', [app / 'session.yaml'], [ROOT])

    def test_nested_installation_protects_skill_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            app = Path(temp)
            installed = app / '.agents/skills'
            installed.mkdir(parents=True)
            boundary.check(app, app / 'bringup', [app / 'src/main.c'], [installed])
            with self.assertRaises(ValueError):
                boundary.check(app, app / 'bringup', [installed / 'skill/SKILL.md'], [installed])


if __name__ == '__main__':
    unittest.main()
