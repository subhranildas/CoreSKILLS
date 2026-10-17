"""Explicit legacy-plan migration creates a candidate copy; never overwrites source."""
import copy
import shutil
import uuid
from pathlib import Path

import yaml

from . import runtime as rt


def migrate_plan(source, output, library, application, confirm=False):
    validator = rt.helper(library, "workflow-tree-editor/scripts/validate-workflow-plan.py")
    old = validator.load_yaml(Path(source))
    if not isinstance(old, dict) or type(old.get("schema_version")) is not int or old["schema_version"] not in (1, 2, 3):
        raise ValueError("Only declared plan schemas 1, 2, 3 have a migration path")
    if old["schema_version"] == 3:
        validator.validate(old, Path(source).resolve().parent)
        return {"changed": False, "message": "Plan is already schema 3"}
    candidate = copy.deepcopy(old)
    candidate["schema_version"] = 3
    additions = []
    root = candidate["entrypoint"]
    nodes = {node["id"]: node for node in candidate["nodes"]}
    for node in candidate["nodes"]:
        node.setdefault("skippable", False)
        if node["kind"] == "work" and not node.get("work_config"):
            if not isinstance(node.get("criterion"), str) or not node["criterion"].strip():
                raise ValueError(f'{node["id"]}: define the criterion before migrating')
            node["work_config"] = "leaves/" + node["id"] + ".yaml"
            additions.append(node["id"])
    root_config = None
    if not nodes[root].get("workflow_config"):
        nodes[root]["workflow_config"] = "root-workflow.yaml"
        root_config = {"schema_version": 1, "workflow_id": root, "inputs": {}, "steps": []}
        for child in nodes[root]["children"]:
            root_config["steps"].append({"id": child, "action": "workflow", "workflow": child,
                                         "skippable": nodes[child]["skippable"], "depends_on": [],
                                         "instructions": "Run and verify the selected child according to its recorded contract",
                                         "success_checks": [{"id": "accepted", "expected": "Child criteria and required commit/report obligations are satisfied", "verification": "Inspect saved child results and evidence", "evidence": []}],
                                         "checkpoint_after": True})
    preview = {"from_schema": old["schema_version"], "to_schema": 3, "added_leaf_configs": additions,
               "added_root_config": root_config is not None, "output": str(Path(output).resolve()), "applied": False}
    if not confirm:
        return preview
    output = Path(output).resolve()
    state = {"application": str(Path(application).resolve()), "runtime": str(output), "library": str(library),
             "protected_roots": [str(library)], "run_id": "migration-" + uuid.uuid4().hex}
    rt.guard(state, output)
    with rt.workspace_lock(state):
        if output.exists():
            raise ValueError("Migration output exists; choose a new directory")
        output.mkdir(parents=True)
        original_dir = Path(source).resolve().parent
        shutil.copyfile(source, output / "original-plan.yaml")
        for node in candidate["nodes"]:
            for key in ("work_config", "workflow_config", "procedure"):
                value = node.get(key)
                if not value:
                    continue
                if Path(value).is_absolute() or ".." in Path(value).parts:
                    raise ValueError("Migration references must be project-relative")
                original = original_dir / value
                if original.is_file():
                    target = output / value
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(original, target)
        for key in additions:
            config = validator.load_yaml(Path(library) / "zephyr-platform-bringup/assets/leaf-work.yaml")
            config["work_id"] = key
            config["steps"][0]["success_checks"][0]["expected"] = nodes[key]["criterion"]
            destination = output / nodes[key]["work_config"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
        if root_config:
            (output / nodes[root]["workflow_config"]).write_text(yaml.safe_dump(root_config, sort_keys=False), encoding="utf-8")
        path = output / "workflow-plan.yaml"
        path.write_text(yaml.safe_dump(candidate, sort_keys=False), encoding="utf-8")
        validator.validate(candidate, output)
        preview["applied"] = True
    return preview
