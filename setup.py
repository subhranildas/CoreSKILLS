"""Ship all six sibling skill folders with the CLI wheel."""
from pathlib import Path
from setuptools import setup

root = Path(__file__).parent
files = []
for skill in ("zephyr-platform-bringup", "git-work-commit", "commit-update-report", "workflow-tree-editor", "workflow-reset", "workflow-help"):
    for directory in sorted({p.parent for p in (root / skill).rglob("*") if p.is_file() and "__pycache__" not in p.parts}):
        items = [str(p.relative_to(root)) for p in directory.iterdir() if p.is_file() and p.suffix in {".py", ".md", ".yaml", ".txt"}]
        if items:
            files.append(("share/coreskills/" + directory.relative_to(root).as_posix(), items))
setup(data_files=files)
