"""Generate public docs from the canonical guides bundled with workflow-help."""
import os
import re
from pathlib import Path


def generate(library, output, write=False):
    library, output = Path(library).resolve(), Path(output).resolve()
    source = library / "workflow-help/references"
    mapping = {source / "setup.md": output / "setup.md", source / "user-guide.md": output / "usage.md",
               source / "overview.md": output / "README.md", source / "cli-guide.md": output / "cli.md"}
    changed = []
    for original, destination in mapping.items():
        text = original.read_text(encoding="utf-8")
        def link(match):
            target = match.group(1)
            if target.startswith(("https://", "http://", "#")):
                return match.group(0)
            path = (original.parent / target).resolve()
            path = mapping.get(path, path)
            return "](" + os.path.relpath(path, destination.parent).replace("\\", "/") + ")"
        content = "<!-- Generated from workflow-help/references; edit the canonical guide. -->\n\n" + re.sub(r"\]\(([^)]+)\)", link, text)
        if not destination.exists() or destination.read_text(encoding="utf-8") != content:
            changed.append(str(destination))
            if write:
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(content, encoding="utf-8")
    return changed
