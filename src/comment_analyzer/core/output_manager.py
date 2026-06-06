"""Output file management with automatic sequence numbering.

This module provides utilities for saving analysis results to categorized
folders with automatic incremental numbering to prevent file overwrites.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd
from loguru import logger

from comment_analyzer.core.settings import Settings, get_settings


@dataclass
class SavedFileInfo:
    """Information about a saved file."""
    category: str
    original_name: str
    sequence_number: int
    final_path: Path
    timestamp: datetime = field(default_factory=datetime.now)

    def __str__(self) -> str:
        return f"[{self.category}] {self.original_name} -> {self.final_path.name}"


class OutputManager:
    """Manages output files with automatic sequence numbering.

    This class handles saving analysis results to categorized folders,
    automatically assigning incremental sequence numbers to prevent
    file overwrites.

    Example:
        >>> manager = OutputManager()
        >>> # Save to demand_analysis folder with auto sequence number
        >>> info = manager.save_dataframe(df, "analysis.csv", category="demand")
        >>> print(info.final_path)  # outputs/demand_analysis/001_analysis.csv
        >>>
        >>> # Save with explicit name (no sequence number)
        >>> info = manager.save_dataframe(df, "report.csv", category="sentiment",
        ...                               use_sequence=False)
    """

    def __init__(self, settings: Optional[Settings] = None):
        """Initialize output manager.

        Args:
            settings: Settings instance. If None, uses global settings.
        """
        self.settings = settings or get_settings()
        self._saved_files: List[SavedFileInfo] = []
        self._ensure_directories()
        logger.debug(f"OutputManager initialized with base: {self.settings.paths.output_base}")

    def _ensure_directories(self) -> None:
        """Create all output directories if they don't exist."""
        self.settings.paths.ensure_directories()

    def _get_category_path(self, category: str) -> Path:
        """Get the folder path for a specific category.

        Args:
            category: Category name (demand, sentiment, word_frequency, derived_columns)

        Returns:
            Path to the category folder
        """
        category_map = {
            "demand": self.settings.paths.get_demand_path(),
            "sentiment": self.settings.paths.get_sentiment_path(),
            "word_frequency": self.settings.paths.get_word_frequency_path(),
            "wordfreq": self.settings.paths.get_word_frequency_path(),
            "derived": self.settings.paths.get_derived_columns_path(),
            "derived_columns": self.settings.paths.get_derived_columns_path(),
            "logs": self.settings.paths.get_logs_path(),
        }

        if category.lower() not in category_map:
            # Use the category name as a subfolder under output_base
            path = self.settings.paths.output_base / category
            path.mkdir(parents=True, exist_ok=True)
            return path

        return category_map[category.lower()]

    def _get_next_sequence_number(self, folder: Path, pattern: str = r"^(\d+)_.*") -> int:
        """Get the next available sequence number in a folder.

        Args:
            folder: Directory to scan
            pattern: Regex pattern to extract sequence numbers from filenames

        Returns:
            Next available sequence number (1-based)
        """
        if not folder.exists():
            return 1

        max_num = 0
        regex = re.compile(pattern)

        for item in folder.iterdir():
            if item.is_file():
                match = regex.match(item.name)
                if match:
                    num = int(match.group(1))
                    max_num = max(max_num, num)

        return max_num + 1

    def _generate_filename(
        self,
        original_name: str,
        folder: Path,
        use_sequence: bool = True
    ) -> tuple[str, int]:
        """Generate a filename with optional sequence number.

        Args:
            original_name: Original filename
            folder: Target folder
            use_sequence: Whether to prepend sequence number

        Returns:
            Tuple of (final_filename, sequence_number)
        """
        if not use_sequence:
            return original_name, 0

        seq_num = self._get_next_sequence_number(folder)
        padding = self.settings.output.sequence_padding
        seq_prefix = f"{seq_num:0{padding}d}_"

        return seq_prefix + original_name, seq_num

    def save_dataframe(
        self,
        df: pd.DataFrame,
        filename: str,
        category: str,
        use_sequence: bool = True,
        **kwargs: Any
    ) -> SavedFileInfo:
        """Save a DataFrame to CSV with automatic sequence numbering.

        Args:
            df: DataFrame to save
            filename: Target filename
            category: Output category (determines folder)
            use_sequence: Whether to use sequence numbering
            **kwargs: Additional arguments for to_csv()

        Returns:
            SavedFileInfo with details about the saved file
        """
        folder = self._get_category_path(category)
        final_name, seq_num = self._generate_filename(filename, folder, use_sequence)
        final_path = folder / final_name

        # Default CSV options
        csv_options = {
            "index": self.settings.output.csv_index,
            "encoding": self.settings.output.encoding,
            "float_format": self.settings.output.float_format,
        }
        csv_options.update(kwargs)

        df.to_csv(final_path, **csv_options)

        info = SavedFileInfo(
            category=category,
            original_name=filename,
            sequence_number=seq_num,
            final_path=final_path
        )
        self._saved_files.append(info)

        logger.info(f"Saved DataFrame: {info}")
        return info

    def save_text(
        self,
        content: str,
        filename: str,
        category: str,
        use_sequence: bool = True
    ) -> SavedFileInfo:
        """Save text content to file with automatic sequence numbering.

        Args:
            content: Text content to save
            filename: Target filename
            category: Output category
            use_sequence: Whether to use sequence numbering

        Returns:
            SavedFileInfo with details about the saved file
        """
        folder = self._get_category_path(category)
        final_name, seq_num = self._generate_filename(filename, folder, use_sequence)
        final_path = folder / final_name

        with open(final_path, "w", encoding=self.settings.output.encoding) as f:
            f.write(content)

        info = SavedFileInfo(
            category=category,
            original_name=filename,
            sequence_number=seq_num,
            final_path=final_path
        )
        self._saved_files.append(info)

        logger.info(f"Saved text file: {info}")
        return info

    def save_json(
        self,
        data: Dict[str, Any],
        filename: str,
        category: str,
        use_sequence: bool = True,
        indent: int = 2
    ) -> SavedFileInfo:
        """Save dictionary to JSON file with automatic sequence numbering.

        Args:
            data: Dictionary to save
            filename: Target filename
            category: Output category
            use_sequence: Whether to use sequence numbering
            indent: JSON indentation

        Returns:
            SavedFileInfo with details about the saved file
        """
        import json

        folder = self._get_category_path(category)
        final_name, seq_num = self._generate_filename(filename, folder, use_sequence)
        final_path = folder / final_name

        # JSON should use plain utf-8 without BOM
        encoding = self.settings.output.encoding.replace("-sig", "")
        with open(final_path, "w", encoding=encoding) as f:
            json.dump(data, f, ensure_ascii=False, indent=indent)

        info = SavedFileInfo(
            category=category,
            original_name=filename,
            sequence_number=seq_num,
            final_path=final_path
        )
        self._saved_files.append(info)

        logger.info(f"Saved JSON file: {info}")
        return info

    def save_excel(
        self,
        df: pd.DataFrame,
        filename: str,
        category: str,
        use_sequence: bool = True,
        sheet_name: str = "Sheet1",
        **kwargs: Any
    ) -> SavedFileInfo:
        """Save a DataFrame to Excel file with automatic sequence numbering.

        Args:
            df: DataFrame to save
            filename: Target filename (should end with .xlsx)
            category: Output category
            use_sequence: Whether to use sequence numbering
            sheet_name: Name of the sheet
            **kwargs: Additional arguments for to_excel()

        Returns:
            SavedFileInfo with details about the saved file
        """
        folder = self._get_category_path(category)
        final_name, seq_num = self._generate_filename(filename, folder, use_sequence)
        final_path = folder / final_name

        df.to_excel(final_path, sheet_name=sheet_name, **kwargs)

        info = SavedFileInfo(
            category=category,
            original_name=filename,
            sequence_number=seq_num,
            final_path=final_path
        )
        self._saved_files.append(info)

        logger.info(f"Saved Excel file: {info}")
        return info

    def get_saved_files(self, category: Optional[str] = None) -> List[SavedFileInfo]:
        """Get list of saved files.

        Args:
            category: Optional category filter

        Returns:
            List of SavedFileInfo objects
        """
        if category:
            return [f for f in self._saved_files if f.category == category]
        return self._saved_files.copy()

    def get_latest_file(self, category: str) -> Optional[SavedFileInfo]:
        """Get the most recently saved file in a category.

        Args:
            category: Category to check

        Returns:
            SavedFileInfo or None if no files in category
        """
        category_files = [f for f in self._saved_files if f.category == category]
        if not category_files:
            return None
        return max(category_files, key=lambda f: f.timestamp)

    def list_category_files(self, category: str) -> List[Path]:
        """List all files in a category folder.

        Args:
            category: Category to list

        Returns:
            List of file paths
        """
        folder = self._get_category_path(category)
        if not folder.exists():
            return []
        return sorted(folder.iterdir())

    def clear_category(self, category: str, confirm: bool = False) -> int:
        """Delete all files in a category folder.

        Args:
            category: Category to clear
            confirm: Must be True to actually delete

        Returns:
            Number of files deleted
        """
        if not confirm:
            logger.warning(f"clear_category called without confirm=True for {category}")
            return 0

        folder = self._get_category_path(category)
        if not folder.exists():
            return 0

        count = 0
        for item in folder.iterdir():
            if item.is_file():
                item.unlink()
                count += 1

        logger.info(f"Cleared {count} files from {category}")
        return count

    def generate_summary(self) -> str:
        """Generate a summary of all saved files.

        Returns:
            Formatted summary string
        """
        lines = ["=" * 60]
        lines.append("Output Summary")
        lines.append("=" * 60)
        lines.append(f"Total files saved: {len(self._saved_files)}")
        lines.append("")

        # Group by category
        by_category: Dict[str, List[SavedFileInfo]] = {}
        for info in self._saved_files:
            by_category.setdefault(info.category, []).append(info)

        for category, files in sorted(by_category.items()):
            lines.append(f"\n[{category}]")
            lines.append("-" * 40)
            for f in files:
                seq_str = f"#{f.sequence_number:03d}" if f.sequence_number > 0 else "    "
                lines.append(f"  {seq_str} {f.final_path.name}")

        lines.append("\n" + "=" * 60)
        return "\n".join(lines)
