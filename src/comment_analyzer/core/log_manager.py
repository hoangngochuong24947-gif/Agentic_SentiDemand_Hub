"""Structured logging management using Loguru.

This module provides centralized logging with support for both console
and file output, automatic rotation, and specialized logging for analysis results.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from loguru import logger

from comment_analyzer.core.settings import Settings, get_settings


class LogManager:
    """Manages application logging with structured output.

    This class wraps Loguru to provide:
    - Console and file logging
    - Automatic log rotation
    - Specialized logging for analysis results
    - Context-aware logging with extra fields

    Example:
        >>> log_manager = LogManager()
        >>> log_manager.configure()
        >>>
        >>> # Log analysis results
        >>> log_manager.log_analysis("sentiment", {"positive": 100, "negative": 50})
        >>>
        >>> # Log important strings
        >>> log_manager.log_important("Model training completed", category="ml")
    """

    # Track if logging has been configured
    _configured: bool = False

    def __init__(self, settings: Optional[Settings] = None):
        """Initialize log manager.

        Args:
            settings: Settings instance. If None, uses global settings.
        """
        self.settings = settings or get_settings()
        self._log_entries: List[Dict[str, Any]] = []

    def configure(self) -> None:
        """Configure Loguru handlers based on settings.

        This should be called once at application startup.
        """
        if LogManager._configured:
            logger.debug("Logging already configured, skipping")
            return

        # Remove default handler
        logger.remove()

        config = self.settings.logging

        # Console handler
        if config.log_to_console:
            logger.add(
                sys.stderr,
                level=config.level,
                format=config.format_string,
                colorize=True,
            )

        # File handler
        if config.log_to_file:
            log_path = self.settings.paths.get_logs_path()
            log_path.mkdir(parents=True, exist_ok=True)

            log_file = log_path / "app_{time:YYYY-MM-DD}.log"

            logger.add(
                str(log_file),
                level=config.level,
                format=config.format_string,
                rotation=config.rotation,
                retention=config.retention,
                compression=config.compression,
                encoding="utf-8",
            )

        LogManager._configured = True
        logger.info(f"Logging configured at level: {config.level}")

    def get_logger(self):
        """Get the configured logger instance.

        Returns:
            Loguru logger instance
        """
        return logger

    def log_analysis(
        self,
        analysis_type: str,
        data: Dict[str, Any],
        extra: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log analysis results in a structured format.

        Args:
            analysis_type: Type of analysis (e.g., "sentiment", "demand", "topic")
            data: Analysis results data
            extra: Additional context fields
        """
        context = {
            "analysis_type": analysis_type,
            **(extra or {}),
        }

        # Log as JSON for structured logging
        logger.bind(**context).info(
            f"Analysis [{analysis_type}]: {len(data)} results",
            analysis_data=data,
        )

        # Store entry for potential export
        self._log_entries.append({
            "type": "analysis",
            "analysis_type": analysis_type,
            "data": data,
            "context": context,
        })

    def log_important(
        self,
        message: str,
        category: str = "general",
        data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log an important string/message that should be preserved.

        Args:
            message: The important message to log
            category: Category for grouping (e.g., "ml", "config", "error")
            data: Optional associated data
        """
        context = {
            "important": True,
            "category": category,
        }

        logger.bind(**context).info(f"[IMPORTANT] [{category}] {message}", extra_data=data)

        self._log_entries.append({
            "type": "important",
            "category": category,
            "message": message,
            "data": data,
        })

    def log_model_result(
        self,
        model_name: str,
        metrics: Dict[str, float],
        params: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log machine learning model results.

        Args:
            model_name: Name of the model
            metrics: Model performance metrics
            params: Model parameters
        """
        context = {
            "model_name": model_name,
            "metrics": metrics,
            "params": params or {},
        }

        # Format metrics for readability
        metrics_str = ", ".join([f"{k}={v:.4f}" for k, v in metrics.items()])
        logger.bind(**context).info(
            f"Model [{model_name}]: {metrics_str}",
        )

        self._log_entries.append({
            "type": "model_result",
            "model_name": model_name,
            "metrics": metrics,
            "params": params,
        })

    def log_pipeline_start(self, config_summary: Optional[Dict[str, Any]] = None) -> None:
        """Log pipeline start event.

        Args:
            config_summary: Optional configuration summary
        """
        logger.bind(event="pipeline_start").info(
            "=" * 60 + "\nPipeline started",
            config=config_summary,
        )

    def log_pipeline_end(
        self,
        duration_seconds: float,
        results_summary: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log pipeline completion event.

        Args:
            duration_seconds: Total execution time
            results_summary: Optional results summary
        """
        logger.bind(event="pipeline_end").info(
            f"Pipeline completed in {duration_seconds:.2f}s",
            duration=duration_seconds,
            results=results_summary,
        )

        self._log_entries.append({
            "type": "important",
            "category": "pipeline",
            "message": f"Pipeline completed in {duration_seconds:.2f}s",
            "data": {
                "duration_seconds": duration_seconds,
                **(results_summary or {}),
            },
        })

    def log_data_info(
        self,
        data_name: str,
        row_count: int,
        column_info: Optional[Dict[str, str]] = None
    ) -> None:
        """Log data loading/processing information.

        Args:
            data_name: Name/identifier of the data
            row_count: Number of rows
            column_info: Optional column type information
        """
        logger.bind(data_name=data_name).info(
            f"Data [{data_name}]: {row_count} rows",
            columns=column_info,
        )

    def log_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        category: str = "runtime"
    ) -> None:
        """Log an error with context.

        Args:
            error: The exception that occurred
            context: Additional context information
            category: Error category
        """
        logger.bind(
            error_type=type(error).__name__,
            category=category,
            **(context or {}),
        ).error(f"Error [{category}]: {error}")

    def export_log_entries(
        self,
        output_path: Optional[Union[str, Path]] = None,
        entry_type: Optional[str] = None
    ) -> Path:
        """Export collected log entries to a JSON file.

        Args:
            output_path: Path to save the log entries. If None, uses default location.
            entry_type: Filter by entry type (analysis, important, model_result)

        Returns:
            Path to the saved file
        """
        import json
        from datetime import datetime

        if output_path is None:
            log_path = self.settings.paths.get_logs_path()
            log_path.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = log_path / f"log_entries_{timestamp}.json"
        else:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

        # Filter entries if type specified
        entries = self._log_entries
        if entry_type:
            entries = [e for e in entries if e.get("type") == entry_type]

        export_data = {
            "exported_at": datetime.now().isoformat(),
            "total_entries": len(entries),
            "entries": entries,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)

        logger.info(f"Exported {len(entries)} log entries to {output_path}")
        return output_path

    def get_log_entries(
        self,
        entry_type: Optional[str] = None,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get collected log entries with optional filtering.

        Args:
            entry_type: Filter by entry type
            category: Filter by category

        Returns:
            List of log entries
        """
        entries = self._log_entries

        if entry_type:
            entries = [e for e in entries if e.get("type") == entry_type]

        if category:
            entries = [e for e in entries if e.get("category") == category]

        return entries

    def clear_entries(self) -> None:
        """Clear all collected log entries."""
        count = len(self._log_entries)
        self._log_entries.clear()
        logger.debug(f"Cleared {count} log entries")


# Global log manager instance
_log_manager: Optional[LogManager] = None


def get_log_manager() -> LogManager:
    """Get or create global log manager instance.

    Returns:
        LogManager instance (singleton pattern)
    """
    global _log_manager
    if _log_manager is None:
        _log_manager = LogManager()
    return _log_manager


def init_logging(settings: Optional[Settings] = None) -> LogManager:
    """Initialize logging system.

    Args:
        settings: Optional settings instance

    Returns:
        Configured LogManager instance
    """
    global _log_manager
    _log_manager = LogManager(settings)
    _log_manager.configure()
    return _log_manager
