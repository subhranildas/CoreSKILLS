#!/usr/bin/env python3
"""Run an explicit argv command or record a workflow event in a JSONL flow log."""
import argparse
import base64
import codecs
import importlib.util
import json
import os
import math
import queue
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path


def prepare_log(log):
    """Refuse corruption; preserve an incomplete final record before repairing it."""
    if not log.exists():
        return None
    data = log.read_bytes()
    complete, separator, tail = data.rpartition(b'\n')
    prefix = complete + separator
    for line in prefix.splitlines():
        item = json.loads(line.decode('utf-8'))
        if not isinstance(item, dict):
            raise ValueError('Existing flow log contains a non-object record')
    if not tail:
        return None
    try:
        valid_tail = isinstance(json.loads(tail.decode('utf-8')), dict)
    except (ValueError, UnicodeError):
        valid_tail = False
    if valid_tail:
        with log.open('ab') as stream:
            stream.write(b'\n')
        return None
    quarantine = log.with_name(log.name + f'.partial-{time.time_ns()}')
    if quarantine.resolve().parent != log.resolve().parent:
        raise ValueError('Invalid quarantine location')
    # Retain the entire original log, not only the damaged tail, before repair.
    with quarantine.open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    if quarantine.read_bytes() != data:
        raise ValueError('Could not verify quarantined flow log')
    with log.open('wb') as stream:
        stream.write(prefix)
    return str(quarantine)


def read_output(pipe, messages, stop):
    try:
        while not stop.is_set():
            chunk = pipe.read1(4096)
            item = ('data', chunk) if chunk else ('eof', None)
            while not stop.is_set():
                try:
                    messages.put(item, timeout=0.1)
                    break
                except queue.Full:
                    continue
            if not chunk:
                break
    except OSError as error:
        if not stop.is_set():
            messages.put(('error', error))
    finally:
        pipe.close()


def validate_paths(args):
    sys.dont_write_bytecode = True
    path = Path(__file__).resolve().parents[2] / 'workflow-reset/scripts/boundary-check.py'
    spec = importlib.util.spec_from_file_location('workflow_boundary', path)
    boundary = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(boundary)
    application = args.application_root.resolve()
    runtime = args.runtime_root.resolve()
    log = args.log.resolve()
    protected = [Path(__file__).resolve().parents[2]] + args.protected_root
    boundary.check(application, runtime, [log, Path(str(log) + '.lock')], protected)
    if not boundary.within(log, runtime):
        raise ValueError('Flow log must be inside the configured runtime directory')
    if args.mode == 'run':
        cwd = args.cwd.resolve()
        if not cwd.is_dir() or not boundary.within(cwd, application):
            raise ValueError('Command working directory must exist inside the application')
        if any(boundary.within(cwd, root.resolve()) for root in protected):
            raise ValueError('Command working directory is inside a protected library')
    return log


def execute(args):
    for field in ('run_id', 'workflow_path', 'work_id', 'step_id', 'attempt_id'):
        if not getattr(args, field).strip():
            raise ValueError(f'{field} must not be empty')
    log = validate_paths(args)
    codecs.lookup(args.encoding)
    b''.decode(args.encoding) # Reject non-text codecs before launching anything.
    if not math.isfinite(args.drain_timeout) or args.drain_timeout <= 0:
        raise ValueError('drain-timeout must be a positive finite number')
    if args.mode == 'run':
        command = args.command
        if command and command[0] == '--':
            command = command[1:]
        if not command or not command[0].strip():
            raise ValueError('Supply an executable and arguments after --')
    log.parent.mkdir(parents=True, exist_ok=True)
    lock = Path(str(log) + '.lock')
    # Refuse concurrent writers; a leftover lock after a crash needs reconciliation.
    with lock.open('x', encoding='utf-8') as handle:
        handle.write(str(os.getpid()))
    try:
        repaired = prepare_log(log)
        with log.open('a', encoding='utf-8', newline='\n') as stream:
            def record(event, **fields):
                item = {'schema_version': 1, 'timestamp_utc': datetime.now(timezone.utc).isoformat(),
                        'run_id': args.run_id, 'workflow_path': args.workflow_path,
                        'work_id': args.work_id, 'step_id': args.step_id,
                        'attempt_id': args.attempt_id, 'event': event, **fields}
                stream.write(json.dumps(item, ensure_ascii=False) + '\n')
                stream.flush()
            if repaired:
                record('log_tail_quarantined', original_copy=repaired)
            if args.mode == 'event':
                record(args.event, message=args.message)
                return 0
            started = time.monotonic()
            record('command_start', argv=command, working_directory=str(args.cwd.resolve()), output_encoding=args.encoding)
            process = None
            reader = None
            stop = threading.Event()
            try:
                flags = {'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == 'nt' else {'start_new_session': True}
                process = subprocess.Popen(command, cwd=args.cwd, stdout=subprocess.PIPE,
                                           stderr=subprocess.STDOUT, shell=False, **flags)
                record('command_spawned', pid=process.pid)
                decoder = codecs.getincrementaldecoder(args.encoding)(errors='replace')
                messages = queue.Queue(maxsize=64)
                reader = threading.Thread(target=read_output, args=(process.stdout, messages, stop), daemon=True)
                reader.start()
                exited_at = None
                capture_complete = True
                while True:
                    code = process.poll()
                    if code is not None and exited_at is None:
                        exited_at = time.monotonic()
                    if exited_at is not None and time.monotonic() - exited_at >= args.drain_timeout:
                        capture_complete = False
                        stop.set()
                        break
                    try:
                        kind, chunk = messages.get(timeout=0.05)
                    except queue.Empty:
                        continue
                    if kind == 'error':
                        raise chunk
                    if kind == 'eof':
                        break
                    output = decoder.decode(chunk)
                    if output:
                        print(output, end='', flush=True)
                    record('command_output', text=output, raw_base64=base64.b64encode(chunk).decode('ascii'))
                tail = decoder.decode(b'', final=True)
                if tail:
                    print(tail, end='', flush=True)
                    record('command_output', text=tail, raw_base64='')
                code = process.wait()
                record('command_end', exit_code=code, capture_complete=capture_complete,
                       runner_exit_code=125 if not capture_complete else code,
                       descendants_may_remain=not capture_complete,
                       duration_seconds=round(time.monotonic() - started, 3))
                if not capture_complete:
                    return 125
                return code if code >= 0 else 128 + (-code)
            except KeyboardInterrupt:
                if process is not None and process.poll() is None:
                    if os.name == 'nt':
                        process.terminate()
                    else:
                        os.killpg(process.pid, signal.SIGTERM)
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                record('command_interrupted', exit_code=process.returncode if process else None,
                       descendants_may_remain=os.name == 'nt')
                return 130
            except OSError as error:
                if process is not None and process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                record('command_error', message=str(error), exit_code=125)
                return 125
            finally:
                stop.set()
                if reader is not None:
                    reader.join(timeout=0.1)
                if reader is None and process is not None and process.stdout is not None:
                    process.stdout.close()
    finally:
        lock.unlink()


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(errors='replace') # Console encoding must not break UTF-8 file logging.
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['run', 'event'])
    parser.add_argument('--application-root', required=True, type=Path)
    parser.add_argument('--runtime-root', required=True, type=Path)
    parser.add_argument('--protected-root', action='append', default=[], type=Path)
    parser.add_argument('--log', required=True, type=Path)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--workflow-path', required=True)
    parser.add_argument('--work-id', required=True)
    parser.add_argument('--step-id', required=True)
    parser.add_argument('--attempt-id', required=True)
    parser.add_argument('--cwd', type=Path)
    parser.add_argument('--event', help='Event name for event mode')
    parser.add_argument('--message', default='')
    parser.add_argument('--encoding', default='utf-8', help='Child output text encoding; raw bytes are always retained')
    parser.add_argument('--drain-timeout', type=float, default=1.0, help='Maximum seconds to drain output after parent exit')
    # Split explicitly: tool options end at --; command arguments are literal argv.
    arguments = sys.argv[1:]
    command = []
    if '--' in arguments:
        index = arguments.index('--')
        arguments, command = arguments[:index], arguments[index + 1:]
    args = parser.parse_args(arguments)
    args.command = command
    if args.mode == 'run' and (not args.cwd or not command or args.event):
        parser.error('run requires --cwd and a command after --')
    if args.mode == 'event' and (not args.event or command or args.cwd):
        parser.error('event requires --event and does not execute commands')
    try:
        return execute(args)
    except (OSError, ValueError, RuntimeError, LookupError) as error:
        print(f'error: {error}', file=sys.stderr)
        return 125


if __name__ == '__main__':
    sys.exit(main())
