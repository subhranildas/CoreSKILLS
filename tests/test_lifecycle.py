"""Native lifecycle transitions, locking, and scoped isolation."""
import contextlib
import copy
import io
import json
import tempfile
import shutil
import subprocess
import time
import unittest
import yaml
from pathlib import Path

from coreskills import cli, runtime as rt

LIBRARY = Path(__file__).resolve().parents[1]


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.app = Path(self.temp.name)
        self.runtime = self.app / "bringup/run"
        self.session = self.runtime / "run.json"
        with contextlib.redirect_stdout(io.StringIO()):
            result = cli.main(["--library", str(LIBRARY), "init", "--application", str(self.app), "--runtime", str(self.runtime), "--workflow", "inventory"])
        self.assertEqual(result, 0)
        self.evidence = self.app / "evidence.txt"
        self.evidence.write_text("inspected applications and platforms", encoding="utf-8")

    def command(self, *arguments):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return cli.main(["--library", str(LIBRARY), *arguments, "--session", str(self.session)])

    def test_scoped_run_does_not_schedule_siblings(self):
        state = rt.load_state(self.session)
        self.assertEqual([u["base_id"] for u in state["units"]], ["inventory"])
        self.assertEqual(state["selection"]["mode"], "scoped")

    def test_failed_checks_cannot_advance_or_commit(self):
        self.assertEqual(self.command("run"), 0)
        self.assertEqual(self.command("record-check", "--check", "result-recorded", "--result", "fail", "--evidence", str(self.evidence)), 0)
        self.assertEqual(rt.load_state(self.session)["status"], "awaiting_intervention")
        self.assertNotEqual(self.command("run"), 0)
        self.assertNotEqual(self.command("review", "--path", str(self.evidence), "--message", "Inspect inputs"), 0)
        self.assertNotEqual(self.command("record-check", "--check", "result-recorded", "--result", "pass", "--evidence", str(self.evidence)), 0)
        self.assertEqual(self.command("resolve"), 0)
        self.assertEqual(self.command("run"), 0)
        self.assertEqual(self.command("record-check", "--check", "result-recorded", "--result", "pass", "--evidence", str(self.evidence)), 0)

    def test_pause_resume_preserves_step_cursor(self):
        self.command("run")
        before = rt.load_state(self.session)
        self.assertEqual(self.command("pause"), 0)
        self.assertNotEqual(self.command("run"), 0)
        self.assertEqual(self.command("resume"), 0)
        after = rt.load_state(self.session)
        self.assertEqual(after["status"], before["status"])
        self.assertEqual(after["units"][0]["step_cursor"], before["units"][0]["step_cursor"])

    def test_reset_archives_state_and_preserves_sources(self):
        before = rt.load_state(self.session)
        self.assertNotEqual(self.command("reset"), 0)
        self.assertEqual(self.command("reset", "--confirm"), 0)
        after = rt.load_state(self.session)
        self.assertNotEqual(after["run_id"], before["run_id"])
        archive = json.loads(Path(after["previous_run_archive"]).read_text())
        self.assertEqual(archive["run_id"], before["run_id"])
        self.assertTrue(self.evidence.exists())
        self.assertEqual(after["selection"], before["selection"])

    def test_workspace_lock_serializes_different_sessions(self):
        state = rt.load_state(self.session)
        other = dict(state, run_id="another-run")
        with rt.workspace_lock(state):
            with self.assertRaisesRegex(ValueError, "locked"):
                with rt.workspace_lock(other):
                    pass
        self.assertFalse((self.app / ".coreskills/workspace.lock").exists())

    def test_config_edit_invalidates_old_observations(self):
        self.command("run")
        self.command("record-check", "--check", "result-recorded", "--result", "pass", "--evidence", str(self.evidence))
        config = Path(rt.load_state(self.session)["units"][0]["config"])
        config.write_text(config.read_text() + "\n# changed\n")
        self.assertNotEqual(self.command("run"), 0)
        self.assertEqual(self.command("reconcile"), 0)
        self.assertEqual(rt.load_state(self.session)["units"][0]["step_cursor"], 0)

    def test_completed_state_cannot_have_unfinished_work(self):
        state = rt.load_state(self.session)
        state["status"] = "complete"
        with self.assertRaises(ValueError):
            rt.validate_state(state)

    def test_machine_checks(self):
        self.assertTrue(rt.check_assertion({"kind": "exit_code", "equals": 0}, self.app, {"exit_code": 0}))
        self.assertFalse(rt.check_assertion({"kind": "exit_code", "equals": 0}, self.app, {"exit_code": 7}))
        self.assertTrue(rt.check_assertion({"kind": "file_exists", "path": "evidence.txt"}, self.app))
        self.assertTrue(rt.check_assertion({"kind": "contains", "path": "evidence.txt", "text": "platforms"}, self.app))

    def profile_run(self, selected, disabled):
        definitions = self.app / "definitions"
        shutil.copytree(LIBRARY / 'zephyr-platform-bringup/assets', definitions)
        plan_path = definitions / 'workflow-plan.yaml'
        plan = yaml.safe_load(plan_path.read_text(encoding='utf-8'))
        plan['execution_profile'] = {'name': 'development', 'disabled': {key: {'reason': 'Testing'} for key in disabled}}
        plan_path.write_text(yaml.safe_dump(plan), encoding='utf-8')
        self.runtime = self.app / 'profile-run'
        self.session = self.runtime / 'run.json'
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(['--library', str(LIBRARY), 'init', '--application', str(self.app), '--runtime', str(self.runtime), '--plan', str(plan_path), '--workflow', selected]), 0)

    def test_native_disabled_selection_never_runs_or_commits(self):
        self.profile_run('inventory', ['discover'])
        state = rt.load_state(self.session)
        self.assertEqual(state['units'], [])
        self.assertEqual(state['status'], 'disabled')
        self.assertNotEqual(self.command('run'), 0)
        self.assertNotEqual(self.command('review', '--path', 'evidence.txt', '--message', 'Test'), 0)
        self.assertEqual(self.command('reset', '--confirm'), 0)
        self.assertEqual(rt.load_state(self.session)['status'], 'disabled')

    def test_native_disabled_dependency_blocks_before_work(self):
        self.profile_run('build-combination', ['platform-integration'])
        self.assertTrue(rt.load_state(self.session)['selection']['profile_blockers'])
        self.assertNotEqual(self.command('run'), 0)
        self.assertEqual(rt.load_state(self.session)['units'][0]['results'], {})

    def test_profile_change_cannot_silently_resume_or_reconcile(self):
        state = rt.load_state(self.session)
        plan_path = Path(state['plan'])
        plan = yaml.safe_load(plan_path.read_text(encoding='utf-8'))
        plan['execution_profile']['disabled'] = {'inventory': {'reason': 'Testing'}}
        plan_path.write_text(yaml.safe_dump(plan), encoding='utf-8')
        self.assertNotEqual(self.command('run'), 0)
        self.assertNotEqual(self.command('reconcile'), 0)

    @unittest.skipUnless(shutil.which("git"), "Git unavailable")
    def test_review_commit_and_acceptance_are_separate_gates(self):
        def git(*args):
            return subprocess.run(["git", "-C", str(self.app), *args], check=True, capture_output=True, text=True).stdout.strip()
        git("init")
        git("config", "user.name", "Lifecycle Test")
        git("config", "user.email", "lifecycle@example.invalid")
        git("config", "commit.gpgSign", "false")
        baseline = self.app / "baseline.txt"
        baseline.write_text("baseline")
        git("add", "--", "baseline.txt")
        git("commit", "-m", "Baseline")
        self.command("run")
        self.command("record-check", "--check", "result-recorded", "--result", "pass", "--evidence", str(self.evidence))
        self.command("run")
        self.command("record-check", "--check", "criterion-met", "--result", "pass", "--evidence", str(self.evidence))
        self.assertEqual(rt.load_state(self.session)["status"], "awaiting_criterion")
        self.assertNotEqual(self.command("review", "--path", "evidence.txt", "--message", "Inspect platform"), 0)
        self.assertEqual(self.command("record-criterion", "--result", "pass", "--evidence", str(self.evidence)), 0)
        self.assertEqual(self.command("review", "--path", "evidence.txt", "--message", "Inspect platform"), 0)
        candidate = rt.load_state(self.session)["units"][0]["candidate"]
        self.assertNotEqual(self.command("commit", "--accept", "wrong-digest"), 0)
        time.sleep(1.05) # Commit identity must not depend on Git's current timestamp.
        self.assertEqual(self.command("commit", "--accept", candidate["digest"]), 0)
        state = rt.load_state(self.session)
        self.assertEqual(state["status"], "awaiting_result")
        self.assertNotEqual(self.command("run"), 0)
        commit = state["units"][0]["commit"]
        self.assertIn("Signed-off-by:", git("show", "-s", "--format=%B", commit["sha"]))
        self.assertEqual(self.command("accept-result", "--sha", commit["sha"]), 0)
        self.assertEqual(rt.load_state(self.session)["status"], "complete")


if __name__ == "__main__":
    unittest.main()
