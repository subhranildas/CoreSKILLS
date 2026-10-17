"""Validated state changes with atomic persistence and application-wide locks."""
import hashlib
import importlib.util
import json
import os
import sys
import tempfile
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

VERSION = 1
STATUSES = {"ready", "disabled", "awaiting_observation", "awaiting_intervention", "awaiting_criterion", "awaiting_commit", "awaiting_candidate", "awaiting_result", "paused", "stopped", "complete"}


def now():
    return datetime.now(timezone.utc).isoformat()


def library_path(override=None):
    candidates = [Path(override)] if override else [Path(__file__).resolve().parent.parent, Path(sys.prefix) / "share/coreskills"]
    for path in candidates:
        if (path / "zephyr-platform-bringup/assets/workflow-plan.yaml").is_file():
            return path.resolve()
    raise ValueError("Library not found; use --library or install the complete package")


def helper(library, relative):
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("coreskills_" + hashlib.sha256(relative.encode()).hexdigest()[:12], Path(library) / relative)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def within(path, root):
    path, root = Path(path).resolve(), Path(root).resolve()
    return path == root or root in path.parents


def guard(state, destination):
    helper(state["library"], "workflow-reset/scripts/boundary-check.py").check(
        Path(state["application"]), Path(state["runtime"]), [Path(destination)], [Path(p) for p in state["protected_roots"]])


def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if Path(temporary).exists():
            Path(temporary).unlink()


@contextmanager
def workspace_lock(state):
    path = Path(state["application"]) / ".coreskills/workspace.lock"
    guard(state, path)
    path.parent.mkdir(parents=True, exist_ok=True)
    token = uuid.uuid4().hex
    try:
        with path.open("x", encoding="utf-8") as stream:
            json.dump({"pid": os.getpid(), "token": token, "run_id": state["run_id"], "started": now()}, stream)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError:
        raise ValueError(f"Workspace locked: {path}; inspect its owner before manual recovery") from None
    try:
        yield
    finally:
        try:
            if json.loads(path.read_text(encoding="utf-8")).get("token") == token:
                path.unlink()
        except (FileNotFoundError, json.JSONDecodeError):
            pass


def validate_state(state):
    if not isinstance(state, dict) or type(state.get("schema_version")) is not int or state["schema_version"] != VERSION:
        raise ValueError("Unsupported lifecycle state schema; migrate explicitly")
    if state.get("status") not in STATUSES or not isinstance(state.get("units"), list):
        raise ValueError("Invalid lifecycle status or units")
    for key in ("application", "runtime", "library", "plan", "run_id"):
        if not isinstance(state.get(key), str) or not state[key]:
            raise ValueError(f"Missing state field: {key}")
    if not isinstance(state.get("protected_roots"), list) or state["library"] not in state["protected_roots"]:
        raise ValueError("State must protect its library")
    cursor = state.get("cursor")
    if type(cursor) is not int or not 0 <= cursor <= len(state["units"]):
        raise ValueError("Invalid unit cursor")
    if state["status"] == "complete" and cursor != len(state["units"]):
        raise ValueError("Completed state has unfinished units")
    ids = [u.get("id") for u in state["units"] if isinstance(u, dict)]
    if len(ids) != len(state["units"]) or any(not isinstance(key, str) or not key for key in ids) or len(ids) != len(set(ids)):
        raise ValueError("Invalid or duplicate work IDs")
    return state


def load_state(path):
    path = Path(path).resolve()
    state = validate_state(json.loads(path.read_text(encoding="utf-8")))
    if not within(path, state["runtime"]):
        raise ValueError("Session is outside its runtime")
    guard(state, path)
    return state


def save_state(path, state, event, **fields):
    validate_state(state)
    guard(state, path)
    state.setdefault("history", []).append({"timestamp": now(), "event": event, **fields})
    state["revision"] = state.get("revision", 0) + 1
    atomic_json(path, state)


def unit(state):
    if state["cursor"] >= len(state["units"]):
        raise ValueError("No active work remains")
    return state["units"][state["cursor"]]


def configuration(state, current):
    path = Path(current["config"])
    validator = helper(state["library"], "workflow-tree-editor/scripts/validate-workflow-plan.py")
    config = validator.load_yaml(path)
    validator.validate_leaf(config, current["base_id"])
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    old = current.get("config_sha256")
    if old and old != digest and (current.get("results") or current.get("candidate")):
        raise ValueError("Config changed after work began; reconcile before continuing")
    if old != digest:
        helper(state["library"], "workflow-tree-editor/scripts/file-state.py").capture([path], Path(state["runtime"]) / "snapshots", Path(state["application"]))
        current["config_sha256"] = digest
        current["config_snapshot"] = str(Path(state["runtime"]) / "snapshots" / (digest + ".snapshot"))
    return config


def pending_step(state):
    current = unit(state)
    config = configuration(state, current)
    index = current.get("step_cursor", 0)
    return current, config, config["steps"][index] if index < len(config["steps"]) else None


def record_check(state, check_id, result, evidence):
    if state["status"] != "awaiting_observation":
        raise ValueError("Start/recheck work before recording observations")
    current, config, step = pending_step(state)
    if step is None or check_id not in {check["id"] for check in step["success_checks"]}:
        raise ValueError("Unknown check for current step")
    if not evidence:
        raise ValueError("At least one existing evidence file is required")
    paths = []
    for item in evidence:
        path = Path(item)
        path = path if path.is_absolute() else Path(state["application"]) / path
        if not path.is_file() or not (within(path, state["application"]) or within(path, state["runtime"])):
            raise ValueError(f"Evidence unavailable/outside workspace: {path}")
        paths.append({"path": str(path.resolve()), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    current.setdefault("results", {}).setdefault(step["id"], {})[check_id] = {"result": result, "evidence": paths, "provenance": "explicit_observation"}
    checks = current["results"][step["id"]]
    state["status"] = "awaiting_intervention" if any(c["result"] == "fail" for c in checks.values()) else "awaiting_observation"
    if all(checks.get(c["id"], {}).get("result") == "pass" for c in step["success_checks"]):
        current["step_cursor"] = current.get("step_cursor", 0) + 1
        state["status"] = "awaiting_criterion" if current["step_cursor"] == len(config["steps"]) else "ready"


def check_assertion(check, application, execution=None):
    kind = check.get("kind", "manual")
    if kind == "exit_code":
        if execution is None:
            raise ValueError("exit_code check requires command execution")
        return execution["exit_code"] == check.get("equals", 0)
    path = Path(check.get("path", ""))
    path = path if path.is_absolute() else Path(application) / path
    if not within(path, application):
        raise ValueError("Automatic check path is outside application")
    if kind == "file_exists":
        return path.is_file()
    if kind == "sha256":
        return path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == check["equals"]
    if kind == "contains":
        return path.is_file() and check["text"] in path.read_text(encoding="utf-8", errors="replace")
    if kind == "metric":
        value = json.loads(path.read_text(encoding="utf-8"))[check["key"]]
        return type(value) in (int, float) and value <= check["maximum"]
    raise ValueError(f"Unsupported automatic check: {kind}")


def verify_evidence(current):
    groups = list(current.get("results", {}).values())
    if current.get("criterion_result"):
        groups.append({"criterion": current["criterion_result"]})
    for checks in groups:
        for result in checks.values():
            for evidence in result["evidence"]:
                path = Path(evidence["path"])
                if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != evidence["sha256"]:
                    raise ValueError(f'Validation evidence changed: {path}; recheck before committing')
