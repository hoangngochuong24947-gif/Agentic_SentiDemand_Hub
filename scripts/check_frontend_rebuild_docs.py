"""Require frontend rebuild docs when guarded frontend/API paths change."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
GUARDED_PREFIXES = ("frontend/", "src/comment_analyzer/api/")
REQUIRED_DOCS = (
    Path("docs/frontend_rebuild_plan.md"),
    Path("docs/frontend_rebuild_memory.md"),
    Path("docs/frontend_rebuild_progress.md"),
)


def git_status_short() -> list[str]:
    result = subprocess.run(
        ["git", "status", "--short"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(result.stderr.strip() or "Failed to read git status.", file=sys.stderr)
        sys.exit(result.returncode)
    return [line for line in result.stdout.splitlines() if line.strip()]


def changed_path_from_status(line: str) -> str:
    path = line[3:].strip()
    if " -> " in path:
        path = path.split(" -> ", 1)[1].strip()
    return path.strip('"').replace("\\", "/")


def has_guarded_changes(status_lines: list[str]) -> bool:
    for line in status_lines:
        path = changed_path_from_status(line)
        if path.startswith(GUARDED_PREFIXES):
            return True
    return False


def missing_or_empty_docs() -> list[Path]:
    missing: list[Path] = []
    for doc in REQUIRED_DOCS:
        full_path = REPO_ROOT / doc
        if not full_path.exists() or not full_path.read_text(encoding="utf-8").strip():
            missing.append(doc)
    return missing


def main() -> int:
    status_lines = git_status_short()
    if not has_guarded_changes(status_lines):
        print("No frontend/API changes detected; frontend rebuild docs check skipped.")
        return 0

    missing = missing_or_empty_docs()
    if missing:
        print("Frontend/API changes detected, but required rebuild docs are missing or empty:")
        for doc in missing:
            print(f"- {doc.as_posix()}")
        return 1

    print("Frontend/API changes detected; required frontend rebuild docs are present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
