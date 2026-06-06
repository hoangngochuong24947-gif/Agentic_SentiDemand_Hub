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
