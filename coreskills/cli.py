"""Unified CLI: deterministic lifecycle operations with explicit human decisions."""
import argparse
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import yaml

from . import __version__
from . import runtime as rt


def git(state, *args, binary=False):
    result = subprocess.run(["git", "-C", state["application"], *args], capture_output=True)
    if result.returncode:
        raise ValueError(result.stderr.decode("utf-8", errors="replace").strip())
    return result.stdout if binary else result.stdout.decode("utf-8", errors="replace").strip()


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def committer(state):
    identity = git(state, "var", "GIT_COMMITTER_IDENT")
    # Git var includes a timestamp; approval binds the stable name/email only.
    return identity.split(">", 1)[0] + ">"


def emit(value):
    print(json.dumps(value, indent=2, ensure_ascii=False))


def adapter_data(path):
    if not path:
        return {"schema_version": 1, "combinations": [], "regressions": [], "peripherals": [], "capabilities": []}
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or type(data.get("schema_version")) is not int or data["schema_version"] != 1:
        raise ValueError("Adapter schema 1 required")
    for key in ("combinations", "regressions", "peripherals", "capabilities"):
        rows = data.get(key, [])
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise ValueError(f"Adapter {key} must contain mappings")
    return data


def initialize(args, library):
    application = args.application.resolve()
    runtime = args.runtime.resolve()
    if not rt.within(runtime, application):
        raise ValueError("CLI runtime must be inside the application for portable snapshots")
    state = {"schema_version": 1, "run_id": uuid.uuid4().hex, "application": str(application),
             "runtime": str(runtime), "library": str(library), "protected_roots": [str(library)] + [str(p.resolve()) for p in args.protected_root],
             "plan": str(runtime / "config/workflow-plan.yaml"), "status": "ready", "cursor": 0, "units": [],
             "revision": 0, "history": [], "external_prerequisites": {}, "selection": {}, "adapter": adapter_data(args.adapter)}
    session = runtime / "run.json"
    rt.guard(state, runtime)
    with rt.workspace_lock(state):
        if runtime.exists():
            raise ValueError("Runtime already exists; resume it or choose a new run directory")
        assets = library / "zephyr-platform-bringup/assets"
        source_plan = args.plan.resolve() if args.plan else assets / "workflow-plan.yaml"
        validator = rt.helper(library, "workflow-tree-editor/scripts/validate-workflow-plan.py")
        plan = validator.load_yaml(source_plan)
        validator.validate(plan, source_plan.parent)
        selector = rt.helper(library, "zephyr-platform-bringup/scripts/select-workflow.py")
        selected = selector.selection(plan, source_plan.parent, args.workflow or plan["entrypoint"])
        runtime.mkdir(parents=True)
        destination = runtime / "config"
        destination.mkdir()
        shutil.copyfile(source_plan, destination / "workflow-plan.yaml")
        files = set()
        for node in plan["nodes"]:
            for field in ("work_config", "workflow_config", "procedure"):
                if node.get(field):
                    files.add(node[field])
        for name in files:
            if Path(name).is_absolute() or ".." in Path(name).parts:
                raise ValueError("CLI project definition paths must be relative and remain within their plan directory")
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source_plan.parent / name, target)
        state["selection"] = selected
        state["source_head"] = git(state, "rev-parse", "HEAD") if shutil.which("git") and (application / ".git").exists() else None
        nodes = {node["id"]: node for node in plan["nodes"]}
        categories = {"selected-combination": "combinations", "affected-existing-combination": "regressions", "selected-peripheral": "peripherals", "required-runtime-capability": "capabilities"}
        for key in selected["executable_node_ids"]:
            node = nodes[key]
            if node["kind"] != "work":
                continue
            rows = state["adapter"].get(categories.get(node.get("expand_per"), ""), []) if node.get("expand_per") else [{}]
            if not rows:
                rows = [{"unresolved_expansion": True}]
            for row in rows:
                suffix = hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()[:10] if node.get("expand_per") else ""
                identifier = key + ("." + suffix if suffix else "")
                config = validator.load_yaml(source_plan.parent / node["work_config"])
                if row.get("command"):
                    validator.validate_command(row["command"], identifier)
                    config["inputs"]["build_command"] = row["command"]
                config_path = runtime / "instances" / (identifier + ".yaml")
                config_path.parent.mkdir(exist_ok=True)
                config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
                state["units"].append({"id": identifier, "base_id": key, "config": str(config_path), "context": row,
                                       "criterion": node["criterion"], "skippable": node["skippable"], "step_cursor": 0, "results": {}, "depends_on": node.get("depends_on", [])})
        if not state["units"]:
            if selected["disabled_nodes"]:
                state["status"] = "disabled"
            else:
                raise ValueError("Selection contains no work")
        state["plan_sha256"] = digest(state["plan"])
        rt.save_state(session, state, "initialized")
    emit({"session": str(session), "selected": selected["selected_node"], "units": len(state["units"]), "status": state["status"]})


def doctor(state, library):
    findings = []
    for skill in ("zephyr-platform-bringup", "git-work-commit", "commit-update-report", "workflow-tree-editor", "workflow-reset", "workflow-help"):
        findings.append({"check": skill, "pass": (library / skill / "SKILL.md").is_file()})
    if state:
        validator = rt.helper(library, "workflow-tree-editor/scripts/validate-workflow-plan.py")
        validator.validate(validator.load_yaml(Path(state["plan"])), Path(state["plan"]).parent)
        findings.append({"check": "plan_identity", "pass": digest(state["plan"]) == state["plan_sha256"]})
        try:
            git(state, "var", "GIT_COMMITTER_IDENT")
            git(state, "rev-parse", "--show-toplevel")
            findings.append({"check": "git_identity", "pass": True})
        except ValueError as error:
            findings.append({"check": "git_identity", "pass": False, "detail": str(error)})
        findings.append({"check": "workspace_lock", "pass": not (Path(state["application"]) / ".coreskills/workspace.lock").exists()})
    return findings


def execute_step(path, state):
    if state["status"] != "ready":
        raise ValueError("Run only from ready; failed work needs resolve, paused work needs resume")
    if digest(state["plan"]) != state["plan_sha256"]:
        raise ValueError("Plan/profile changed; create a reviewed new run before continuing")
    if state["selection"].get("profile_blockers"):
        raise ValueError("Disabled dependencies block this scope: " + json.dumps(state["selection"]["profile_blockers"]))
    missing = set(state["selection"]["external_prerequisite_ids"]) - set(state["external_prerequisites"])
    if missing:
        raise ValueError("Scoped prerequisite evidence missing: " + ", ".join(sorted(missing)))
    current, config, step = rt.pending_step(state)
    if current["context"].get("unresolved_expansion"):
        raise ValueError("This expanded work needs a concrete adapter row; create a reviewed new run with an adapter")
    if step is None:
        state["status"] = "awaiting_criterion"
        rt.save_state(path, state, "checks_finished")
        return
    validator = rt.helper(state["library"], "workflow-tree-editor/scripts/validate-workflow-plan.py")
    validator.validate_leaf(config, current["base_id"], require_ready=True, step_id=step["id"])
    state["status"] = "awaiting_observation"
    rt.save_state(path, state, "step_started", work=current["id"], step=step["id"])
    if step["action"] != "command":
        emit({"action_required": step["action"], "instructions": step["instructions"], "checks": step["success_checks"]})
        return
    command = config["inputs"][step["command_ref"]] if step.get("command_ref") else step["command"]
    argv = command.get("argv")
    if argv is None:
        raise ValueError("Native CLI command execution requires explicit argv; convert shell syntax to shell executable argv")
    cwd = Path(command["working_directory"])
    cwd = cwd if cwd.is_absolute() else Path(state["application"]) / cwd
    attempt = uuid.uuid4().hex
    log = Path(state["runtime"]) / "workflow-flow.log"
    state["operation"] = {"state": "running", "command_attempt": attempt, "log": str(log), "work": current["id"], "step": step["id"]}
    rt.save_state(path, state, "command_started")
    runner = Path(state["library"]) / "zephyr-platform-bringup/scripts/run-custom-command.py"
    invocation = [sys.executable, "-B", str(runner), "run", "--application-root", state["application"], "--runtime-root", state["runtime"],
                  "--cwd", str(cwd), "--log", str(log), "--run-id", state["run_id"], "--workflow-path", state["selection"]["selected_node"],
                  "--work-id", current["id"], "--step-id", step["id"], "--attempt-id", attempt]
    for protected in state["protected_roots"]:
        invocation += ["--protected-root", protected]
    code = subprocess.run(invocation + ["--", *argv]).returncode
    state["operation"]["state"] = "finished"
    state["operation"]["exit_code"] = code
    current["execution"] = {"exit_code": code, "log": str(log)}
    if code:
        state["status"] = "awaiting_intervention"
    else:
        for check in step["success_checks"]:
            if check.get("kind", "manual") != "manual":
                passed = rt.check_assertion(check, state["application"], current["execution"])
                rt.record_check(state, check["id"], "pass" if passed else "fail", [log])
                if not passed:
                    break
    rt.save_state(path, state, "command_finished", exit_code=code)
    emit({"status": state["status"], "exit_code": code, "log": str(log)})


def candidate(state, paths, message):
    if state["status"] not in {"awaiting_commit", "awaiting_candidate"}:
        raise ValueError("All step checks must pass before commit review")
    current = rt.unit(state)
    rt.configuration(state, current)
    rt.verify_evidence(current)
    if current.get("criterion_result", {}).get("result") != "pass":
        raise ValueError("The aggregate leaf criterion must pass before review")
    if git(state, "diff", "--cached", "--name-only"):
        raise ValueError("Git index contains staged changes; resolve ownership before review")
    entries = []
    for item in paths:
        path = Path(item)
        path = path if path.is_absolute() else Path(state["application"]) / path
        rt.guard(state, path)
        if not path.is_file() or not rt.within(path, state["application"]):
            raise ValueError("Candidate files must exist inside application")
        relative = path.resolve().relative_to(Path(state["application"]).resolve()).as_posix()
        if rt.within(path, state["runtime"]) and relative != current.get("work_report"):
            raise ValueError("Live state, snapshots and post-commit logs/reports are not candidate source files")
        entries.append({"path": relative, "sha256": digest(path), "blob": git(state, "hash-object", "--path=" + relative, "--", relative)})
    if not entries:
        raise ValueError("Choose explicit owned paths; no empty commits")
    identity = committer(state)
    attempt = uuid.uuid4().hex
    message = message + f"\n\nWorkflow-Run: {state['run_id']}\nWorkflow-Work: {current['id']}\nWorkflow-Attempt: {attempt}\n"
    data = {"paths": entries, "message": message, "identity": identity, "head": git(state, "rev-parse", "HEAD"), "attempt": attempt}
    data["digest"] = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
    current["candidate"] = data
    state["status"] = "awaiting_candidate"
    return data


def create_commit(path, state, accepted):
    if state["status"] != "awaiting_candidate":
        raise ValueError("No pending commit candidate")
    current = rt.unit(state)
    rt.configuration(state, current)
    rt.verify_evidence(current)
    data = current["candidate"]
    actual_digest = hashlib.sha256(json.dumps({k: v for k, v in data.items() if k != "digest"}, sort_keys=True).encode()).hexdigest()
    if accepted != data["digest"] or actual_digest != accepted or git(state, "rev-parse", "HEAD") != data["head"] or committer(state) != data["identity"]:
        raise ValueError("Acceptance/candidate identity changed; review again")
    if any(digest(Path(state["application"]) / item["path"]) != item["sha256"] for item in data["paths"]):
        raise ValueError("Candidate content changed; review again")
    if git(state, "diff", "--cached", "--name-only"):
        raise ValueError("Index changed since review")
    gitdir = Path(git(state, "rev-parse", "--absolute-git-dir"))
    rt.guard(state, gitdir / "index")
    state["operation"] = {"state": "running", "kind": "commit", "attempt": data["attempt"], "head_before": data["head"]}
    rt.save_state(path, state, "candidate_accepted", digest=accepted)
    message_path = Path(state["runtime"]) / "commit-message.txt"
    message_path.write_text(data["message"], encoding="utf-8")
    try:
        git(state, "add", "--", *[item["path"] for item in data["paths"]])
        git(state, "commit", "--signoff", "--file", str(message_path))
        sha = git(state, "rev-parse", "HEAD")
        for item in data["paths"]:
            if git(state, "rev-parse", sha + ":" + item["path"]) != item["blob"]:
                raise ValueError("Hooks changed committed content; revalidate and review actual result")
        message = git(state, "show", "-s", "--format=%B", sha)
        if "Signed-off-by:" not in message or not rt.helper(state["library"], "git-work-commit/scripts/verify-recovery.py").identity_matches(message, state["run_id"], current["id"], data["attempt"]):
            raise ValueError("Actual commit identity/signoff differs from accepted candidate")
        signing = subprocess.run(["git", "-C", state["application"], "config", "--get", "commit.gpgSign"], capture_output=True, text=True)
        if signing.stdout.strip().lower() == "true":
            git(state, "verify-commit", sha)
    except ValueError as error:
        state["status"] = "awaiting_intervention"
        state["operation"]["state"] = "unknown" if git(state, "rev-parse", "HEAD") != data["head"] else "finished"
        state["operation"]["error"] = str(error)
        rt.save_state(path, state, "commit_failed")
        raise
    current["commit"] = {"sha": sha, "verified": True, "result_accepted": False}
    state["operation"]["state"] = "finished"
    report = Path(state["runtime"]) / "updates" / (sha + ".txt")
    report.parent.mkdir(exist_ok=True)
    report.write_text(f"COMMIT UPDATE REPORT\nRun: {state['run_id']}\nWork: {current['id']}\nSHA: {sha}\n\n{message}\n\nValidation: {json.dumps(current['results'], indent=2)}\nResult acceptance: pending\n", encoding="utf-8")
    current["commit"]["report"] = str(report)
    current["commit"]["report_sha256"] = digest(report)
    state["status"] = "awaiting_result"
    rt.save_state(path, state, "commit_verified", sha=sha)
    emit(current["commit"])


def mutate(args, path, state):
    if args.command != "reset" and digest(state["plan"]) != state["plan_sha256"]:
        raise ValueError("Plan/profile changed; create a reviewed new run before continuing")
    current = rt.unit(state) if state["cursor"] < len(state["units"]) else None
    if args.command == "run":
        execute_step(path, state)
        return
    if args.command == "record-check":
        rt.record_check(state, args.check, args.result, args.evidence)
    elif args.command == "record-criterion":
        if state["status"] != "awaiting_criterion":
            raise ValueError("Finish all step checks before recording aggregate acceptance")
        evidence = []
        for name in args.evidence:
            item = Path(name)
            item = item if item.is_absolute() else Path(state["application"]) / item
            if not item.is_file() or not rt.within(item, state["application"]):
                raise ValueError("Criterion evidence must exist inside the application")
            evidence.append({"path": str(item.resolve()), "sha256": digest(item)})
        current["criterion_result"] = {"result": args.result, "evidence": evidence, "criterion": current["criterion"]}
        state["status"] = "awaiting_commit" if args.result == "pass" else "awaiting_intervention"
    elif args.command in {"pause", "stop"}:
        if state.get("operation", {}).get("state") in {"running", "unknown"}:
            raise ValueError("Reconcile the running/unknown operation first")
        state["resume_status"] = state["status"]
        state["status"] = "paused" if args.command == "pause" else "stopped"
    elif args.command == "resume":
        if state["status"] not in {"paused", "stopped"}:
            raise ValueError("Only paused/stopped runs resume")
        state["status"] = state["resume_status"]
    elif args.command == "resolve":
        if state["status"] != "awaiting_intervention" or state.get("operation", {}).get("state") in {"running", "unknown"}:
            raise ValueError("Only failed, reconciled work can be retried")
        step = rt.pending_step(state)[2]
        state["status"] = "ready" if step else "awaiting_criterion"
        if step:
            current.get("results", {}).pop(step["id"], None)
    elif args.command == "review":
        emit(candidate(state, args.path, args.message))
    elif args.command == "commit":
        create_commit(path, state, args.accept)
        return
    elif args.command == "accept-result":
        if state["status"] != "awaiting_result" or args.sha != current["commit"]["sha"]:
            raise ValueError("Accept the exact verified current result")
        report = Path(current["commit"]["report"])
        if digest(report) != current["commit"]["report_sha256"]:
            raise ValueError("Report changed; inspect before accepting")
        report.write_text(report.read_text(encoding="utf-8").replace("Result acceptance: pending", "Result acceptance: accepted"), encoding="utf-8")
        current["commit"].update(result_accepted=True, report_sha256=digest(report))
        state["cursor"] += 1
        state["status"] = "complete" if state["cursor"] == len(state["units"]) else "ready"
    elif args.command == "skip":
        if state["status"] != "ready" or not current["skippable"] or not args.reason.strip():
            raise ValueError("Skip requires a ready skippable unit and reason")
        current["skipped"] = {"reason": args.reason, "timestamp": rt.now()}
        state["cursor"] += 1
        state["status"] = "complete" if state["cursor"] == len(state["units"]) else "ready"
    elif args.command == "prerequisite":
        if args.id not in state["selection"]["external_prerequisite_ids"]:
            raise ValueError("Not an external prerequisite in this selection")
        evidence = Path(args.evidence).resolve()
        if not evidence.is_file():
            raise ValueError("Prerequisite evidence must exist")
        state["external_prerequisites"][args.id] = {"path": str(evidence), "sha256": digest(evidence), "verification": args.verification}
    elif args.command == "reconcile":
        if state.get("operation", {}).get("state") in {"running", "unknown"}:
            raise ValueError("Unknown operation outcome must be resolved before config adoption")
        current.pop("config_sha256", None)
        current.pop("candidate", None)
        current["results"], current["step_cursor"] = {}, 0
        current.pop("criterion_result", None)
        rt.configuration(state, current)
        state["status"] = "ready"
    elif args.command == "reset":
        if not args.confirm or state.get("operation", {}).get("state") in {"running", "unknown"}:
            raise ValueError("Reset needs --confirm and no unresolved operation")
        archive = Path(state["runtime"]) / "archives" / uuid.uuid4().hex / "run.json"
        rt.atomic_json(archive, state)
        state["previous_run_archive"] = str(archive)
        state["run_id"] = uuid.uuid4().hex
        state["cursor"], state["status"] = 0, "ready" if state["units"] else "disabled"
        state.pop("operation", None)
        for item in state["units"]:
            for field in ("candidate", "commit", "execution", "skipped", "criterion_result"):
                item.pop(field, None)
            item["results"], item["step_cursor"] = {}, 0
    rt.save_state(path, state, args.command)
    emit({"status": state["status"], "cursor": state["cursor"], "run_id": state["run_id"]})


def main(argv=None):
    parser = argparse.ArgumentParser(prog="coreskills", description=__doc__)
    parser.add_argument("--library", type=Path)
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--application", required=True, type=Path)
    init.add_argument("--runtime", required=True, type=Path)
    init.add_argument("--workflow")
    init.add_argument("--plan", type=Path)
    init.add_argument("--adapter", type=Path)
    init.add_argument("--protected-root", type=Path, action="append", default=[])
    for name in ("status", "tree", "doctor", "run", "record-check", "record-criterion", "pause", "stop", "resume", "resolve", "review", "commit", "accept-result", "skip", "prerequisite", "reconcile", "reset"):
        command = sub.add_parser(name)
        command.add_argument("--session", required=name not in {"tree", "doctor"}, type=Path)
        if name == "tree":
            command.add_argument("--plan", type=Path)
        if name in {"record-check", "record-criterion"}:
            if name == "record-check":
                command.add_argument("--check", required=True)
            command.add_argument("--result", choices=["pass", "fail"], required=True)
            command.add_argument("--evidence", action="append", required=True)
        if name == "review":
            command.add_argument("--path", action="append", required=True)
            command.add_argument("--message", required=True)
        if name == "commit":
            command.add_argument("--accept", required=True, help="Exact reviewed candidate digest")
        if name == "accept-result":
            command.add_argument("--sha", required=True)
        if name == "skip":
            command.add_argument("--reason", required=True)
        if name == "prerequisite":
            command.add_argument("--id", required=True)
            command.add_argument("--evidence", required=True)
            command.add_argument("--verification", required=True)
        if name == "reset":
            command.add_argument("--confirm", action="store_true")
    help_parser = sub.add_parser("help")
    help_parser.add_argument("topic", nargs="?", choices=["setup", "usage", "tree", "cli"], default="cli")
    docs = sub.add_parser("docs")
    docs.add_argument("--output", type=Path, required=True)
    docs.add_argument("--write", action="store_true", help="Explicit library-maintenance generation; never called during a workflow run")
    migration = sub.add_parser("migrate")
    migration.add_argument("--plan", required=True, type=Path)
    migration.add_argument("--application", required=True, type=Path)
    migration.add_argument("--output", required=True, type=Path)
    migration.add_argument("--confirm", action="store_true")
    args = parser.parse_args(argv)
    try:
        library = rt.library_path(args.library)
        if args.command == "docs":
            from .documentation import generate
            emit({"changed": generate(library, args.output, args.write), "written": args.write})
            return 0
        if args.command == "migrate":
            from .migration import migrate_plan
            emit(migrate_plan(args.plan, args.output, library, args.application, args.confirm))
            return 0
        if args.command == "help":
            if args.topic == "cli":
                parser.print_help()
            else:
                filename = {"setup": "setup.md", "usage": "user-guide.md", "tree": "workflow-tree.md"}[args.topic]
                print((library / "workflow-help/references" / filename).read_text(encoding="utf-8"))
            return 0
        if args.command == "init":
            initialize(args, library)
            return 0
        state = rt.load_state(args.session) if args.session else None
        if args.command == "doctor":
            findings = doctor(state, library)
            emit(findings)
            return 0 if all(item["pass"] for item in findings) else 1
        if args.command == "tree":
            path = args.plan or (Path(state["plan"]) if state else library / "zephyr-platform-bringup/assets/workflow-plan.yaml")
            validator = rt.helper(library, "workflow-tree-editor/scripts/validate-workflow-plan.py")
            plan = validator.load_yaml(path)
            emit(rt.helper(library, "zephyr-platform-bringup/scripts/select-workflow.py").selection(plan, path.resolve().parent, plan["entrypoint"]))
            return 0
        if args.command == "status":
            emit({"run_id": state["run_id"], "status": state["status"], "selected": state["selection"]["selected_node"], "execution_profile": state["selection"].get("execution_profile"), "disabled_nodes": state["selection"].get("disabled_nodes", {}), "profile_blockers": state["selection"].get("profile_blockers", []), "current": rt.unit(state) if state["cursor"] < len(state["units"]) else None})
            return 0
        with rt.workspace_lock(state):
            state = rt.load_state(args.session)
            mutate(args, args.session, state)
        return 0
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, yaml.YAMLError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
