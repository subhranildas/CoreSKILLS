"""Observable command execution, flow logging, and boundary regression checks."""
import json
import base64
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

LIBRARY = Path(__file__).resolve().parents[2]
RUNNER = LIBRARY / 'zephyr-platform-bringup/scripts/run-custom-command.py'


class CustomCommandTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.app = Path(self.temp.name)
        self.runtime = self.app / 'bringup/beta'
        self.log = self.runtime / 'workflow-flow.log'

    def command(self, mode='run', log=None):
        return [sys.executable, '-B', str(RUNNER), mode,
                '--application-root', str(self.app), '--runtime-root', str(self.runtime),
                '--log', str(log or self.log), '--run-id', 'run1',
                '--workflow-path', 'add-platform/verification/build-matrix',
                '--work-id', 'build.sensor.beta.debug', '--step-id', 'perform',
                '--attempt-id', 'command1']

    def run_command(self, arguments, log=None):
        return subprocess.run(self.command(log=log) + ['--cwd', str(self.app), '--', *arguments],
                              capture_output=True, text=True)

    def records(self):
        return [json.loads(line) for line in self.log.read_text(encoding='utf-8').splitlines()]

    def test_streams_output_and_preserves_literal_arguments(self):
        literal = 'space and $(literal)'
        result = self.run_command([sys.executable, '-u', '-c', 'import sys; print(sys.argv[1]); print("stderr-output", file=sys.stderr)', literal])
        self.assertEqual(result.returncode, 0, result.stderr)
        records = self.records()
        self.assertEqual(records[0]['event'], 'command_start')
        self.assertEqual(records[0]['argv'][-1], literal)
        output = ''.join(r['text'] for r in records if r['event'] == 'command_output')
        self.assertIn(literal, output)
        self.assertIn('stderr-output', output)
        self.assertEqual(records[-1]['exit_code'], 0)
        self.assertTrue(all(r['work_id'] == 'build.sensor.beta.debug' for r in records))
        self.assertFalse(Path(str(self.log) + '.lock').exists())

    def test_failed_command_returns_and_logs_its_exit_code(self):
        result = self.run_command([sys.executable, '-c', 'raise SystemExit(7)'])
        self.assertEqual(result.returncode, 7)
        self.assertEqual(self.records()[-1]['exit_code'], 7)

    def test_event_appends_without_executing_a_command(self):
        self.run_command([sys.executable, '-c', 'print("first")'])
        before = self.log.read_bytes()
        result = subprocess.run(self.command('event') + ['--event', 'awaiting_input', '--message', 'Waiting for Continue'], capture_output=True)
        self.assertEqual(result.returncode, 0)
        self.assertTrue(self.log.read_bytes().startswith(before))
        self.assertEqual(self.records()[-1]['event'], 'awaiting_input')

    def test_protected_output_refused_before_command_runs(self):
        marker = self.app / 'executed'
        result = self.run_command([sys.executable, '-c', 'from pathlib import Path; Path("executed").write_text("yes")'], log=LIBRARY / 'forbidden-flow.log')
        self.assertEqual(result.returncode, 125)
        self.assertFalse(marker.exists())
        self.assertFalse((LIBRARY / 'forbidden-flow.log').exists())

    def test_existing_lock_blocks_execution_and_is_preserved(self):
        self.runtime.mkdir(parents=True)
        lock = Path(str(self.log) + '.lock')
        lock.write_text('other writer')
        result = self.run_command([sys.executable, '-c', 'print("must not run")'])
        self.assertEqual(result.returncode, 125)
        self.assertEqual(lock.read_text(), 'other writer')
        self.assertFalse(self.log.exists())

    def test_partial_tail_is_preserved_and_repaired_before_append(self):
        self.runtime.mkdir(parents=True)
        prefix = b'{"event":"previous"}\n'
        original = prefix + b'{"event":"unfinished'
        self.log.write_bytes(original)
        result = subprocess.run(self.command('event') + ['--event', 'awaiting_input'], capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        records = self.records()
        self.assertEqual(records[1]['event'], 'log_tail_quarantined')
        self.assertEqual(Path(records[1]['original_copy']).read_bytes(), original)
        self.assertEqual(records[-1]['event'], 'awaiting_input')

    def test_corrupt_complete_record_blocks_execution(self):
        self.runtime.mkdir(parents=True)
        original = b'not-json\n'
        self.log.write_bytes(original)
        result = self.run_command([sys.executable, '-c', 'print("must not run")'])
        self.assertEqual(result.returncode, 125)
        self.assertEqual(self.log.read_bytes(), original)

    def test_valid_record_without_newline_is_not_lost(self):
        self.runtime.mkdir(parents=True)
        self.log.write_bytes(b'{"event":"previous"}')
        result = subprocess.run(self.command('event') + ['--event', 'awaiting_input'], capture_output=True)
        self.assertEqual(result.returncode, 0)
        self.assertEqual([r['event'] for r in self.records()], ['previous', 'awaiting_input'])

    def test_custom_encoding_and_exact_raw_output(self):
        command = self.command() + ['--cwd', str(self.app), '--encoding', 'cp1252', '--', sys.executable, '-c', 'import sys; sys.stdout.buffer.write(bytes([0xe9,0x00,0xff]))']
        result = subprocess.run(command, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        outputs = [r for r in self.records() if r['event'] == 'command_output']
        self.assertEqual(''.join(r['text'] for r in outputs), '\u00e9\x00\u00ff')
        self.assertEqual(b''.join(base64.b64decode(r['raw_base64']) for r in outputs), bytes([0xe9, 0, 0xff]))

    def test_inherited_pipe_does_not_hang_after_parent_exit(self):
        code = 'import subprocess,sys; subprocess.Popen([sys.executable,"-c","import time; time.sleep(2)"]); print("parent finished")'
        command = self.command() + ['--cwd', str(self.app), '--drain-timeout', '0.15', '--', sys.executable, '-c', code]
        started = time.monotonic()
        result = subprocess.run(command, capture_output=True, timeout=5)
        self.assertLess(time.monotonic() - started, 1.5)
        self.assertEqual(result.returncode, 125)
        end = self.records()[-1]
        self.assertEqual(end['exit_code'], 0)
        self.assertFalse(end['capture_complete'])
        self.assertTrue(end['descendants_may_remain'])
        # Let the intentionally surviving descendant exit before Windows removes its cwd.
        time.sleep(max(0, 2.3 - (time.monotonic() - started)))

    def test_unknown_encoding_rejected_before_execution(self):
        command = self.command() + ['--cwd', str(self.app), '--encoding', 'missing-codec', '--', sys.executable, '-c', 'print("must not run")']
        result = subprocess.run(command, capture_output=True)
        self.assertEqual(result.returncode, 125)
        self.assertFalse(self.log.exists())


if __name__ == '__main__':
    unittest.main()
