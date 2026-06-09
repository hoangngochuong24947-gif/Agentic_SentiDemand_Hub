"""Storage adapters for API run metadata."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Protocol

from comment_analyzer.visualization.run_registry import RunRecord, RunRegistry


class RunStorage(Protocol):
    """Minimal persistence contract used by the API layer."""

    def list_runs(self) -> List[Dict[str, Any]]:
        ...

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        ...

    def record(self, record: RunRecord | Mapping[str, Any]) -> Dict[str, Any]:
        ...

    def latest(self) -> Optional[Dict[str, Any]]:
        ...

    def get_comments(self, run_id: str) -> List[Dict[str, Any]]:
        ...

    def update_comment(self, comment_id: int, updates: Dict[str, Any]) -> None:
        ...

    def save_comments(self, run_id: str, df: Any, text_column: str) -> None:
        ...


class JsonRunStorage:
    """JSON-backed run storage that preserves the existing RunRegistry behavior."""

    def __init__(self, registry_path: Path):
        self.registry = RunRegistry(registry_path)

    def list_runs(self) -> List[Dict[str, Any]]:
        return self.registry.list_runs()

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        return self.registry.get_run(run_id)

    def record(self, record: RunRecord | Mapping[str, Any]) -> Dict[str, Any]:
        return self.registry.record(record)

    def latest(self) -> Optional[Dict[str, Any]]:
        return self.registry.latest()

    def get_comments(self, run_id: str) -> List[Dict[str, Any]]:
        return self.registry.get_comments(run_id)

    def update_comment(self, comment_id: int, updates: Dict[str, Any]) -> None:
        self.registry.update_comment(comment_id, updates)

    def save_comments(self, run_id: str, df: Any, text_column: str) -> None:
        self.registry.save_comments(run_id, df, text_column)
