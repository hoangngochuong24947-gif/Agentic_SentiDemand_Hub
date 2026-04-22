"""Install repository hook templates into .git/hooks."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


HOOKS = ["pre-commit", "post-commit", "post-merge"]


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_dir = repo_root / "scripts" / "hooks"
    hooks_path = subprocess.check_output(
        ["git", "rev-parse", "--git-path", "hooks"],
        cwd=repo_root,
        text=True,
    ).strip()
    target_dir = (repo_root / hooks_path).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    for hook_name in HOOKS:
        source = source_dir / f"{hook_name}.ps1"
        target = target_dir / f"{hook_name}.ps1"
        shutil.copy2(source, target)
        print(f"Installed {hook_name} -> {target}")


if __name__ == "__main__":
    main()
